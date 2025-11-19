import click
from flask import Flask
from sqlalchemy import text, inspect
from sqlalchemy.schema import CreateTable
from flowork import create_app
from flowork.extensions import db
from config import Config

# 모든 모델을 불러와야 메타데이터에 등록됩니다.
from flowork.models import * app = create_app(Config)

def get_column_type(column):
    """SQLAlchemy 컬럼 타입 객체를 SQL 문자열로 변환"""
    return column.type.compile(db.engine.dialect)

@click.command()
@click.option('--force', is_flag=True, help='확인 절차 없이 강제로 실행합니다.')
def sync_db(force):
    """
    DB 스키마 동기화 도구 (Development Tool)
    - 누락된 테이블 생성
    - 누락된 컬럼 추가
    - (옵션) 불필요한 테이블/컬럼 삭제 제안
    """
    with app.app_context():
        inspector = inspect(db.engine)
        
        # 1. 현재 DB와 모델의 테이블 목록 비교
        db_tables = set(inspector.get_table_names())
        model_tables = set(db.metadata.tables.keys())

        print("=" * 50)
        print(f"📡 DB 연결 확인: {db.engine.url}")
        print("=" * 50)

        # --- A. 테이블 생성 (Missing Tables) ---
        missing_tables = model_tables - db_tables
        if missing_tables:
            print(f"➕ [테이블 생성] 누락된 테이블 발견: {', '.join(missing_tables)}")
            if force or click.confirm("   >> 위 테이블들을 생성하시겠습니까?"):
                try:
                    # create_all은 이미 존재하는 테이블은 건너뛰고 없는 것만 만듭니다.
                    db.create_all()
                    print("   ✅ 테이블 생성 완료")
                except Exception as e:
                    print(f"   ❌ 생성 실패: {e}")
        else:
            print("✅ 모든 모델 테이블이 DB에 존재합니다.")

        print("-" * 50)

        # --- B. 컬럼 동기화 (Table Columns) ---
        print("🔍 테이블별 컬럼 검사 중...")
        
        for table_name in model_tables:
            if table_name not in db_tables:
                continue  # 방금 생성되지 않았다면 스킵

            # DB 컬럼 정보 조회
            db_cols_info = inspector.get_columns(table_name)
            db_col_names = {col['name'] for col in db_cols_info}
            
            # 모델 컬럼 정보 조회
            model_table = db.metadata.tables[table_name]
            model_col_names = {col.name for col in model_table.columns}

            # 1. 누락된 컬럼 추가 (Add Columns)
            missing_cols = model_col_names - db_col_names
            if missing_cols:
                print(f"   👉 [{table_name}] 누락된 컬럼: {', '.join(missing_cols)}")
                if force or click.confirm(f"      >> '{table_name}' 테이블에 컬럼을 추가하시겠습니까?"):
                    with db.engine.connect() as conn:
                        for col_name in missing_cols:
                            col = model_table.columns[col_name]
                            col_type = get_column_type(col)
                            
                            # DEFAULT 값 처리 (간단한 경우만)
                            default_stmt = ""
                            if col.server_default:
                                default_stmt = f" DEFAULT {col.server_default.arg}"
                            
                            # NULL 허용 여부
                            nullable_stmt = "NULL" if col.nullable else "NOT NULL"
                            if not col.nullable and not col.server_default and not col.default:
                                # 기존 데이터가 있는데 NOT NULL을 추가하면 에러나므로 임시로 NULL 허용
                                print(f"      ⚠️ 경고: '{col_name}'은 NOT NULL이지만 기본값이 없어 NULL로 생성합니다.")
                                nullable_stmt = "NULL"

                            sql = f'ALTER TABLE "{table_name}" ADD COLUMN "{col_name}" {col_type} {nullable_stmt}{default_stmt}'
                            try:
                                conn.execute(text(sql))
                                print(f"      ✅ 추가됨: {col_name}")
                            except Exception as e:
                                print(f"      ❌ 실패 ({col_name}): {e}")
                        conn.commit()

            # 2. 불필요한 컬럼 감지 (Extra Columns - 삭제는 신중하게)
            extra_cols = db_col_names - model_col_names
            if extra_cols:
                print(f"   🗑️  [{table_name}] DB에만 있는 컬럼 (삭제 대상?): {', '.join(extra_cols)}")
                # 자동 삭제는 위험하므로 알림만 주거나 명시적 동의 필요
                # if click.confirm(f"      >> 위험! '{table_name}'에서 위 컬럼들을 삭제하시겠습니까?"):
                #     ...

        print("-" * 50)

        # --- C. 불필요한 테이블 (Extra Tables) ---
        extra_tables = db_tables - model_tables
        # alembic_version 등 시스템 테이블 제외
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
