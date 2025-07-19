from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    boards = db.relationship('Board', backref='user', lazy=True)
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Board(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    thoughts = db.relationship('Thought', backref='board', lazy=True, passive_deletes=True)
    minutes = db.relationship('MeetingMinute', backref='board', lazy=True, passive_deletes=True)

class Thought(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(500), nullable=False)
    quadrant = db.Column(db.String(20), nullable=False)  # status, goal, analysis, plan
    board_id = db.Column(db.Integer, db.ForeignKey('board.id', ondelete='CASCADE'), nullable=False)

class MeetingMinute(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    board_id = db.Column(db.Integer, db.ForeignKey('board.id', ondelete='CASCADE'), nullable=False)
    action = db.Column(db.String(50), nullable=False)  # e.g., 'add', 'edit', 'delete', 'move', 'ai_suggest', etc.
    detail = db.Column(db.Text, nullable=False)

class ConversationTurn(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    board_id = db.Column(db.Integer, db.ForeignKey('board.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=True)
    role = db.Column(db.String(16), nullable=False)  # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
