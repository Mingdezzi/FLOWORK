import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from flask import current_app

SCOPES = ['https://www.googleapis.com/auth/drive.file']

def get_drive_service():
    creds_path = os.path.join(current_app.root_path, '..', 'service_account.json')
    
    if not os.path.exists(creds_path):
        print(f"Service account file not found: {creds_path}")
        return None
        
    creds = service_account.Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

def get_or_create_folder(service, folder_name, parent_id=None):
    query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
        
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get('files', [])
    
    if files:
        return files[0]['id']
    else:
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_id:
            file_metadata['parents'] = [parent_id]
        
        folder = service.files().create(body=file_metadata, fields='id').execute()
        return folder.get('id')

def upload_file_to_drive(service, file_path, filename, parent_id=None):
    if not service:
        return None

    file_metadata = {'name': filename}
    if parent_id:
        file_metadata['parents'] = [parent_id]
        
    media = MediaFileUpload(file_path, resumable=True)
    
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, webContentLink'
    ).execute()
    
    service.permissions().create(
        fileId=file.get('id'),
        body={'type': 'anyone', 'role': 'reader'}
    ).execute()
    
    return file.get('webContentLink')