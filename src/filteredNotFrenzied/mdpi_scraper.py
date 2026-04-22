"""MDPI web scraper for downloading research papers."""

import logging
import os
import re
import time
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


class MDPIScraper:
    """Web scraper for MDPI research papers."""

    def __init__(
        self,
        search_query: str = "coffee+brew",
        output_directory: str = "data",
        base_url: str = "https://www.mdpi.com/search?q=",
        results_per_page: int = 200,
        max_retries: int = 5,
        retry_delay: int = 2,
        request_delay: float = 1.0,
        timeout: int = 30,
        user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        log_level: str = "INFO",
    ):
        """Initialize the MDPI scraper.

        Args:
            search_query: Search query for MDPI papers
            output_directory: Directory to save downloaded PDFs
            base_url: Base URL for MDPI search
            results_per_page: Number of results per page (default 200 for maximum results)
            max_retries: Maximum number of retries for failed requests
            retry_delay: Delay in seconds before retrying
            request_delay: Delay in seconds between requests
            timeout: Request timeout in seconds
            user_agent: User agent string for HTTP requests
            log_level: Logging level
        """
        self.search_query = search_query
        self.output_directory = output_directory
        self.base_url = base_url
        self.results_per_page = results_per_page
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.request_delay = request_delay
        self.timeout = timeout
        self.user_agent = user_agent

        # Setup logging
        self.logger = logging.getLogger(__name__)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

        # Create output directory
        os.makedirs(self.output_directory, exist_ok=True)
        self.logger.info(f"Output directory: {self.output_directory}")

    def _get_headers(self) -> dict[str, str]:
        """Return HTTP headers to mimic browser request.

        Returns:
            Dictionary of HTTP headers
        """
        return {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
        }

    def _sanitize_filename(self, filename: str) -> str:
        """Remove invalid characters from filename.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename
        """
        # Remove invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', "", filename)
        # Replace multiple spaces with single space
        filename = re.sub(r"\s+", " ", filename)
        # Remove trailing dots and spaces
        filename = filename.rstrip(". ")
        # Limit length
        if len(filename) > 200:
            filename = filename[:200]
        return filename.strip()

    def _fetch_page(self, url: str, retries: int = 0) -> requests.Response | None:
        """Fetch a web page with retry logic for handling 429 errors.

        Args:
            url: URL to fetch
            retries: Current retry count

        Returns:
            Response object or None if failed
        """
        try:
            response = requests.get(
                url, headers=self._get_headers(), timeout=self.timeout
            )

            if response.status_code == 429:  # Too Many Requests
                if retries < self.max_retries:
                    wait_time = self.retry_delay * (2**retries)  # Exponential backoff
                    retry_info = f"{retries + 1}/{self.max_retries}"
                    msg = f"Rate limited. Waiting {wait_time}s before retry {retry_info}"
                    self.logger.warning(msg)
                    time.sleep(wait_time)
                    return self._fetch_page(url, retries + 1)
                else:
                    self.logger.error(f"Max retries exceeded for {url}")
                    return None

            response.raise_for_status()
            return response

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching {url}: {str(e)}")
            return None

    def _extract_paper_title_from_article(self, article_url: str) -> str | None:
        """Fetch an article page and extract the paper title.

        Args:
            article_url: URL of the article

        Returns:
            Paper title or None if not found
        """
        try:
            response = self._fetch_page(article_url)
            if response is None:
                return None

            soup = BeautifulSoup(response.text, "html.parser")

            # Try multiple selectors for title
            title_elem = (
                soup.find("h1", class_="article-title")
                or soup.find("h1", class_=["title", "heading"])
                or soup.find("meta", attrs={"name": "citation_title"})
                or soup.find("meta", attrs={"property": "og:title"})
            )

            if title_elem:
                if title_elem.name == "meta":
                    title = title_elem.get("content", "")
                else:
                    title = title_elem.get_text(strip=True)
                return title if title else None

            return None
        except Exception as e:
            self.logger.debug(f"Error extracting title from article: {e}")
            return None

    def extract_pdf_links(self, html_content: str, base_url: str) -> list[dict[str, str]]:
        """Extract PDF links with metadata from search results page.

        Args:
            html_content: HTML content of the page
            base_url: Base URL for resolving relative links

        Returns:
            List of paper dictionaries with url, title, and authors
        """
        soup = BeautifulSoup(html_content, "html.parser")
        papers = []

        # Strategy 1: Look for direct PDF links
        # (format: /journal/volume/issue/id/pdf or /pdf?...)
        # Match hrefs that contain /pdf (either at end or followed by query string)
        pdf_links = soup.find_all(
            "a", href=lambda x: x and (x.rstrip("/").endswith("/pdf") or "/pdf?" in x)
        )

        self.logger.debug(
            f"Strategy 1: Found {len(pdf_links)} potential direct PDF links"
        )

        if pdf_links:
            self.logger.info(f"Found {len(pdf_links)} direct PDF links")
            for link in pdf_links:
                pdf_url = urljoin(base_url, link.get("href"))

                # Better title extraction: get text from immediate parent div containers
                title = link.get_text(strip=True)

                # Skip very short titles or UI elements
                if (
                    not title
                    or len(title) < 3
                    or title.lower() in ["pdf", "download", ""]
                ):
                    # Look for title in nearby container elements
                    parent = link.find_parent("article") or link.find_parent(
                        "div",
                        class_=lambda x: (
                            x
                            and any(
                                term in str(x).lower()
                                for term in ["article", "item", "result", "entry", "card"]
                            )
                        ),
                    )

                    if parent:
                        # Try to find heading in the parent
                        heading = parent.find(["h1", "h2", "h3", "h4"])
                        if heading:
                            title = heading.get_text(strip=True)
                        else:
                            # Get first 100 words of text from parent
                            parent_text = parent.get_text(strip=True)
                            words = parent_text.split()[:20]  # First 20 words
                            title = " ".join(words)

                # Skip if title is too long
                if len(title) > 250:
                    title = title[:250].rstrip()

                # Filter out titles that are likely navigation/UI elements
                skip_terms = [
                    "active journals",
                    "journal finder",
                    "sciforum",
                    "proceedings",
                    "contact us",
                    "call for papers",
                    "submit",
                ]
                if any(term.lower() in title.lower() for term in skip_terms):
                    continue

                # Skip if title is very short (less than 5 chars is suspicious)
                if len(title.strip()) < 5:
                    continue

                papers.append(
                    {"url": pdf_url, "title": title or "paper", "authors": "Unknown"}
                )

        if papers:
            self.logger.info(f"Extracted {len(papers)} papers from direct PDF links")
            return papers

        # Fallback Strategy 2: Look for search result containers
        search_results = soup.find_all("li", class_="search-result") or soup.find_all(
            "div", class_="search-result"
        )

        if not search_results:
            # Strategy 3: Look for article-specific containers
            search_results = soup.find_all(
                "div",
                class_=lambda x: (
                    x
                    and any(
                        term in x.lower()
                        for term in ["article", "result", "paper", "item", "entry"]
                    )
                ),
            )

        if not search_results:
            # Strategy 4: Find all links with 'article' or about' in href
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if any(
                    term in href.lower() for term in ["/articles/", "/about/", "/paper/"]
                ):
                    article_url = urljoin(base_url, href)
                    title = link.get_text(strip=True)

                    if not title or len(title) < 3:
                        fetched_title = self._extract_paper_title_from_article(
                            article_url
                        )
                        if fetched_title:
                            title = fetched_title

                    papers.append(
                        {
                            "url": article_url,
                            "title": title or "paper",
                            "authors": "Unknown",
                        }
                    )

            self.logger.info(f"Strategy 4: Found {len(papers)} papers from direct links")
            return papers[:15]  # Limit results from fallback

        self.logger.info(f"Found {len(search_results)} search result containers")

        # Extract from search result containers
        for result in search_results:
            article_link = result.find(
                "a",
                href=lambda x: (
                    x
                    and any(
                        term in x.lower()
                        for term in ["/articles/", "/about/", "/paper/", "/pdf"]
                    )
                ),
            )

            if not article_link:
                continue

            article_url = urljoin(base_url, article_link.get("href"))
            title_elem = result.find(["h2", "h3", "h4", "a"])
            if not title_elem:
                title_elem = article_link

            title = title_elem.get_text(strip=True) if title_elem else "paper"

            # Try to extract authors
            authors_elem = result.find(
                "div",
                class_=lambda x: (
                    x
                    and any(
                        term in x.lower() for term in ["authors", "author", "creators"]
                    )
                ),
            )
            authors = authors_elem.get_text(strip=True) if authors_elem else "Unknown"

            # If title is too short or generic, fetch from article page
            if not title or len(title) < 5:
                self.logger.info(
                    f"  Fetching title from article page: {article_url[:60]}..."
                )
                fetched_title = self._extract_paper_title_from_article(article_url)
                if fetched_title:
                    title = fetched_title
                time.sleep(1)  # Small delay between article page fetches

            papers.append({"url": article_url, "title": title, "authors": authors})

        self.logger.info(f"Found {len(papers)} total papers")
        return papers

    def download_pdf(
        self,
        pdf_info: dict[str, str],
        output_dir: str | None = None,
        retry_count: int = 0,
    ) -> bool:
        """Download a PDF file from article page with better naming and retry logic.

        Args:
            pdf_info: Dictionary with 'url' and 'title' keys
            output_dir: Output directory (uses self.output_directory if None)
            retry_count: Current retry count

        Returns:
            True if successful, False otherwise
        """
        if output_dir is None:
            output_dir = self.output_directory

        article_url = pdf_info["url"]
        title = pdf_info.get("title", "paper")

        try:
            # Check if this is already a direct PDF link
            is_direct_pdf = (
                article_url.rstrip("/").endswith("/pdf") or "/pdf?" in article_url
            )

            if is_direct_pdf:
                # Direct PDF link - download directly
                pdf_url = article_url
                self.logger.debug(f"Direct PDF link: {pdf_url}")

                # Try to fetch article page to get better title if needed
                if title == "paper" or len(title) < 5:
                    # Build article URL from PDF URL (remove /pdf suffix)
                    article_page_url = article_url.split("/pdf")[0]
                    try:
                        response = self._fetch_page(article_page_url)
                        if response:
                            soup = BeautifulSoup(response.text, "html.parser")
                            title_elem = soup.find(
                                "h1", class_="article-title"
                            ) or soup.find("h1")
                            if title_elem:
                                title = title_elem.get_text(strip=True)
                    except Exception:
                        pass  # Use default title if fetching fails
            else:
                # Article page - need to fetch and find PDF link
                response = self._fetch_page(article_url)
                if response is None:
                    self.logger.error(f"Could not fetch article page for {article_url}")
                    return False

                soup = BeautifulSoup(response.text, "html.parser")

                # Find PDF download link on article page
                pdf_link = soup.find("a", href=lambda x: x and ".pdf" in x.lower())

                if not pdf_link:
                    self.logger.warning(
                        f"No PDF link found on article page: {article_url}"
                    )
                    return False

                pdf_url = urljoin(article_url, pdf_link.get("href"))

                # Try to get better title from article if not already good
                if title == "paper" or len(title) < 5:
                    title_elem = soup.find("h1", class_="article-title") or soup.find(
                        "h1"
                    )
                    if title_elem:
                        title = title_elem.get_text(strip=True)

            # Download the PDF
            pdf_response = requests.get(
                pdf_url, headers=self._get_headers(), timeout=self.timeout, stream=True
            )

            if pdf_response.status_code == 429:
                if retry_count < self.max_retries:
                    wait_time = self.retry_delay * (2**retry_count)
                    self.logger.warning(
                        f"Rate limited on PDF download. Waiting {wait_time}s..."
                    )
                    time.sleep(wait_time)
                    return self.download_pdf(pdf_info, output_dir, retry_count + 1)
                else:
                    self.logger.error(f"Max retries exceeded for PDF: {pdf_url}")
                    return False

            pdf_response.raise_for_status()

            # Create filename from title
            filename = self._sanitize_filename(title)

            # Ensure .pdf extension
            if not filename.endswith(".pdf"):
                filename = filename + ".pdf"

            filepath = os.path.join(output_dir, filename)

            # Avoid overwriting files
            if os.path.exists(filepath):
                base, ext = os.path.splitext(filename)
                counter = 1
                while os.path.exists(os.path.join(output_dir, f"{base}_{counter}{ext}")):
                    counter += 1
                filepath = os.path.join(output_dir, f"{base}_{counter}{ext}")

            # Write PDF to file
            with open(filepath, "wb") as f:
                for chunk in pdf_response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            self.logger.info(f"Downloaded: {filepath}")
            return True

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error downloading PDF: {str(e)}")
            return False

    def debug_page(self, search_url: str | None = None) -> None:
        """Inspect page structure to diagnose scraping issues.

        Args:
            search_url: URL to inspect (uses constructed URL from search_query if None)
        """
        if search_url is None:
            params = f"&resultsPerPage={self.results_per_page}"
            search_url = f"{self.base_url}{self.search_query}{params}"

        self.logger.info(f"Base URL: {self.base_url}")
        self.logger.info(f"Search URL: {search_url}")
        self.logger.info(f"\nFetching: {search_url}")

        response = self._fetch_page(search_url)
        if response is None:
            self.logger.error("Could not fetch page")
            return

        soup = BeautifulSoup(response.text, "html.parser")

        self.logger.info(
            f"\nPage title: {soup.title.string if soup.title else 'No title'}"
        )
        self.logger.info(f"Page length: {len(response.text)} characters")

        # Look for any links with 'articles' or 'pdf'
        links_with_articles = soup.find_all("a", href=lambda x: x and "/articles/" in x)
        self.logger.info(
            f"\nFound {len(links_with_articles)} links with '/articles/' in href"
        )

        # Look for search results
        search_results = soup.find_all("li", class_="search-result")
        self.logger.info(
            f"Found {len(search_results)} elements with class 'search-result'"
        )

        search_results2 = soup.find_all("div", class_="search-result")
        self.logger.info(
            f"Found {len(search_results2)} div elements with class 'search-result'"
        )

        # Show first few links found
        self.logger.info("\nFirst 3 links on page:")
        for idx, link in enumerate(soup.find_all("a", href=True)[:3], 1):
            self.logger.info(
                f"  {idx}. {link.get_text(strip=True)[:60]} -> {link['href'][:80]}"
            )

        # Look for common elements
        self.logger.info("\nSearching for common article containers:")
        for class_name in ["article-item", "result-item", "article-container", "article"]:
            found = soup.find_all("div", class_=class_name)
            self.logger.info(f"  Found {len(found)} elements with class '{class_name}'")

    def scrape_and_download(
        self,
        search_url: str | None = None,
    ) -> tuple[int, int]:
        """Scrape MDPI and download PDFs from search results.

        Args:
            search_url: Full search URL (uses base_url + search_query if None)

        Returns:
            Tuple of (total_pdfs_found, total_pdfs_downloaded)
        """
        if search_url is None:
            params = f"&resultsPerPage={self.results_per_page}"
            search_url = f"{self.base_url}{self.search_query}{params}"

        total_pdfs_found = 0
        total_pdfs_downloaded = 0

        self.logger.info(f"Starting scrape with search query: {self.search_query}")
        self.logger.info(f"Search URL: {search_url}")

        # Fetch the search results page
        response = self._fetch_page(search_url)
        if response is None:
            self.logger.error("Could not fetch search page")
            return total_pdfs_found, total_pdfs_downloaded

        html_content = response.text
        self.logger.info(f"Fetched {len(html_content)} bytes")

        # Extract PDF links with metadata
        papers = self.extract_pdf_links(html_content, search_url)

        if papers:
            self.logger.info(f"Found {len(papers)} paper(s)")
            total_pdfs_found = len(papers)

            # Download each PDF
            for paper in papers:
                self.logger.info(f"  - Downloading: {paper['title'][:60]}...")
                if self.download_pdf(paper):
                    total_pdfs_downloaded += 1

                # Delay between downloads
                time.sleep(self.request_delay)
        else:
            self.logger.info("No PDFs found on search results page")
            self.logger.debug(f"HTML content sample: {html_content[:500]}...")

        # Summary
        self.logger.info("\n" + "=" * 50)
        self.logger.info("Scraping Complete!")
        self.logger.info(f"Total PDFs found: {total_pdfs_found}")
        self.logger.info(f"Total PDFs downloaded: {total_pdfs_downloaded}")
        self.logger.info(f"Output directory: {self.output_directory}")
        self.logger.info("=" * 50)

        return total_pdfs_found, total_pdfs_downloaded

    def extract_journal_from_search_results(
        self, html_content: str, paper_index: int
    ) -> str:
        """Extract journal name from search results page.

        Args:
            html_content: HTML content of search results page
            paper_index: Index of paper to extract (0-based)

        Returns:
            Journal name or "Unknown"
        """
        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # Find all PDF links with class UD_Listings_ArticlePDF
            pdf_links = soup.find_all("a", class_="UD_Listings_ArticlePDF")

            if paper_index >= len(pdf_links):
                return "Unknown"

            # Get the specific PDF link
            pdf_link = pdf_links[paper_index]

            # Find the generic-item container
            generic_item = pdf_link.find_parent(class_="generic-item")

            if not generic_item:
                return "Unknown"

            # Find the div with class color-grey-dark, contains journal + publication info
            color_grey_div = generic_item.find("div", class_="color-grey-dark")

            if not color_grey_div:
                return "Unknown"

            # Get the full text from this div
            full_text = color_grey_div.get_text(strip=True)

            # Extract journal name (everything before the year, which is a 4-digit number)
            match = re.match(r"^([^0-9]+?)\d{4}\s*,", full_text)

            if match:
                journal_name = match.group(1).strip()
                if journal_name:
                    return journal_name
            # Fallback: just get text before first digit
            for i, char in enumerate(full_text):
                if char.isdigit():
                    journal_name = full_text[:i].strip()
                    if journal_name:
                        return journal_name
            return "Unknown"
        except Exception as e:
            self.logger.debug(f"Error extracting journal: {str(e)}")

        return "Unknown"

    def extract_publication_date_from_search_results(
        self, html_content: str, paper_index: int
    ) -> str:
        """Extract publication date from search results page.

        Args:
            html_content: HTML content of search results page
            paper_index: Index of paper to extract (0-based)

        Returns:
            Publication date in format "DD Mon YYYY" or "Unknown"
        """
        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # Find all PDF links with class UD_Listings_ArticlePDF
            pdf_links = soup.find_all("a", class_="UD_Listings_ArticlePDF")

            if paper_index >= len(pdf_links):
                return "Unknown"

            # Get the specific PDF link
            pdf_link = pdf_links[paper_index]

            # Find the generic-item container
            generic_item = pdf_link.find_parent(class_="generic-item")

            if not generic_item:
                return "Unknown"

            # Find the div with class color-grey-dark, contains journal + publication info
            color_grey_div = generic_item.find("div", class_="color-grey-dark")

            if not color_grey_div:
                return "Unknown"

            # Get the full text from this div
            full_text = color_grey_div.get_text(strip=True)

            # Extract date (everything after the dash)
            # Pattern: "...DOI- DD Mon YYYY" or "...- DD Mon YYYY"
            match = re.search(r"-\s+(\d{1,2}\s+\w+\s+\d{4})", full_text)

            if match:
                date = match.group(1).strip()
                if date:
                    return date
            # Fallback: look for date pattern anywhere (DD Mon YYYY)
            date_match = re.search(r"(\d{1,2}\s+\w+\s+\d{4})", full_text)
            if date_match:
                return date_match.group(1)
            return "Unknown"
        except Exception as e:
            self.logger.debug(f"Error extracting publication date: {str(e)}")

        return "Unknown"

    def extract_abstract_from_search_results(
        self, html_content: str, paper_index: int, full: bool = True
    ) -> str:
        """Extract abstract/summary from search results page.

        Args:
            html_content: HTML content of search results page
            paper_index: Index of paper to extract (0-based)
            full: If True, return full abstract; if False, return cropped version

        Returns:
            Abstract text or empty string
        """
        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # Find all PDF links with class UD_Listings_ArticlePDF
            pdf_links = soup.find_all("a", class_="UD_Listings_ArticlePDF")

            if paper_index >= len(pdf_links):
                return ""

            # Get the specific PDF link
            pdf_link = pdf_links[paper_index]

            # Find the generic-item container
            generic_item = pdf_link.find_parent(class_="generic-item")

            if not generic_item:
                return ""

            # Find the appropriate abstract div
            if full:
                # Get the FULL abstract (hidden by default, but already in HTML!)
                abstract_div = generic_item.find("div", class_="abstract-full")
            else:
                # Get the short abstract (shown by default)
                abstract_div = generic_item.find("div", class_="abstract-cropped")

            if not abstract_div:
                return ""

            # Extract text, removing the "Abstract" label if present
            abstract_text = abstract_div.get_text(strip=True)

            # Clean up the text
            if abstract_text.startswith("Abstract"):
                abstract_text = abstract_text[8:].strip()

            # Remove "Full article" or "Full Article" from the end
            if abstract_text.endswith("Full article") or abstract_text.endswith(
                "Full Article"
            ):
                abstract_text = abstract_text[:-12].strip()

            return abstract_text if abstract_text else ""
        except Exception as e:
            self.logger.debug(f"Error extracting abstract: {str(e)}")

        return ""

    def extract_version_id_from_url(self, pdf_url: str) -> str:
        """Extract the version ID from the PDF URL.

        Args:
            pdf_url: PDF URL (e.g., https://www.mdpi.com/2076-3417/16/4/1904/pdf?version=1771050786)

        Returns:
            Version ID string or "Unknown" if not found
        """
        try:
            # Extract version parameter from URL
            match = re.search(r"[?&]version=([0-9]+)", pdf_url)
            if match:
                return match.group(1)
        except Exception as e:
            self.logger.debug(f"Error extracting version ID: {str(e)}")
        return "Unknown"

    def extract_all_paper_data(self, html_content: str) -> list[dict]:
        """Extract all paper data from search results page.

        Returns a list of dictionaries with paper information compatible with
          Spark DataFrame.

        Args:
            html_content: HTML content of search results page

        Returns:
            List of dictionaries with keys: id, title, authors, summary, published,
              pdf_url, journal, ingestion_timestamp
        """
        papers = []

        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # Find all PDF links using the class selector for reliability
            pdf_links = soup.find_all("a", class_="UD_Listings_ArticlePDF")

            for idx, pdf_link in enumerate(pdf_links):
                try:
                    # Extract title from data-name attribute
                    title = pdf_link.get("data-name", "Unknown").strip()
                    # Extract PDF URL
                    pdf_href = pdf_link.get("href", "")
                    pdf_url = urljoin(self.base_url, pdf_href) if pdf_href else "Unknown"

                    # Extract version ID from URL
                    version_id = self.extract_version_id_from_url(pdf_url)

                    # Extract metadata using improved methods
                    authors = self.extract_authors_from_search_results(html_content, idx)
                    journal = self.extract_journal_from_search_results(html_content, idx)
                    published = self.extract_publication_date_from_search_results(
                        html_content, idx
                    )
                    summary = self.extract_abstract_from_search_results(html_content, idx)

                    papers.append(
                        {
                            "id": version_id,
                            "title": title,
                            "authors": authors,
                            "summary": summary,
                            "published": published,
                            "pdf_url": pdf_url,
                            "journal": journal,
                            "ingestion_timestamp": datetime.now().isoformat(),
                        }
                    )

                except Exception as e:
                    self.logger.debug(f"Error extracting paper {idx}: {str(e)}")
                    continue

            self.logger.info(f"Extracted {len(papers)} papers with full metadata")

        except Exception as e:
            self.logger.error(f"Error in extract_all_paper_data: {str(e)}")

        return papers

    def extract_authors_from_search_results(
        self, html_content: str, paper_index: int
    ) -> str:
        """Extract paper authors directly from search results page.

        Args:
            html_content: HTML content of search results page
            paper_index: Index of paper (0-based) in the PDF links list

        Returns:
            Comma-separated string of author names, or "Unknown" if not found
        """
        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # Find all PDF links with class UD_Listings_ArticlePDF
            pdf_links = soup.find_all("a", class_="UD_Listings_ArticlePDF")

            if paper_index >= len(pdf_links):
                return "Unknown"

            # Get the specific PDF link
            pdf_link = pdf_links[paper_index]

            # Find the generic-item container
            generic_item = pdf_link.find_parent(class_="generic-item")

            if not generic_item:
                return "Unknown"

            # Find the authors div
            authors_div = generic_item.find("div", class_="authors")

            if not authors_div:
                return "Unknown"

            # Extract author names from <strong> tags
            author_tags = authors_div.find_all("strong")

            if author_tags:
                authors = [
                    tag.get_text(strip=True)
                    for tag in author_tags
                    if tag.get_text(strip=True)
                ]
                if authors:
                    return ", ".join(authors)
            return "Unknown"
        except Exception as e:
            self.logger.debug(f"Error extracting authors: {str(e)}")
            return "Unknown"

    def fetch_papers(self, max_results: int = 50) -> list[dict]:
        """Fetch MDPI papers matching the search query and return as list of dictionaries.

        The search query is set during initialization. This is the main method for
        getting papers compatible with Spark DataFrame.

        Args:
            max_results: Maximum number of results to fetch (default 50)

        Returns:
            List of paper dictionaries with schema:
            {
                'id': int,
                'title': str,
                'authors': str,
                'summary': str,
                'published': str,
                'pdf_url': str,
                'journal': str,
                'ingestion_timestamp': str
            }
        """
        # Build search URL
        params = f"&resultsPerPage={max(max_results, 200)}"
        search_url = f"{self.base_url}{self.search_query}{params}"

        self.logger.info(f"Fetching papers for query: {self.search_query}")
        self.logger.info(f"Search URL: {search_url}")

        # Fetch the search results page
        response = self._fetch_page(search_url)
        if response is None:
            self.logger.error("Could not fetch search page")
            return []

        html_content = response.text
        self.logger.info(f"Fetched {len(html_content)} bytes")

        # Extract all paper data
        papers = self.extract_all_paper_data(html_content)

        # Limit to max_results
        papers = papers[:max_results]

        self.logger.info(f"Returning {len(papers)} papers")
        return papers

    def download_papers(
        self, papers: list[dict], output_dir: str | None = None
    ) -> tuple[int, int]:
        """Download PDFs for a list of papers.

        Args:
            papers: List of paper dictionaries (as returned by fetch_papers)
            output_dir: Output directory (uses self.output_directory if None)

        Returns:
            Tuple of (total_papers, downloaded_count)
        """
        if output_dir is None:
            output_dir = self.output_directory

        total = len(papers)
        downloaded = 0

        self.logger.info(f"Starting download of {total} papers")

        for idx, paper in enumerate(papers, 1):
            try:
                pdf_info = {
                    "url": paper.get("pdf_url"),
                    "title": paper.get("title", "paper"),
                }

                self.logger.info(
                    f"[{idx}/{total}] Downloading: {paper.get('title', 'Unknown')[:60]}"
                )

                if self.download_pdf(pdf_info, output_dir):
                    downloaded += 1

                # Delay between downloads
                time.sleep(self.request_delay)

            except Exception as e:
                self.logger.error(f"Error downloading paper {idx}: {str(e)}")
                continue

        # Summary
        self.logger.info("\n" + "=" * 50)
        self.logger.info("Download Complete!")
        self.logger.info(f"Total papers: {total}")
        self.logger.info(f"Downloaded: {downloaded}")
        self.logger.info(f"Failed: {total - downloaded}")
        self.logger.info(f"Output directory: {output_dir}")
        self.logger.info("=" * 50)

        return total, downloaded
