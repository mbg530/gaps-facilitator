#!/usr/bin/env python3
"""
Fix admin status for mbg530 user using Flask ORM
"""
import os

# Set environment variable to avoid OpenAI API key error
os.environ['OPENAI_API_KEY'] = 'dummy-key-for-debug'

try:
    from app import app, db
    from models import User
    
    with app.app_context():
        # Find the user
        user = User.query.filter_by(username='mbg530').first()
        
        if user:
            print(f"Before: {user.username} is_admin={user.is_admin}")
            
            # Update admin status using ORM
            user.is_admin = True
            db.session.commit()
            
            print(f"After: {user.username} is_admin={user.is_admin}")
            
            # Verify the change
            user_check = User.query.filter_by(username='mbg530').first()
            print(f"Verification: {user_check.username} is_admin={user_check.is_admin}")
            
        else:
            print("User 'mbg530' not found!")
            
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
