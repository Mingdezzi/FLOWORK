import click
from flask import Flask
from sqlalchemy import text, inspect
from sqlalchemy.schema import CreateTable
from flowork import create_app
from flowork.extensions import db
from config import Config
from flowork.models import *

app = create_app(Config)

def get_column_type(column):
    return column.type.compile(db.engine.dialect)

@click.command()
@click.option('--force', is_flag=True, help='확인 절차 없이 강제로 실행합니다.')
def sync_db(force):
    with app.app_context():
        inspector = inspect(db.engine)
        
        db_tables = set(inspector.get_table_names())
        model_tables = set(db.metadata.tables.keys())

        print("=" * 50)
        print(f"📡 DB 연결 확인: {db.engine.url}")
        print("=" * 50)

        missing_tables = model_tables - db_tables
        if missing_tables:
            print(f"➕ [테이블 생성] 누락된 테이블 발견: {', '.join(missing_tables)}")
            if force or click.confirm("   >> 위 테이블들을 생성하시겠습니까?"):
                try:
                    db.create_all()
                    print("   ✅ 테이블 생성 완료")
                except Exception as e:
                    print(f"   ❌ 생성 실패: {e}")
        else:
            print("✅ 모든 모델 테이블이 DB에 존재합니다.")

        print("-" * 50)

        print("🔍 테이블별 컬럼 검사 중...")
        
        for table_name in model_tables:
            if table_name not in db_tables:
                continue

            db_cols_info = inspector.get_columns(table_name)
            db_col_names = {col['name'] for col in db_cols_info}
            
            model_table = db.metadata.tables[table_name]
            model_col_names = {col.name for col in model_table.columns}

            missing_cols = model_col_names - db_col_names
            if missing_cols:
                print(f"   👉 [{table_name}] 누락된 컬럼: {', '.join(missing_cols)}")
                if force or click.confirm(f"      >> '{table_name}' 테이블에 컬럼을 추가하시겠습니까?"):
                    with db.engine.connect() as conn:
                        for col_name in missing_cols:
                            col = model_table.columns[col_name]
                            col_type = get_column_type(col)
                            
                            default_stmt = ""
                            if col.server_default:
                                default_stmt = f" DEFAULT {col.server_default.arg}"
                            
                            nullable_stmt = "NULL" if col.nullable else "NOT NULL"
                            if not col.nullable and not col.server_default and not col.default:
                                print(f"      ⚠️ 경고: '{col_name}'은 NOT NULL이지만 기본값이 없어 NULL로 생성합니다.")
                                nullable_stmt = "NULL"

                            sql = f'ALTER TABLE "{table_name}" ADD COLUMN "{col_name}" {col_type} {nullable_stmt}{default_stmt}'
                            try:
                                conn.execute(text(sql))
                                print(f"      ✅ 추가됨: {col_name}")
                            except Exception as e:
                                print(f"      ❌ 실패 ({col_name}): {e}")
                        conn.commit()

            extra_cols = db_col_names - model_col_names
            if extra_cols:
                print(f"   🗑️  [{table_name}] DB에만 있는 컬럼 (삭제 대상?): {', '.join(extra_cols)}")

        print("-" * 50)

        extra_tables = db_tables - model_tables
        extra_tables = {t for t in extra_tables if t != 'alembic_version'}
        
        if extra_tables:
            print(f"❓ [미정의 테이블] 모델에 없는 테이블 발견: {', '.join(extra_tables)}")
            if click.confirm("   >> ⚠️ 주의: 이 테이블들을 DB에서 삭제(DROP) 하시겠습니까? (데이터가 유실됩니다)"):
                with db.engine.connect() as conn:
                    for table in extra_tables:
                        try:
                            conn.execute(text(f'DROP TABLE "{table}" CASCADE'))
                            print(f"   🗑️  삭제됨: {table}")
                        except Exception as e:
                            print(f"   ❌ 삭제 실패 ({table}): {e}")
                    conn.commit()
        else:
            print("✨ 불필요한 테이블이 없습니다.")

        print("=" * 50)
        print("🚀 동기화 작업 완료")

if __name__ == '__main__':
    sync_db()