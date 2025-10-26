# main.py
import os
import uuid
from fastapi import FastAPI, BackgroundTasks, HTTPException, Header
import requests
from orders_db import add_order, update_order, get_order

# Config (read from environment)
COURIER_API_URL = os.getenv("https://my-courier-mock.free.beeceptor.com", "https://httpbin.org/post")
COURIER_API_KEY = os.getenv("COURIER_API_KEY", "")
API_SECRET = os.getenv("API_SECRET", "dev-secret")  # change in production

app = FastAPI(title="Cloud Order Agent")

def send_to_courier(order):
    payload = {
        "order_id": order["order_id"],
        "customer": order["customer"],
        "items": order["items"]
    }
    headers = {"Authorization": f"Bearer {COURIER_API_KEY}"} if COURIER_API_KEY else {}
    try:
        resp = requests.post(COURIER_API_URL, json=payload, headers=headers, timeout=15)
        if resp.status_code >= 200 and resp.status_code < 300:
            # example: generate a mock tracking id if courier doesn't return one
            tracking_id = resp.json().get("tracking_id") if isinstance(resp.json(), dict) else None
            if not tracking_id:
                tracking_id = f"{order['order_id']}-track"
            update_order(order["order_id"], {"status": "sent_to_courier", "tracking_id": tracking_id})
            print(f"[OK] Sent order {order['order_id']} -> tracking {tracking_id}")
        else:
            update_order(order["order_id"], {"status": "failed_to_send", "error": resp.text})
            print(f"[ERR] Courier responded {resp.status_code} for {order['order_id']}: {resp.text}")
    except Exception as e:
        update_order(order["order_id"], {"status": "failed_to_send", "error": str(e)})
        print(f"[EXC] Error sending {order['order_id']}: {e}")

@app.post("/order")
def create_order(payload: dict, background_tasks: BackgroundTasks, x_api_key: str | None = Header(None)):
    # Basic API key check
    if x_api_key != API_SECRET:
        raise HTTPException(status_code=403, detail="Invalid API key")
    if "customer" not in payload or "items" not in payload:
        raise HTTPException(status_code=400, detail="payload must include 'customer' and 'items'")
    order_id = str(uuid.uuid4())
    order = {
        "order_id": order_id,
        "customer": payload["customer"],
        "items": payload["items"],
        "status": "new"
    }
    add_order(order)
    background_tasks.add_task(send_to_courier, order)
    return {"message": "Order received", "order_id": order_id}

@app.get("/order/{order_id}")
def read_order(order_id: str, x_api_key: str | None = Header(None)):
    if x_api_key != API_SECRET:
        raise HTTPException(status_code=403, detail="Invalid API key")
    o = get_order(order_id)
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    return o

@app.post("/resend/{order_id}")
def resend_order(order_id: str, background_tasks: BackgroundTasks, x_api_key: str | None = Header(None)):
    if x_api_key != API_SECRET:
        raise HTTPException(status_code=403, detail="Invalid API key")
    order = get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    # set status to retrying then schedule
    update_order(order_id, {"status": "retrying"})
    background_tasks.add_task(send_to_courier, order)
    return {"message": "Resend scheduled", "order_id": order_id}
