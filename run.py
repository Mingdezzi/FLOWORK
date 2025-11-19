import os
from flask import Flask
from sqlalchemy import text, inspect
from flowork import create_app
from flowork.extensions import db
from config import Config

app = create_app(Config)

def auto_patch_db():
    """서버 시작 시 DB 컬럼 자동 패치 (last_message 포함)"""
    with app.app_context():
        try:
            inspector = inspect(db.engine)
            if 'products' in inspector.get_table_names():
                existing_columns = [col['name'] for col in inspector.get_columns('products')]
                
                patch_queries = []
                
                if 'image_status' not in existing_columns:
                    patch_queries.append("ALTER TABLE products ADD COLUMN image_status VARCHAR(20) DEFAULT 'READY'")
                
                if 'image_drive_link' not in existing_columns:
                    patch_queries.append("ALTER TABLE products ADD COLUMN image_drive_link VARCHAR(500)")
                    
                if 'thumbnail_url' not in existing_columns:
                    patch_queries.append("ALTER TABLE products ADD COLUMN thumbnail_url VARCHAR(500)")
                    
                if 'detail_image_url' not in existing_columns:
                    patch_queries.append("ALTER TABLE products ADD COLUMN detail_image_url VARCHAR(500)")

                # [추가] 누락되었던 last_message 컬럼 추가 로직
                if 'last_message' not in existing_columns:
                    patch_queries.append("ALTER TABLE products ADD COLUMN last_message TEXT")
                
                if patch_queries:
                    print(f"🔄 [DB Patch] {len(patch_queries)}개 컬럼 추가 중...")
                    with db.engine.connect() as conn:
                        for sql in patch_queries:
                            try:
                                conn.execute(text(sql))
                                print(f"   Query executed: {sql}")
                            except Exception as qe:
                                print(f"   Query failed: {qe}")
                        conn.commit()
                    print("✅ [DB Patch] 컬럼 추가 완료!")
                else:
                    print("✅ [DB Patch] 변경 사항 없음 (최신 상태).")
                    
        except Exception as e:
            print(f"❌ [DB Patch Error] {e}")

if __name__ == '__main__':
    # 로컬 개발 환경(python run.py 직접 실행)에서는 패치 기능 유지
    auto_patch_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
else:
    # [수정] 프로덕션(Gunicorn) 환경에서는 자동 패치 실행 제거 (부팅 속도 향상)
    pass
