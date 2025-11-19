import os
from flask import Flask
from sqlalchemy import text, inspect
from flowork import create_app
from flowork.extensions import db
from config import Config

app = create_app(Config)

def auto_patch_db():
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
                
                if patch_queries:
                    print(f"DB Patch: Adding {len(patch_queries)} missing columns...")
                    with db.engine.connect() as conn:
                        for sql in patch_queries:
                            conn.execute(text(sql))
                        conn.commit()
                    print("DB Patch: Completed.")
                else:
                    print("DB Patch: No changes needed.")
                    
        except Exception as e:
            print(f"DB Patch Error: {e}")

if __name__ == '__main__':
    auto_patch_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
else:
    auto_patch_db()
