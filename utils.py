# utils.py
import os, json, re
import random
from typing import Optional, List

import pandas as pd
from io import BytesIO
import requests

from config import STATUS_FILE


def load_status(order_dir):
    path = os.path.join(order_dir, STATUS_FILE)
    if os.path.isfile(path):
        try:
            return json.load(open(path)).get('status', 'pending')
        except:
            return 'pending'
    return 'pending'

def save_status(order_dir, status):
    with open(os.path.join(order_dir, STATUS_FILE), 'w') as f:
        json.dump({'status': status}, f)

def extract_with_regex(html):
    sns    = re.findall(r'"goods_sn"\s*:\s*"([^"]+)"', html)
    qtys   = re.findall(r'"quantity"\s*:\s*"([^"]+)"', html)
    names  = re.findall(r'"goods_name"\s*:\s*"([^"]+)"', html)
    # Try after coupon price first
    estimated_prices = re.findall(r'"estimatedPrice"\s*:\s*\{[^\}]*"amount"\s*:\s*"([\d.]+)"', html)
    # Fallback: discounted price
    unit_prices = re.findall(r'"unitPrice"\s*:\s*\{[^\}]*"amount"\s*:\s*"([\d.]+)"', html)

    prices = []
    for i in range(len(sns)):
        # If estimated (after coupon) price exists for this item, use it
        if i < len(estimated_prices) and estimated_prices[i]:
            prices.append(estimated_prices[i])
        # else, if unit price exists, use it
        elif i < len(unit_prices) and unit_prices[i]:
            prices.append(unit_prices[i])
        else:
            prices.append('')

    return [
        {'goods_sn': sn, 'quantity': q, 'name': nm, 'price': pr}
        for sn, q, nm, pr in zip(sns, qtys, names, prices)
    ]

SHARE_LINK = (
    "https://arcshields-my.sharepoint.com/:x:/p/ekaram/ETxBxNWicw9OrpqpjhkjLj4BR_J0oYV68tvEEc3k2znHFA?e=WTxaFp"
)
# Force direct download
DOWNLOAD_URL = f"{SHARE_LINK}&download=1"

# Caches the DataFrame load on import to avoid repeated fetch
_xls = None
_df_lines = None
_df_base = None


def _load_sheets():
    global _xls, _df_lines, _df_base
    if _xls is None:
        resp = requests.get(DOWNLOAD_URL)
        resp.raise_for_status()
        _xls = pd.ExcelFile(BytesIO(resp.content), engine="openpyxl")
        # ensure headers exactly match sheet
        _df_lines = pd.read_excel(_xls, sheet_name="Customer_Lines")
        _df_base  = pd.read_excel(_xls, sheet_name="Customer Base")
    return _df_lines, _df_base


def get_order_shipping_info(order_id: str):
    """
    Returns a list of dicts with keys:
      - Customer Full Name
      - Phone Number
      - Written Address
      - Sold Price
    for any rows in Customer_Lines where OrderNumber contains the given order_id substring.
    """
    df_lines, df_base = _load_sheets()
    # filter for rows where OrderNumber contains the search term
    primary_id = order_id.split(",")[0].strip()
    rows = df_lines[df_lines["OrderNumber"].astype(str) == primary_id]
    # merge on the common "Customer Full Name" column
    merged = rows.merge(
        df_base,
        left_on="Customer Full Name",
        right_on="Customer Full Name",
        how="left"
    )
    if "Amount Paid Whish" in merged.columns:
        merged["Amount Paid Whish"] = merged["Amount Paid Whish"].fillna(0)
    # select and return only the needed fields
    return merged[[
        "Customer Full Name",
        "Phone Number",
        "Written Address",
        "Sold Price",
        "Amount Paid Whish",
        "Number of Items",
        "Google Maps Link"
    ]].to_dict(orient="records")


def mark_order_as_sent(order_id: str):
    # TODO: implement persistence for sent parcels
    pass

# --- TinyURL Shortening -----------------------------------------------
# Replace with your actual TinyURL API key
TINYURL_API_KEY = "E63CBepjwNES5ItSNBNnBB3hAo2mMwqY7UvrBMqhzM79XTshCCKcpE4DWeVf"
TINYURL_CREATE_ENDPOINT = "https://api.tinyurl.com/create"


def generate_alias(name: str) -> str:
    """
    Generate an alias by removing spaces and appending 5 random digits.
    """
    base = name.replace(' ', '')
    rand_suffix = f"{random.randint(0, 99999):05d}"
    return f"{base}{rand_suffix}"


def shorten_url(
    long_url: str,
    domain: str = "tinyurl.com",
    alias: Optional[str] = None,
    tags: Optional[List[str]] = None,
    expires_at: Optional[str] = None,
    description: Optional[str] = None
) -> str:
    """
    Shortens the given long URL using the TinyURL API and returns the shortened URL.
    Optional parameters:
      - domain: e.g. "tinyurl.com" or a custom domain
      - alias: to reserve a specific alias
      - tags: list of tags for categorization
      - expires_at: ISO timestamp when link should expire
      - description: a text description for the link
    """
    headers = {
        'Authorization': f'Bearer {TINYURL_API_KEY}',
        'Content-Type': 'application/json'
    }
    payload = {'url': long_url, 'domain': domain}
    if alias:
        payload['alias'] = alias
    if tags:
        payload['tags'] = ','.join(tags)
    if expires_at:
        payload['expires_at'] = expires_at
    if description:
        payload['description'] = description

    resp = requests.post(TINYURL_CREATE_ENDPOINT, json=payload, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    return data.get('data', {}).get('tiny_url', long_url)
