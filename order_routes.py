import base64
import os
import json
import csv
import shutil
import logging
from urllib.parse import quote
import io, qrcode
import requests
from flask import (
    Blueprint, redirect, url_for, abort,
    render_template_string, request, send_from_directory, flash, send_file, Response
)
from auth import auth
from config import OUTPUTS_DIR
from utils import save_status, get_order_shipping_info, mark_order_as_sent, shorten_url, generate_alias
from rtd_client import auth_rtd, create_rtd_parcel
from templates import NAV_HTML, CUSTOMER_HTML, EDIT_HTML

# Unified blueprint for order-related routes
orders_bp = Blueprint('order_routes', __name__, url_prefix='/order')


@orders_bp.route('/<order>/delete')
@auth.login_required
def delete_order(order):
    base = os.path.join(OUTPUTS_DIR, order)
    shutil.rmtree(base, ignore_errors=True)
    return redirect(url_for('dashboard_bp.dashboard'))


@orders_bp.route('/<order>/status/<new_status>')
@auth.login_required
def change_status(order, new_status):
    base = os.path.join(OUTPUTS_DIR, order)
    if os.path.isdir(base) and new_status in ('pending', 'checked'):
        save_status(base, new_status)
    return redirect(url_for('dashboard_bp.dashboard'))


@orders_bp.route('/<order>/edit', methods=['GET', 'POST'])
@auth.login_required
def edit_order(order):
    base = os.path.join(OUTPUTS_DIR, order)
    if not os.path.isdir(base):
        abort(404)
    if request.method == 'POST':
        new = request.form['new_order'].strip()
        new_dir = os.path.join(OUTPUTS_DIR, new)
        if not os.path.exists(new_dir):
            os.rename(base, new_dir)
            return redirect(url_for('dashboard_bp.dashboard'))
        return f"Order '{new}' exists", 400
    return render_template_string(EDIT_HTML, nav_html=NAV_HTML, order=order)


@orders_bp.route('/<order>/merged.pdf')
@auth.login_required
def download_merged_pdf(order):
    path = os.path.join(OUTPUTS_DIR, order, 'merged', 'pdf')
    pdfs = [f for f in sorted(os.listdir(path)) if f.endswith('.pdf')]
    if not pdfs:
        abort(404)
    return send_from_directory(path, pdfs[-1], as_attachment=False)


@orders_bp.route('/<order>/customers', methods=['GET'])
@auth.login_required
def view_customers(order):
    # Load shipping records from Excel
    try:
        shipping_recs = get_order_shipping_info(order)
    except Exception:
        shipping_recs = []

    # A) Shipping Label Dropdown
    dropdown_html = ''
    if shipping_recs:
        action_url = url_for('order_routes.print_customer_label', order=order, cust='__CUST__')
        # Build options with computed remaining
        options_list = []
        for rec in shipping_recs:
            name = rec.get('Customer Full Name', '')
            sold = rec.get('Sold Price', 0) or 0
            whish = rec.get('Amount Paid Whish', 0) or 0
            quantity = int(rec.get('Number of Items', ''))
            amount_due = sold - whish
            address = rec.get('Written Address', '')
            options_list.append(
                f'<option value="{name}">{name} ({quantity} items) ($ {amount_due}) {address}</option>'
            )
        options = '\n'.join(options_list)
        dropdown_html = f"""
        <form id="excel-select-form" class="mb-4" method="get" action="{action_url}">
          <div class="form-group">
            <label>Select customer:</label>
            <select id="cust-select" class="form-control">{options}</select>
          </div>
          <button class="btn btn-sm btn-success">Create Shipping Label</button>
        </form>
        <script>
          document.getElementById('excel-select-form').addEventListener('submit', e => {{
            e.preventDefault();
            const cust = encodeURIComponent(document.getElementById('cust-select').value);
            const url = e.target.action.replace('__CUST__', cust);
            window.location.href = url;
          }});
        </script>
        """

    # B) Label Creation Dropdown
    label_dropdown_html = ''
    if shipping_recs:
        label_action = url_for('order_routes.render_label', order=order, cust='__CUST__')
        opts = []
        for rec in shipping_recs:
            sold = rec.get('Sold Price', 0) or 0
            whish = rec.get('Amount Paid Whish', 0) or 0
            amount_due = sold - whish
            address = rec.get('Written Address', '')
            quantity = int(rec.get('Number of Items', ''))
            name = rec.get('Customer Full Name', '')
            opts.append(f'<option value="{name}">{name} ({quantity} items) ($ {amount_due}) {address}</option>')
        label_options = '\n'.join(opts)
        label_dropdown_html = f"""
        <form id="label-select-form" class="mb-4" method="get" action="{label_action}">
          <div class="form-group">
            <label>Select customer for Label:</label>
            <select id="label-cust-select" class="form-control">{label_options}</select>
          </div>
          <button class="btn btn-sm btn-warning">Create Label</button>
        </form>
        <script>
          document.getElementById('label-select-form').addEventListener('submit', e => {{
            e.preventDefault();
            const cust = encodeURIComponent(document.getElementById('label-cust-select').value);
            const url = e.target.action.replace('__CUST__', cust);
            window.location.href = url;
          }});
        </script>
        """

    # C) Filesystem-based Customer Table
    indiv_dir = os.path.join(OUTPUTS_DIR, order, 'individual')
    pdf_dir = os.path.join(indiv_dir, 'pdf')
    csv_dir = os.path.join(indiv_dir, 'csv')
    if not os.path.isdir(pdf_dir):
        abort(404)
    try:
        with open(os.path.join(indiv_dir, 'metadata.json'), encoding='utf-8') as mf:
            oos_meta = json.load(mf)
    except FileNotFoundError:
        oos_meta = {}
    rows = []
    for fname in sorted(os.listdir(pdf_dir)):
        if not fname.endswith('.pdf'):
            continue
        cust_key = os.path.splitext(fname)[0]
        real_name = cust_key.rsplit('-', 1)[0].replace('_', ' ')
        total = 0
        csv_fname = next(
            (c for c in os.listdir(csv_dir) if c.startswith(cust_key) and c.endswith('.csv')),
            None
        )
        if csv_fname:
            with open(os.path.join(csv_dir, csv_fname), encoding='utf-8-sig') as cf:
                for row in csv.DictReader(cf):
                    try:
                        total += int(row.get('quantity', 0))
                    except:
                        pass
        oos = oos_meta.get(cust_key, 0)
        rows.append({'cust_key': cust_key, 'real_name': real_name, 'total': total, 'oos': oos})

    return render_template_string(
        CUSTOMER_HTML,
        nav_html=NAV_HTML,
        order=order,
        dropdown_html=dropdown_html,
        qr_dropdown_html=label_dropdown_html,
        customers=rows
    )


