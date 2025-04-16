import requests
from bs4 import BeautifulSoup
from google.cloud import storage
import os
import re
import logging

class Scraper:
    def __init__(self, bucket_name, subfolder):
        self.bucket_name = bucket_name
        self.subfolder = subfolder
        self.storage_client = storage.Client()

    def scrape_website(self, url):
        """
        Scrapes the content of a website.
        :param url: URL to scrape
        :return: Scraped content as a string
        """
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            # Parse the HTML content
            soup = BeautifulSoup(response.text, 'html.parser')

            # Remove unnecessary elements (e.g., scripts, styles)
            for element in soup(["script", "style", "meta", "noscript", "link"]):
                element.decompose()

            text = soup.get_text(separator='\n')
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            return '\n'.join(lines)
        except Exception as e:
            logging.error(f"Failed to scrape URL {url}: {e}")
            raise

    def upload_to_gcs(self, url, content):
        """
        Uploads scraped content to Google Cloud Storage.
        :param url: URL of the webpage
        :param content: Scraped content to upload
        :return: GCS file path
        """
        try:
            # Replace `/` with `-` in the URL to flatten the structure
            unique_id = url.lower().replace("/", "-").replace(":", "-").strip("-")
            gcs_path = f"{self.subfolder}/{unique_id}/content.txt"

            # Upload content to GCS
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(gcs_path)

            with blob.open("w") as f:
                f.write(content)

            logging.info(f"Content uploaded to GCS: gs://{self.bucket_name}/{gcs_path}")
            return f"gs://{self.bucket_name}/{gcs_path}"
        except Exception as e:
            logging.error(f"Failed to upload content to GCS for URL {url}: {e}")
            raise
