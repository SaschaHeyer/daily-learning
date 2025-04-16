import json
import vertexai
import os
import re
from datetime import datetime
import shutil
from google.cloud import texttospeech, texttospeech_v1beta1
from google.cloud import storage, firestore
from pydub import AudioSegment
from vertexai.generative_models import GenerativeModel, GenerationConfig
from dotenv import load_dotenv
from pydub import AudioSegment

# Load environment variables from .env file
load_dotenv()

# Google Cloud Configuration
BUCKET_NAME = "doit-llm"
BUCKET_FOLDER = "learning"
PODCAST_FOLDER = "podcasts"
storage_client = storage.Client()

# Clients
tts_client = texttospeech.TextToSpeechClient()
tts_beta_client = texttospeech_v1beta1.TextToSpeechClient()


system_prompt = """you are an experienced podcast host

Follow these instructions precisely:
1. based on text like an article you can create an engaging conversation between two people. 
7. Short sentences that can be easily used with speech synthesis.
8. excitement during the conversation.
9. Include filler words like äh to make the conversation more natural.
10. only use the content provided.
"""

MULTISPEAKER_CONFIG = {
    "Sascha": "U",  
    "Ieva": "R"
}

def upload_to_gcs(file_path, filename, folder, identifier):
    """Upload a file to Google Cloud Storage bucket."""
    try:
        print(f"Uploading file: {file_path} as {filename} to GCS...")
        bucket = storage_client.bucket(BUCKET_NAME)
        destination_blob_name = f"{folder}/{identifier}/{filename}"
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_filename(file_path, timeout=60)
        print(f"File uploaded successfully to: gs://{BUCKET_NAME}/{destination_blob_name}")
        return True, f"gs://{BUCKET_NAME}/{destination_blob_name}"
    except Exception as e:
        print(f"GCS Upload Error: {e}")
        return False, str(e)

def store_metadata_in_firestore(url, gcs_path, podcast_gcs_path, conversation_gcs_path):
    """Store URL, content path, and podcast path in Firestore."""
    try:
        print("Storing metadata in Firestore...")
        db = firestore.Client()
        doc_ref = db.collection('scraped_urls').document()
        doc_data = {
            'source_url': url,
            'content_gcs_path': gcs_path,
            'podcast_gcs_path': podcast_gcs_path,
            'conversation_gcs_path': conversation_gcs_path,
            'timestamp': datetime.now(),
            'status': 'completed'
        }
        doc_ref.set(doc_data)
        print("Metadata stored successfully in Firestore.")
        return True, doc_ref.id
    except Exception as e:
        print(f"Firestore Error: {e}")
        return False, str(e)

def chunk_conversation(conversation, max_bytes=1000):  # Reduced to be even safer
    chunks = []
    current_chunk = []
    current_size = 0
    
    for turn in conversation:
        # Calculate byte size of the text
        text_size = len(turn['text'].encode('utf-8'))
        
        if current_size + text_size > max_bytes:
            # Store current chunk and start a new one
            if current_chunk:  # Only append if chunk is not empty
                chunks.append(current_chunk)
            current_chunk = [turn]
            current_size = text_size
        else:
            current_chunk.append(turn)
            current_size += text_size
    
    # Append the last chunk if it exists
    if current_chunk:
        chunks.append(current_chunk)
    
    print(f"Split conversation into {len(chunks)} chunks")
    for i, chunk in enumerate(chunks):
        print(f"Chunk {i} size: {sum(len(turn['text'].encode('utf-8')) for turn in chunk)} bytes")
    
    return chunks

from boto3 import client