@orders_bp.route('/<order>/customer/<cust>/view')
@auth.login_required
def download_customer_pdf(order, cust):
    path = os.path.join(OUTPUTS_DIR, order, 'individual', 'pdf')
    fname = next(
        (f for f in os.listdir(path) if f.startswith(cust) and f.endswith('.pdf')),
        None
    )
    if not fname:
        abort(404)
    return send_from_directory(path, fname, as_attachment=False)


@orders_bp.route('/<order>/archive')
@auth.login_required
def archive_order(order):
    base = os.path.join(OUTPUTS_DIR, order)
    archive_dir = os.path.join(OUTPUTS_DIR, 'archived')
    os.makedirs(archive_dir, exist_ok=True)
    if not os.path.isdir(base):
        abort(404)
    shutil.move(base, os.path.join(archive_dir, order))
    return redirect(url_for('dashboard_bp.dashboard'))


@orders_bp.route('/<order>/unarchive')
@auth.login_required
def unarchive_order(order):
    archived_dir = os.path.join(OUTPUTS_DIR, 'archived')
    src = os.path.join(archived_dir, order)
    dst = os.path.join(OUTPUTS_DIR, order)
    if not os.path.isdir(src):
        abort(404)
    shutil.move(src, dst)
    return redirect(url_for('dashboard_bp.archived_orders'))


@orders_bp.route('/<order>/print-label/<cust>')
@auth.login_required
def print_customer_label(order, cust):
    # fetch shipping info from Excel

    records = get_order_shipping_info(order)
    rec = next((r for r in records if r['Customer Full Name'] == cust), None)
    if not rec:
        flash(f"No shipping record for {cust}", "danger")
        return redirect(url_for('order_routes.view_customers', order=order))
    try:
        token = auth_rtd()
        create_rtd_parcel(token, rec)
        flash(f"Label printed for {cust}", "success")
    except Exception as e:
        logging.exception("RTD parcel creation failed")
        flash(f"Failed to print label: {e}", "danger")
    return redirect(url_for('order_routes.view_customers', order=order))


@orders_bp.route('/<order>/label/<cust>')
@auth.login_required
def render_label(order, cust):
    # Fetch record
    records = get_order_shipping_info(order)
    rec = next((r for r in records if r['Customer Full Name'] == cust), None)
    if not rec:
        flash(f"No data for {cust}", "danger")
        return redirect(url_for('order_routes.view_customers', order=order))

    raw_map = rec.get('Google Maps Link')
    maps_url = ''
    maps_status = False
    # treat only non-empty strings as valid
    if isinstance(raw_map, str) and raw_map.strip():
        maps_url = raw_map.strip()
        maps_status = True
    alias = generate_alias(cust)
    try:
        short_url = shorten_url(maps_url, alias=alias)
    except Exception:
        short_url = maps_url

    # Payload = just the tinyurl
    payload = short_url

    # Generate compact QR (small version)
    qr = qrcode.QRCode(
        version=2,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=2,
        border=1,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    qr_img.save(buf, format='PNG')
    qr_data = base64.b64encode(buf.getvalue()).decode()
    sold = rec.get('Sold Price', 0) or 0
    quantity = int(rec.get('Number of Items', ''))
    whish = rec.get('Amount Paid Whish', 0) or 0
    amount_due = sold - whish
    qr_html = ''
    if maps_status:
        qr_html = f'<div class="qr"><img src="data:image/png;base64,{qr_data}"/></div>'
    # Label HTML: float text left, QR on right, text block width reduced
    label_html = f"""
    <!doctype html>
    <html>
    <head>
      <style>
        @page {{ size:2.95in 1.96in; margin:0; }}
        html, body {{
          margin: 0;
          padding: 8px;
          width: 2.95in;
          height: 1.96in;
          overflow: hidden;
          font-family: sans-serif;
          position: relative;
        }}
        .name {{ font-size: 12px; font-weight: bold; margin-bottom: 2px; }}
        .address, .phone {{ font-size: 10px; margin: 1px 0; }}
        .qr {{
          bottom: 15px;
          right: 4px;
          width: 15mm;
          height: 15mm;
        }}
        .qr img {{ width: 100%; height: auto; }}
      </style>
    </head>
    <body>
      <div class="name">{cust}</div>
      <div class="address">{rec['Written Address']}</div>
      <div class="phone">{rec['Phone Number']}</div><br>
      <div class="quantity">{quantity} items</div>
    {qr_html}
    <div class="amount"><b>{amount_due} $</b></div>
    </body>
    </html>
    """
    return Response(label_html, mimetype='text/html')
