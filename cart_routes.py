# cart_routes.py
import os
import re
import json
from datetime import datetime
from flask import Blueprint, render_template_string, redirect, url_for, request
from auth import auth
from config import OUTPUTS_DIR
from utils import extract_with_regex, save_status
from generators import make_pdf, make_merged_pdf, write_csv, write_merged_csv
from templates import NAV_HTML, CART_HTML

cart_bp = Blueprint('cart_bp', __name__)

@cart_bp.route('/cart')
@auth.login_required
def cart_index():
    return render_template_string(CART_HTML, nav_html=NAV_HTML)

@cart_bp.route('/process', methods=['GET','POST'])
@auth.login_required
def process_order():
    # redirect bare GET to the form
    if request.method == 'GET':
        return redirect(url_for('cart_bp.cart_index'))

    order      = request.form['order_number'].strip()
    files      = request.files.getlist('files')
    names      = request.form.getlist('customer_names')
    oos_counts = request.form.getlist('oos_counts')
    base       = os.path.join(OUTPUTS_DIR, order)

    # ensure our output folders exist
    for sub in ('individual/pdf','individual/csv','merged/pdf','merged/csv'):
        os.makedirs(os.path.join(base, sub), exist_ok=True)

    # will hold customer→out-of-stock count
    meta = {}

    merged_items = []
    today        = datetime.now().strftime('%Y-%m-%d')

    # process each uploaded HTML
    for f, cust, oos in zip(files, names, oos_counts):
        html = f.read().decode('utf-8')
        items = extract_with_regex(html)
        if not items:
            continue

        # build your safe filename base: e.g. "Ossi_Krikorian-2025-06-19"
        safe = re.sub(r'\W+', '_', cust)
        filename_base = f"{safe}-{today}"

        # record Out-of-Stock under that same key
        meta[filename_base] = int(oos)

        # now generate PDF/CSV paths using the same base
        pdf_path = os.path.join(base, 'individual', 'pdf', f"{filename_base}.pdf")
        csv_path = os.path.join(base, 'individual', 'csv', f"{filename_base}.csv")

        make_pdf(items, cust, pdf_path, oos)
        write_csv(items, cust, csv_path)

        for it in items:
            merged_items.append({
                'goods_sn': it['goods_sn'],
                'quantity': it['quantity'],
                'price': it['price'],
                'customer': cust
            })

    # merged outputs if any
    if merged_items:
        mpdf = os.path.join(base, 'merged', 'pdf',   f'{order}-merged-{today}.pdf')
        mcsv = os.path.join(base, 'merged', 'csv',   f'{order}-merged-{today}.csv')
        make_merged_pdf(merged_items, order, mpdf)
        write_merged_csv(merged_items, mcsv)

    # write metadata.json for OOS counts
    meta_path = os.path.join(base, 'individual', 'metadata.json')
    with open(meta_path, 'w', encoding='utf-8') as mf:
        json.dump(meta, mf)

    # mark order pending and redirect
    save_status(base, 'pending')
    return redirect(url_for('dashboard_bp.dashboard'))
