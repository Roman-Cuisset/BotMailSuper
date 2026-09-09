"""
Google Drive Manager - Upload and share files
"""
import os
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Scopes required for Drive access
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def get_drive_service():
    """Authenticate and return Google Drive service"""
    creds = None
    
    # Token file stores user's access and refresh tokens
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # If no valid credentials, let user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save credentials for next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    return build('drive', 'v3', credentials=creds)

def upload_to_drive(file_path, file_name):
    """
    Upload file to Google Drive and return shareable link
    
    Args:
        file_path: Local path to file
        file_name: Name for file on Drive
    
    Returns:
        Shareable link or None if error
    """
    try:
        service = get_drive_service()
        
        # File metadata
        file_metadata = {
            'name': file_name,
            'mimeType': 'application/octet-stream'
        }
        
        # Upload file
        media = MediaFileUpload(file_path, resumable=True)
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        file_id = file.get('id')
        
        # Make file shareable (anyone with link can view)
        service.permissions().create(
            fileId=file_id,
            body={'type': 'anyone', 'role': 'reader'}
        ).execute()
        
        # Get shareable link
        link = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
        
        print(f"✅ File uploaded to Drive: {link}")
        return link
        
    except Exception as e:
        print(f"❌ Error uploading to Drive: {e}")
        return None

def get_file_size_mb(file_path):
    """Get file size in MB"""
    size_bytes = os.path.getsize(file_path)
    return size_bytes / (1024 * 1024)
