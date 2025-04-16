import json
import logging
from google.cloud import storage
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig


class Conversation:
    def __init__(self, bucket_name):
        self.bucket_name = bucket_name
        self.storage_client = storage.Client()

    def generate_conversation(self, article, system_prompt):
        """
        Generates a conversation from the given article using Vertex AI.
        :param article: The text content to base the conversation on
        :param system_prompt: The system prompt for the model
        :return: The generated conversation as a JSON object
        """
        try:
            logging.info("Initializing Vertex AI...")
            vertexai.init(project="sascha-playground-doit", location="us-central1")

            model = GenerativeModel(
                "gemini-1.5-flash-002",
                system_instruction=[system_prompt]
            )

            generation_config = GenerationConfig(
                max_output_tokens=8192,
                temperature=0.7,
                top_p=0.95,
                response_mime_type="application/json",
                response_schema={
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "speaker": {"type": "STRING"},
                            "text": {"type": "STRING"}
                        }
                    }
                },
            )

            responses = model.generate_content(
                [article],
                generation_config=generation_config,
                stream=False,
            )

            json_response = responses.candidates[0].content.parts[0].text
            json_data = json.loads(json_response)

            total_chars = sum(len(part["text"]) for part in json_data)
            logging.info(f"Total character count in conversation: {total_chars}")

            return json_data
        except Exception as e:
            logging.error(f"Failed to generate conversation: {e}")
            raise

    def save_conversation_to_gcs(self, json_data, gcs_path):
        """
        Saves the generated conversation as a JSON file to Google Cloud Storage.
        :param json_data: The conversation data to save
        :param gcs_path: The GCS path (folder) where the file should be saved
        :return: Full GCS path to the saved conversation.json file
        """
        try:
            # Replace `/` with `-` in the URL to flatten the structure
            conversation_path = gcs_path.replace("content.txt", "conversation.json")

            # Upload conversation to GCS
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(conversation_path)

            with blob.open("w") as f:
                json.dump(json_data, f, indent=4)

            logging.info(f"Conversation saved to GCS: gs://{self.bucket_name}/{conversation_path}")
            return f"gs://{self.bucket_name}/{conversation_path}"
        except Exception as e:
            logging.error(f"Failed to save conversation to GCS: {e}")
            raise

