#!/usr/bin/env python3
"""
Simple script to initialize the database with the new schema
"""
from app import app, db

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("✅ Database created successfully with created_at field!")
