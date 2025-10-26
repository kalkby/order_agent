# orders_db.py
import json
from pathlib import Path
from threading import Lock

DB_FILE = Path("orders.json")
_lock = Lock()

def _load():
    if not DB_FILE.exists():
        return {}
    return json.loads(DB_FILE.read_text())

def _save(data):
    DB_FILE.write_text(json.dumps(data, indent=2))

def add_order(order):
    with _lock:
        data = _load()
        data[order["order_id"]] = order
        _save(data)

def update_order(order_id, fields):
    with _lock:
        data = _load()
        if order_id not in data:
            return False
        data[order_id].update(fields)
        _save(data)
        return True

def get_order(order_id):
    data = _load()
    return data.get(order_id)
