import os
import json
import threading
from uuid import uuid4

DATA_DIR = os.path.join(os.path.dirname(__file__), 'boards_data')
BOARDS_INDEX = os.path.join(DATA_DIR, 'boards.json')
LOCK = threading.RLock()

# Ensure data dir exists
def ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    if not os.path.exists(BOARDS_INDEX):
        with open(BOARDS_INDEX, 'w') as f:
            json.dump([], f)

def list_boards():
    ensure_data_dir()
    with LOCK:
        with open(BOARDS_INDEX, 'r') as f:
            return json.load(f)

def create_board(name):
    ensure_data_dir()
    board_id = str(uuid4())
    board = {'id': board_id, 'name': name, 'thoughts': []}
    with LOCK:
        boards = list_boards()
        boards.append({'id': board_id, 'name': name})
        with open(BOARDS_INDEX, 'w') as f:
            json.dump(boards, f)
        with open(os.path.join(DATA_DIR, f'{board_id}.json'), 'w') as f:
            json.dump(board, f)
    return board_id

def get_board(board_id):
    ensure_data_dir()
    path = os.path.join(DATA_DIR, f'{board_id}.json')
    if not os.path.exists(path):
        return None
    with LOCK:
        with open(path, 'r') as f:
            return json.load(f)

def save_board(board):
    ensure_data_dir()
    path = os.path.join(DATA_DIR, f"{board['id']}.json")
    with LOCK:
        with open(path, 'w') as f:
            json.dump(board, f)

def delete_board(board_id):
    ensure_data_dir()
    with LOCK:
        # Remove from boards.json
        boards = list_boards()
        boards = [b for b in boards if b['id'] != board_id]
        with open(BOARDS_INDEX, 'w') as f:
            json.dump(boards, f)
        # Remove board file
        board_file = os.path.join(DATA_DIR, f'{board_id}.json')
        if os.path.exists(board_file):
            os.remove(board_file)

def import_board(board_data):
    ensure_data_dir()
    orig_name = board_data.get('name', 'Imported Board')
    name = orig_name
    boards = list_boards()
    names = {b['name'] for b in boards}
    i = 1
    while name in names:
        name = f"{orig_name} ({i})"
        i += 1
    board_id = str(uuid4())
    board = {'id': board_id, 'name': name, 'thoughts': board_data.get('thoughts', [])}
    with LOCK:
        boards.append({'id': board_id, 'name': name})
        with open(BOARDS_INDEX, 'w') as f:
            json.dump(boards, f)
        with open(os.path.join(DATA_DIR, f'{board_id}.json'), 'w') as f:
            json.dump(board, f)
    return board_id
