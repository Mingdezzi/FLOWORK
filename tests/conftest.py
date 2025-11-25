import pytest
from flowork import create_app
from flowork.extensions import db
from flowork.models import Store, Brand, Product, Variant, StoreStock, User
from config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

@pytest.fixture
def app():
    app = create_app(TestConfig)
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def setup_data(app):
    brand = Brand(brand_name="TestBrand")
    db.session.add(brand)
    db.session.flush()
    
    store = Store(store_name="TestStore", brand_id=brand.id)
    db.session.add(store)
    db.session.flush()
    
    user = User(username="testuser", password_hash="hash", brand_id=brand.id, store_id=store.id)
    db.session.add(user)
    db.session.flush()
    
    product = Product(product_number="TEST001", product_name="Test Product", brand_id=brand.id)
    db.session.add(product)
    db.session.flush()
    
    variant = Variant(product_id=product.id, barcode="123456789", color="BLK", size="L", sale_price=10000)
    db.session.add(variant)
    db.session.flush()
    
    stock = StoreStock(store_id=store.id, variant_id=variant.id, quantity=10)
    db.session.add(stock)
    
    db.session.commit()
    
    return {
        'brand': brand,
        'store': store,
        'user': user,
        'product': product,
        'variant': variant,
        'stock': stock
    }