from datetime import datetime
from ..extensions import db

class Suggestion(db.Model):
    __tablename__ = 'suggestions'
    id = db.Column(db.Integer, primary_key=True)
    brand_id = db.Column(db.Integer, db.ForeignKey('brands.id'), nullable=False, index=True)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=True) 
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_private = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.now)
    store = db.relationship('Store', backref='suggestions')
    comments = db.relationship('SuggestionComment', backref='suggestion', lazy='dynamic', cascade="all, delete-orphan")

class SuggestionComment(db.Model):
    __tablename__ = 'suggestion_comments'
    id = db.Column(db.Integer, primary_key=True)
    suggestion_id = db.Column(db.Integer, db.ForeignKey('suggestions.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.now)
    user = db.relationship('User')

class StoreMail(db.Model):
    __tablename__ = 'store_mails'
    id = db.Column(db.Integer, primary_key=True)
    brand_id = db.Column(db.Integer, db.ForeignKey('brands.id'), nullable=False, index=True)
    sender_store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=True)
    receiver_store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.now)
    sender_store = db.relationship('Store', foreign_keys=[sender_store_id], backref='sent_mails')
    receiver_store = db.relationship('Store', foreign_keys=[receiver_store_id], backref='received_mails')