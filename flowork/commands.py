import click
from flask.cli import with_appcontext
from .extensions import db
# [수정] 모든 모델을 가져오도록 변경 (새로 추가된 모델들이 누락되지 않게)
from .models import (
    Brand, Store, User, Product, Variant, StoreStock, StockHistory,
    Order, OrderProcessing, Sale, SaleItem,
    Staff, ScheduleEvent, Setting, Announcement, Comment,
    StockTransfer, Customer, Repair,
    Attendance, CompetitorBrand, CompetitorSale,
    Suggestion, SuggestionComment, StoreMail,
    StoreOrder, StoreReturn
)

@click.command("init-db")
@with_appcontext
def init_db_command():
    """기존 데이터를 삭제하고 새 테이블을 생성합니다."""
    print("Dropping all tables...")
    db.drop_all() 
    print("Creating all tables...")
    db.create_all() 
    print("✅ 모든 DB 테이블 초기화 완료. (모든 데이터 삭제됨)")

# [추가] 기존 데이터를 유지하면서 누락된 테이블만 생성하는 명령어
@click.command("update-db")
@with_appcontext
def update_db_command():
    """삭제 없이 누락된 새 테이블만 생성합니다."""
    print("Checking and creating missing tables...")
    db.create_all()
    print("✅ DB 업데이트 완료. (누락된 테이블 생성됨)")