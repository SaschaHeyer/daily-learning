from google.cloud import firestore
from datetime import datetime
import logging


class FirestoreHandler:
    def __init__(self):
        # Initialize Firestore client
        self.db = firestore.Client()

    def store(self, collection_name, url, content_gcs_path, conversation_gcs_path):
        """
        Store the URL and its associated GCS paths in Firestore.
        :param collection_name: Firestore collection name
        :param url: The URL to store
        :param content_gcs_path: GCS path for the scraped content
        :param conversation_gcs_path: GCS path for the conversation JSON
        :return: Document ID of the added document
        """
        try:
            # Document data to store in Firestore
            doc_data = {
                'source_url': url,
                'content_gcs_path': content_gcs_path,
                'conversation_gcs_path': conversation_gcs_path,
                'timestamp': datetime.utcnow(),
                'status': 'completed'
            }

            # Add document to Firestore
            doc_ref = self.db.collection(collection_name).document()
            doc_ref.set(doc_data)

            logging.info(f"Metadata stored in Firestore with ID: {doc_ref.id}")
            return doc_ref.id
        except Exception as e:
            logging.error(f"Error storing metadata in Firestore: {e}")
            raise


