export OPENAI_API_KEY=dummy
python3 -c "
from app import app, db
from models import User
with app.app_context():
    user = User.query.filter_by(username='mbg530').first()
    if user:
        print(f'User: {user.username}')
        print(f'is_admin: {user.is_admin}')
        print(f'has is_admin attr: {hasattr(user, \"is_admin\")}')
    else:
        print('User not found')
"
