# assign_boards_to_user.py
"""
Assign all boards with no user (user_id=None) to a specified user.
Usage:
    python scripts/assign_boards_to_user.py <username>
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import app, db
from models import Board, User

if len(sys.argv) != 2:
    print("Usage: python scripts/assign_boards_to_user.py <username>")
    sys.exit(1)

username = sys.argv[1]

with app.app_context():
    user = User.query.filter_by(username=username).first()
    if not user:
        print(f"User '{username}' not found.")
        sys.exit(1)
    boards = Board.query.filter_by(user_id=None).all()
    if not boards:
        print("No orphaned boards found.")
        sys.exit(0)
    print(f"Assigning {len(boards)} orphaned boards to user '{username}' (id={user.id})...")
    for board in boards:
        print(f"  Assigning board '{board.title}' (id={board.id})")
        board.user_id = user.id
    db.session.commit()
    print("Done.")
