#!/usr/bin/env python3
"""
Standalone test to verify Board model with created_at field
"""
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Create a fresh Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test_database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Create a fresh db instance
db = SQLAlchemy(app)

# Define the Board model directly here to avoid import issues
class Board(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())

if __name__ == '__main__':
    # Remove any existing test database
    if os.path.exists('test_database.db'):
        os.remove('test_database.db')
    
    with app.app_context():
        print("✅ Creating database with Board model...")
        db.create_all()
        
        # Verify the schema
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        columns = inspector.get_columns('board')
        column_names = [col['name'] for col in columns]
        print(f"📋 Board columns: {column_names}")
        
        if 'created_at' in column_names:
            print("🎉 SUCCESS: created_at column is present!")
            
            # Test creating a board
            test_board = Board(title="Test Board", user_id=1)
            db.session.add(test_board)
            db.session.commit()
            print(f"✅ Test board created with ID: {test_board.id}")
            print(f"📅 Created at: {test_board.created_at}")
            
        else:
            print("❌ FAILED: created_at column is missing!")
            print("Available columns:", column_names)
