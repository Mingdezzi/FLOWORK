import subprocess
from datetime import datetime
from flowork.extensions import db
from flowork.models import UpdateLog

class VersionService:
    @staticmethod
    def get_latest_version():
        last_log = UpdateLog.query.order_by(UpdateLog.id.desc()).first()
        return last_log.version if last_log else "0.0.0"

    @staticmethod
    def generate_auto_log(user_id):
        try:
            # 1. 마지막 업데이트 로그 확인
            last_log = UpdateLog.query.order_by(UpdateLog.id.desc()).first()
            last_date = last_log.created_at.strftime('%Y-%m-%d %H:%M:%S') if last_log else "1970-01-01"

            # 2. Git 로그 가져오기 (마지막 업데이트 이후의 커밋만)
            # 포맷: " hash - message (author)"
            cmd = f'git log --pretty=format:"- %s (%an)" --since="{last_date}"'
            result = subprocess.check_output(cmd, shell=True).decode('utf-8').strip()

            if not result:
                return {'status': 'info', 'message': '새로운 변경 사항(커밋)이 없습니다.'}

            # 3. 새 버전 번호 생성 (단순하게 마이너 버전 +1)
            current_ver = last_log.version if last_log else "1.0.0"
            major, minor, patch = map(int, current_ver.split('.'))
            new_version = f"{major}.{minor}.{patch + 1}"

            # 4. DB 저장
            new_log = UpdateLog(
                version=new_version,
                title=f"자동 업데이트 ({datetime.now().strftime('%Y-%m-%d')})",
                content=result,
                created_by_id=user_id
            )
            db.session.add(new_log)
            db.session.commit()

            return {
                'status': 'success', 
                'message': f'새 버전({new_version}) 업데이트 로그가 생성되었습니다.',
                'log': {
                    'version': new_log.version,
                    'title': new_log.title,
                    'content': new_log.content,
                    'date': new_log.created_at.strftime('%Y-%m-%d')
                }
            }

        except Exception as e:
            return {'status': 'error', 'message': f'로그 생성 실패: {str(e)}'}