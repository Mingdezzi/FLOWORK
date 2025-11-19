import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from flask import current_app

SCOPES = ['https://www.googleapis.com/auth/drive.file']

def get_drive_service(key_filename=None):
    """
    구글 드라이브 서비스 객체 생성
    key_filename: 서비스 계정 키 파일 이름 (예: 'EIDERGOOGLE.json')
    None이면 기본 'service_account.json'을 찾습니다.
    """
    # 프로젝트 루트(/app)에서 파일을 찾습니다.
    if key_filename:
        creds_path = os.path.join(current_app.root_path, '..', key_filename)
    else:
        creds_path = os.path.join(current_app.root_path, '..', 'service_account.json')
    
    if not os.path.exists(creds_path):
        print(f"❌ 구글 인증 키 파일을 찾을 수 없습니다: {creds_path}")
        return None
        
    try:
        creds = service_account.Credentials.from_service_account_file(creds_path, scopes=SCOPES)
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        print(f"❌ 구글 드라이브 인증 오류 ({key_filename}): {e}")
        return None

def get_or_create_folder(service, folder_name, parent_id=None):
    """폴더가 있으면 ID 반환, 없으면 생성 후 ID 반환"""
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
    """파일 업로드 및 webContentLink(다운로드/표시용 링크) 반환"""
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
    
    # 권한 설정: 링크가 있는 누구나 읽기 가능 (이미지 호스팅용)
    service.permissions().create(
        fileId=file.get('id'),
        body={'type': 'anyone', 'role': 'reader'}
    ).execute()
    
    return file.get('webContentLink')