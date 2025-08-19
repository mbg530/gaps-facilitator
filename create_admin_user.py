# create_admin_user.py

import os
from app import app, db
from models import User

# Set a dummy OpenAI API key if not already set (prevents import errors)
os.environ.setdefault("OPENAI_API_KEY", "dummy")

def create_admin(username, email, password):
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if user:
            print(f"User '{username}' already exists. Updating to admin.")
            user.is_admin = True
            user.set_password(password)
        else:
            user = User(username=username, email=email, is_admin=True)
            user.set_password(password)
            db.session.add(user)
        db.session.commit()
        print(f"Admin user '{username}' created/updated.")

if __name__ == "__main__":
    # Edit these values as needed
    create_admin("Brad", "bffishel@gmail.com", "2917")
