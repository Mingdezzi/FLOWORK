import click
from flask.cli import with_appcontext
from .extensions import db
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
    print("Dropping all tables...")
    db.drop_all()
    print("Creating all tables...")
    db.create_all()
    print("✅ 모든 DB 테이블 초기화 완료. (모든 데이터 삭제됨)")

@click.command("update-db")
@with_appcontext
def update_db_command():
    print("Checking and creating missing tables...")
    db.create_all()
    print("✅ DB 업데이트 완료. (누락된 테이블 생성됨)")