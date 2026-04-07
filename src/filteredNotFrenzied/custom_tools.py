"""Custom tool functions for the agent."""

from filteredNotFrenzied.mcp import ToolInfo


def coffee_ratio_brewing(
    water: float = None, coffee: float = None, ratio: float = None
) -> dict:
    """
    Solve for the missing variable in the coffee brewing ratio:
        Water(g) / Coffee(g) = Ratio.

    Provide exactly two of the three arguments to solve for the third.

    Args:
        water: Amount of water in grams (optional)
        coffee: Amount of coffee in grams (optional)
        ratio: Brew ratio (optional)

    Returns:
        dict: {'type': 'water'|'coffee'|'ratio', 'value': float}
    """
    provided = [water is not None, coffee is not None, ratio is not None]
    if sum(provided) != 2:
        raise ValueError(
            "Provide exactly two of the three arguments: water, coffee, ratio."
        )

    if water is None:
        value = coffee * ratio
        return {"type": "water", "value": value}
    elif coffee is None:
        if ratio == 0:
            raise ValueError("Ratio cannot be zero when solving for coffee.")
        if ratio not in {15, 16, 17}:
            raise ValueError("You don't want that! Your coffee will taste awful!")
        value = water / ratio
        return {"type": "coffee", "value": value}
    else:  # ratio is None
        if coffee == 0:
            raise ValueError("Coffee cannot be zero when solving for ratio.")
        value = water / coffee
        return {"type": "ratio", "value": value}


COFFEE_RATIO_BREWING_SPEC = {
    "type": "function",
    "function": {
        "name": "coffee_ratio_brewing",
        "description": "Calculates the brewing ratio, "
        "or needed water/coffee to get to a certain brewing ratio. "
        "Provide exactly two of the three: water, coffee, ratio.",
        "parameters": {
            "type": "object",
            "properties": {
                "water": {"type": "number", "description": "Grams/ml of water"},
                "coffee": {"type": "number", "description": "Grams of coffee"},
                "ratio": {"type": "number", "description": "Brewing ratio"},
            },
            "anyOf": [
                {"required": ["water", "coffee"]},
                {"required": ["water", "ratio"]},
                {"required": ["coffee", "ratio"]},
            ],
        },
    },
}


def kasuya_4_6_split(water: float) -> dict:
    """
    Split total water into 40% and 60% for Tetsu Kasuya's 4:6 method.

    Args:
        water: Total water in grams

    Returns:
        dict: {'first_pour': float, 'second_pour': float}
    """
    if water <= 0:
        raise ValueError("Water amount must be positive.")
    first_pour = round(water * 0.4, 2)
    second_pour = round(water * 0.6, 2)
    return {"first_pour": first_pour, "second_pour": second_pour}


# Example usage:
# result = kasuya_4_6_split(300)
# logger.info(result)  # {'first_pour': 120.0, 'second_pour': 180.0}

KASUYA_4_6_SPLIT_TOOL_SPEC = {
    "type": "function",
    "function": {
        "name": "kasuya_4_6_split",
        "description": "Split total water into 40% and 60% for "
        "Tetsu Kasuya's 4:6 coffee brewing method. "
        "Returns the amount for the first and second pour.",
        "parameters": {
            "type": "object",
            "properties": {
                "water": {"type": "number", "description": "Total water in grams or ml"}
            },
            "required": ["water"],
        },
    },
}


# Create ToolInfo wrappers for each custom tool
COFFEE_RATIO_BREWING_TOOL = ToolInfo(
    name="coffee_ratio_brewing",
    spec=COFFEE_RATIO_BREWING_SPEC,
    exec_fn=coffee_ratio_brewing,
)

KASUYA_4_6_SPLIT_TOOL = ToolInfo(
    name="kasuya_4_6_split", spec=KASUYA_4_6_SPLIT_TOOL_SPEC, exec_fn=kasuya_4_6_split
)


# Export all custom tools as a list
CUSTOM_TOOLS = [COFFEE_RATIO_BREWING_TOOL, KASUYA_4_6_SPLIT_TOOL]
