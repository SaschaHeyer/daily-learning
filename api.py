from flask import Flask, request, jsonify
from google.cloud import firestore, storage
import os
from datetime import datetime

# Initialize Flask app
app = Flask(__name__)

# Firestore and Storage clients
firestore_client = firestore.Client()
storage_client = storage.Client()

def get_firestore_collection():
    return firestore_client.collection('podcast_episodes')

@app.route('/add_episode', methods=['POST'])
def add_episode():
    try:
        data = request.json
        required_fields = ['name', 'description', 'website_url', 'audio_file']

        # Validate input
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        episode_data = {
            'name': data['name'],
            'description': data['description'],
            'website_url': data['website_url'],
            'audio_file': data['audio_file'],
            'created_at': datetime.utcnow().isoformat(),
            'finished': False
        }

        # Store in Firestore
        doc_ref = get_firestore_collection().document()
        doc_ref.set(episode_data)

        return jsonify({'message': 'Episode added successfully', 'id': doc_ref.id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/update_episode/<episode_id>', methods=['PATCH'])
def update_episode(episode_id):
    try:
        data = request.json
        update_data = {}

        if 'finished' in data:
            update_data['finished'] = data['finished']
        if 'description' in data:
            update_data['description'] = data['description']

        if not update_data:
            return jsonify({'error': 'No valid fields to update'}), 400

        # Update Firestore document
        doc_ref = get_firestore_collection().document(episode_id)
        doc_ref.update(update_data)

        return jsonify({'message': 'Episode updated successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_episodes', methods=['GET'])
def get_episodes():
    try:
        docs = get_firestore_collection().stream()
        episodes = [{**doc.to_dict(), 'id': doc.id} for doc in docs]
        return jsonify(episodes), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_episode/<episode_id>', methods=['GET'])
def get_episode(episode_id):
    try:
        doc_ref = get_firestore_collection().document(episode_id)
        doc = doc_ref.get()
        if not doc.exists:
            return jsonify({'error': 'Episode not found'}), 404

        return jsonify({**doc.to_dict(), 'id': doc.id}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
