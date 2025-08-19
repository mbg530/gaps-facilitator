#!/usr/bin/env python3
"""
Debug script to check user admin status in Flask context
"""
import os
import sys

# Set environment variable to avoid OpenAI API key error
os.environ['OPENAI_API_KEY'] = 'dummy-key-for-debug'

try:
    from app import app, db
    from models import User
    
    with app.app_context():
        # Query the user
        user = User.query.filter_by(username='mbg530').first()
        
        if user:
            print(f"User found: {user.username}")
            print(f"User ID: {user.id}")
            print(f"User email: {user.email}")
            print(f"is_admin attribute: {user.is_admin}")
            print(f"is_admin type: {type(user.is_admin)}")
            print(f"is_admin bool(): {bool(user.is_admin)}")
            print(f"is_admin == True: {user.is_admin == True}")
            print(f"is_admin is True: {user.is_admin is True}")
        else:
            print("User 'mbg530' not found!")
            
        # Also check all users
        all_users = User.query.all()
        print(f"\nAll users in database:")
        for u in all_users:
            print(f"  {u.username}: is_admin={u.is_admin} (type: {type(u.is_admin)})")
            
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
