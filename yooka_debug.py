import requests
import uuid
import json

def test_yooka(shop_id, secret_key):
    print(f"\n--- Testing ShopID: {shop_id} ---")
    url = "https://api.yookassa.ru/v3/payments"
    idempotency_key = str(uuid.uuid4())
    
    headers = {
        "Idempotence-Key": idempotency_key,
        "Content-Type": "application/json"
    }
    
    payload = {
        "amount": {"value": "100.00", "currency": "RUB"},
        "confirmation": {"type": "redirect", "return_url": "https://t.me/agcandybot"},
        "description": "Debug test"
    }
    
    try:
        response = requests.post(
            url,
            auth=(str(shop_id), secret_key),
            headers=headers,
            data=json.dumps(payload),
            timeout=10
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    secret_key = "test_*gi5TKCX2pHYIil7C_U7R-ZPWB4BhBwqG0aFnHoIyiIc4"
    shop_ids = ["512868", "1244969", "1119574279"]
    
    for sid in shop_ids:
        test_yooka(sid, secret_key)