def synthesize_speech_multispeaker(conversation):
    # Create output directory if it doesn't exist
    if os.path.exists('audio-files'):
        shutil.rmtree('audio-files')
    os.makedirs('audio-files', exist_ok=True)
    
    # Split conversation into chunks
    conversation_chunks = chunk_conversation(conversation)
    print(conversation_chunks)
    
    # Process each chunk
    for chunk_index, chunk in enumerate(conversation_chunks):
        multi_speaker_markup = texttospeech_v1beta1.MultiSpeakerMarkup()
        
        for part in chunk:
            turn = texttospeech_v1beta1.MultiSpeakerMarkup.Turn()
            turn.text = part['text']
            turn.speaker = MULTISPEAKER_CONFIG[part['speaker']]
            multi_speaker_markup.turns.append(turn)
        
        synthesis_input = texttospeech_v1beta1.SynthesisInput(
            multi_speaker_markup=multi_speaker_markup
        )
        
        voice = texttospeech_v1beta1.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-Studio-MultiSpeaker"
        )
        
        audio_config = texttospeech_v1beta1.AudioConfig(
            audio_encoding=texttospeech_v1beta1.AudioEncoding.MP3
        )
        
        try:
            response = tts_beta_client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            # Save chunk to file
            chunk_filename = f"audio-files/chunk_{chunk_index}.mp3"
            with open(chunk_filename, "wb") as out:
                out.write(response.audio_content)
            print(f'Audio content written to file "{chunk_filename}"')
            
        except Exception as e:
            print(f"Error processing chunk {chunk_index}:")
            print(f"Chunk size: {sum(len(turn['text'].encode('utf-8')) for turn in chunk)} bytes")
            print(f"Number of turns: {len(chunk)}")
            print(f"Error: {str(e)}")
            raise e
    
    # Merge all chunks
    audio_folder = "./audio-files"
    output_file = "podcast.mp3"
    merge_audios(audio_folder, output_file)


def natural_sort_key(filename):
    return [int(text) if text.isdigit() else text for text in re.split(r'(\d+)', filename)]

def merge_audios(audio_folder, output_file):
    combined = AudioSegment.empty()
    audio_files = sorted(
        [f for f in os.listdir(audio_folder) if f.endswith(".mp3") or f.endswith(".wav")],
        key=natural_sort_key
    )
    for filename in audio_files:
        audio_path = os.path.join(audio_folder, filename)
        print(f"Processing: {audio_path}")
        audio = AudioSegment.from_file(audio_path)
        combined += audio
    combined.export(output_file, format="mp3")
    print(f"Merged audio saved as {output_file}")


def generate_conversation(article):
    print(article)
    vertexai.init(project="sascha-playground-doit", location="us-central1")
    model = GenerativeModel(
        "gemini-1.5-flash-002",
        system_instruction=[system_prompt]
    )

    # Vertex AI configuration
    generation_config = GenerationConfig(
        max_output_tokens=8192,
        temperature=0.7,
        top_p=0.95,
        response_mime_type="application/json",
        response_schema={"type": "ARRAY", "items": {"type": "OBJECT", "properties": {"speaker": {"type": "STRING"}, "text": {"type": "STRING"}}}},
    )

    responses = model.generate_content(
        [article],
        generation_config=generation_config,
        stream=False,
    )
    
    json_response = responses.candidates[0].content.parts[0].text
    json_data = json.loads(json_response)
    
    total_chars = sum(len(part["text"]) for part in json_data)
    print(f"Total character count in conversation: {total_chars}")

    formatted_json = json.dumps(json_data, indent=4)
    print(formatted_json)
    return json_data

def generate_audio(conversation):
    synthesize_speech_multispeaker(conversation)
    
    audio_folder = "./audio-files"
    output_file = "podcast.mp3"
    merge_audios(audio_folder, output_file)

def save_conversation(conversation, identifier):
    json_output_path = "conversation.json"
    #os.makedirs(os.path.dirname(json_output_path), exist_ok=True)
    with open(json_output_path, "w") as json_file:
        json.dump(conversation, json_file, indent=4)
    success, gcs_path = upload_to_gcs(json_output_path, json_output_path, BUCKET_FOLDER, identifier)
    print(f"Conversation saved to {json_output_path}")

def main():
    print("reading article")
    # Read the article from the file
    with open('./articles/ranking.txt', 'r') as file:
        article = file.read()

    print(article)

    conversation = generate_conversation(article)

    save_conversation(conversation, "identifier")

    generate_audio(conversation)

if __name__ == "__main__":
    print("main")
    main()