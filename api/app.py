import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from firestore_handler import FirestoreHandler
from scraper import Scraper
from conversation import Conversation

app = Flask(__name__)
CORS(app)

# Set up logging
logging.basicConfig(level=logging.INFO)

# Initialize FirestoreHandler, Scraper, and Conversation
firestore_handler = FirestoreHandler()
scraper = Scraper(bucket_name="doit-llm", subfolder="learning")
conversation_generator = Conversation(bucket_name="doit-llm")

# Example system prompt
SYSTEM_PROMPT = "You are an experienced podcast host. Generate a conversation from the content provided."

@app.route('/learn', methods=['POST'])
def learn():
    # Parse the incoming JSON request
    data = request.get_json()
    if not data or 'url' not in data:
        app.logger.warning("No URL provided in the request.")
        return jsonify({'error': 'No URL provided'}), 400

    url = data['url']
    app.logger.info(f"Received URL: {url}")

    try:
        # Step 1: Scrape website content
        content = scraper.scrape_website(url)
        app.logger.info("Website content scraped successfully.")

        # Step 2: Upload scraped content to GCS
        gcs_path = scraper.upload_to_gcs(url, content)
        app.logger.info(f"Content uploaded to GCS: {gcs_path}")

        # Step 3: Generate conversation
        conversation = conversation_generator.generate_conversation(content, SYSTEM_PROMPT)
        app.logger.info("Conversation generated successfully.")

        # Step 4: Save conversation to GCS
        conversation_gcs_path = conversation_generator.save_conversation_to_gcs(conversation, gcs_path)
        app.logger.info(f"Conversation saved to GCS: {conversation_gcs_path}")

        # Step 5: Store metadata in Firestore
        doc_id = firestore_handler.store(
            collection_name="scraped_urls",
            url=url,
            gcs_path=gcs_path,
        )
        app.logger.info(f"Metadata stored in Firestore with ID: {doc_id}")

        return jsonify({
            'message': 'URL processed successfully',
            'url': url,
            'content_gcs_path': gcs_path,
            'conversation_gcs_path': conversation_gcs_path,
            'doc_id': doc_id
        }), 200

    except Exception as e:
        app.logger.error(f"Failed to process URL {url}: {e}")
        return jsonify({'error': 'Failed to process URL'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
