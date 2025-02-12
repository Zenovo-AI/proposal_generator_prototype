from google.cloud import storage
import streamlit as st
import json

# Load GCP credentials from Streamlit session state
def get_storage_client():
    credentials = st.session_state.get("credentials")
    if credentials:
        try:
            # Using the credentials to initialize the storage client
            storage_client = storage.Client.from_service_account_info(credentials)
            return storage_client
        except Exception as e:
            raise Exception(f"Error initializing GCS client: {e}")
    else:
        raise Exception("No service account credentials found in session state.")

BUCKET_NAME = "lightrag-bucket"

def upload_to_gcs(uploaded_file, destination_blob_path, file_type):
    """Uploads a file (JSON or GraphML) directly to Google Cloud Storage."""
    # Ensure credentials are loaded before proceeding
    if "credentials" not in st.session_state or st.session_state["credentials"] is None:
        raise Exception("Service account credentials are missing. Please upload your credentials.")
    
    try:
        storage_client = get_storage_client()
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(destination_blob_path)

        # Set correct content type
        content_types = {
            "json": "application/json",
            "graphml": "application/xml"
        }
        content_type = content_types.get(file_type, "application/octet-stream")

        # Upload directly from the file-like object
        blob.upload_from_file(uploaded_file, content_type=content_type)
        return f"gs://{BUCKET_NAME}/{destination_blob_path}"

    except Exception as e:
        raise Exception(f"Error uploading file to GCS: {e}")

def process_and_upload(file_data, file_type):
    """Processes and uploads a file to the correct GCS subfolder."""
    # Ensure credentials are loaded before proceeding
    if "credentials" not in st.session_state or st.session_state["credentials"] is None:
        raise Exception("Service account credentials are missing. Please upload your credentials.")
    
    try:
        destination_blob_path = f"analysis_workspace"
        return upload_to_gcs(file_data, destination_blob_path, file_type)
    except Exception as e:
        raise Exception(f"Error processing and uploading file: {e}")

def download_from_gcs(blob_path):
    """Downloads a file from Google Cloud Storage."""
    # Ensure credentials are loaded before proceeding
    if "credentials" not in st.session_state or st.session_state["credentials"] is None:
        raise Exception("Service account credentials are missing. Please upload your credentials.")
    
    try:
        storage_client = get_storage_client()
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(blob_path)

        return blob.download_as_text()
    except Exception as e:
        raise Exception(f"Error downloading file from GCS: {e}")
