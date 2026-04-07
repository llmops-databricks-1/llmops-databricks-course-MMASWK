import json

from databricks.sdk import WorkspaceClient
from loguru import logger
from openai import OpenAI

from filteredNotFrenzied.memory import LakebaseMemory


class MdpiAgent:
    """A simple agent that can call tools in a loop and maintain conversation history."""

    def __init__(
        self,
        llm_endpoint: str,
        system_prompt: str,
        tools: list,
        memory: LakebaseMemory = None,
        session_id: str = None,
    ):
        self.llm_endpoint = llm_endpoint
        self.system_prompt = system_prompt
        self._tools_dict = {tool.name: tool for tool in tools}
        self.workspace_client = WorkspaceClient()
        self._client = OpenAI(
            api_key=self.workspace_client.tokens.create(
                lifetime_seconds=1200
            ).token_value,
            base_url=f"{self.workspace_client.config.host}/serving-endpoints",
        )
        self.memory = memory
        self.session_id = session_id
        # Load conversation history from memory if available
        self.conversation_history = (
            memory.load_messages(session_id) if memory and session_id else []
        )

    def get_tool_specs(self) -> list[dict]:
        """Get tool specifications for the LLM."""
        return [tool.spec for tool in self._tools_dict.values()]

    def execute_tool(self, tool_name: str, args: dict) -> str:
        """Execute a tool by name."""
        if tool_name not in self._tools_dict:
            raise ValueError(f"Unknown tool: {tool_name}")
        return self._tools_dict[tool_name].exec_fn(**args)

    def _save_to_memory(self, messages: list) -> None:
        """Save messages to lakebase memory if configured."""
        if self.memory and self.session_id:
            self.memory.save_messages(self.session_id, messages)

    def chat(self, user_message: str, max_iterations: int = 10) -> str:
        """Chat with the agent,
        allowing tool calls and maintaining conversation history.
        Args:
            user_message: The user's input message
            max_iterations: Max number of tool call iterations before stopping
        Returns:
            Final assistant response after tool calls"""
        # Add user message to history
        user_msg = {"role": "user", "content": user_message}
        self.conversation_history.append(user_msg)
        self._save_to_memory([user_msg])

        # Build messages with system prompt and conversation history
        messages = [
            {"role": "system", "content": self.system_prompt},
        ] + self.conversation_history

        for _ in range(max_iterations):
            response = self._client.chat.completions.create(
                model=self.llm_endpoint,
                messages=messages,
                tools=self.get_tool_specs() if self._tools_dict else None,
            )

            assistant_message = response.choices[0].message

            if assistant_message.tool_calls:
                # Add assistant message with tool calls to history
                tool_calls_data = {
                    "role": "assistant",
                    "content": assistant_message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in assistant_message.tool_calls
                    ],
                }
                messages.append(tool_calls_data)
                self.conversation_history.append(tool_calls_data)
                self._save_to_memory([tool_calls_data])

                for tool_call in assistant_message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)

                    logger.info(f"Calling tool: {tool_name}({tool_args})")

                    try:
                        result = self.execute_tool(tool_name, tool_args)
                    except Exception as e:
                        result = f"Error: {str(e)}"

                    tool_result = {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(result),
                    }
                    messages.append(tool_result)
                    self.conversation_history.append(tool_result)
                    self._save_to_memory([tool_result])
            else:
                # Add final assistant response to history
                final_response = assistant_message.content
                assistant_msg = {"role": "assistant", "content": final_response}
                self.conversation_history.append(assistant_msg)
                self._save_to_memory([assistant_msg])
                return final_response

        return "Max iterations reached."

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.conversation_history = []
        if self.memory and self.session_id:
            self.memory.clear_messages(self.session_id)


# COMMAND ----------
