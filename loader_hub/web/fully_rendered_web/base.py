"""Fully Rendered Web scraper."""
from typing import Dict, List, Literal, Optional

from llama_index.readers.base import BaseReader
from llama_index.readers.schema.base import Document

from playwright.sync_api._generated import Browser

from pathlib import Path
path = Path(__file__).parent / "Readability.js"

readabilityjs = ""
with open(path, "r") as f:
    readabilityjs = f.read()

inject_readability = f"""
    (function(){{
      {readabilityjs}
      function executor() {{
        return new Readability({{}}, document).parse();
      }}
      return executor();
    }}())
"""


class RenderedWebPageReader(BaseReader):
    """Fully Rendered Webpage Loader

    Extracting relevant information from a fully rendered web page.
    During the processing, it is always assumed that web pages used as data sources contain textual content.

    1. Load the page and wait for it fully loaded. (playwright)
    2. Inject Readability.js to extract the main content.

    Args:
        proxy (Optional[str], optional): Proxy server. Defaults to None.

    """

    def __init__(self, proxy: Optional[str] = None, wait_until: Optional[
            Literal["commit", "domcontentloaded", "load", "networkidle"]
        ] = "domcontentloaded") -> None:
        self._launch_options = {
            "headless": True,
        }
        self._wait_until = wait_until
        if proxy:
            self._launch_options["proxy"] = {
                "server": proxy,
            }

    def load_data(self, url: str) -> List[Document]:
        """render and load data content from url.

        Args:
            url (str): URL to scrape.

        Returns:
            List[Document]: List of documents.

        """
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(**self._launch_options)

            article = self.scrape_page(
                browser,
                url,
            )
            extra_info = {key: article[key] for key in [
                "title",
                "length",
                "excerpt",
                "byline",
                "dir",
                "lang",
                "siteName",
            ]}

            browser.close()

            return [Document(article["textContent"], extra_info=extra_info)]

    def scrape_page(
        self,
        browser: Browser,
        url: str,
    ) -> Dict[str, str]:
        """Scrape a single article url.

        Args:
            browser (Any): a Playwright Chromium browser.
            url (str): URL of the article to scrape.

        Returns:
            Ref: https://github.com/mozilla/readability
            title: article title;
            content: HTML string of processed article content;
            textContent: text content of the article, with all the HTML tags removed;
            length: length of an article, in characters;
            excerpt: article description, or short excerpt from the content;
            byline: author metadata;
            dir: content direction;
            siteName: name of the site.
            lang: content language

        """
        page = browser.new_page(ignore_https_errors=True)
        page.set_default_timeout(60000)
        page.goto(url, wait_until=self._wait_until)

        r = page.evaluate(inject_readability)

        page.close()
        print("scraped:", url)

        return r
