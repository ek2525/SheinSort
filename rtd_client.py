# rtd_client.py
import os

import requests, logging

from utils import mark_order_as_sent

RTD_API_BASE = os.getenv('RTD_API_BASE', 'https://app.rtdeliveries.net/api/v10')
RTD_API_KEY = os.getenv('RTD_API_KEY', 'rtd-merchant-123456')
RTD_EMAIL = os.getenv('RTD_EMAIL', 'info@shipbee-lb.com')
RTD_PASSWORD = os.getenv('RTD_PASSWORD', 'hh6Xc#y!m02xAao2')
RTD_SHOP_ID = int(os.getenv('RTD_SHOP_ID', '987'))  # your shop ID


def auth_rtd():
    url = f"{RTD_API_BASE}/merchant/signin"
    headers = {
        'apiKey': RTD_API_KEY,
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    resp = requests.post(url, headers=headers,
                         json={'email': RTD_EMAIL, 'password': RTD_PASSWORD})
    resp.raise_for_status()
    token = resp.json()['data']['auth_token']
    logging.info("Authenticated to RTD.")
    return token


def create_rtd_parcel(token, order: dict):
    url = f"{RTD_API_BASE}/parcel-create"
    headers = {
        'apiKey': RTD_API_KEY,
        'Authorization': f"Bearer {token}",
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    quantity = int(order['Number of Items'])
    payload = {
        'shop_id': RTD_SHOP_ID,
        'delivery_type_id': 3,
        'delivery_priority_id': 2,
        'special_request_id': 4,
        'customer_name': order['Customer Full Name'],
        'customer_phone': order['Phone Number'],
        'customer_address': order['Written Address'],
        'cash_collection': order['Sold Price'] - order['Amount Paid Whish'],
        'currency_type': 1,
        'note': f"{quantity} items \nCall Before Coming"
    }
    r = requests.post(url, json=payload, headers=headers)
    r.raise_for_status()
    logging.info(f"Created RTD parcel for {order['Customer Full Name']}.")
    # mark_order_as_sent(order['id'])
    return r.json()
