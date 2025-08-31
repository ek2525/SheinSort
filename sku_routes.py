# sku_routes.py
import os, csv, json
from flask import Blueprint, render_template_string, redirect, url_for, abort
from auth import auth
from config import OUTPUTS_DIR
from templates import NAV_HTML, SKU_LOOKUP_HTML

sku_bp = Blueprint('sku_bp', __name__, url_prefix='/sku')

@sku_bp.route('/<order>')
@auth.login_required
def sku_order(order):
    # look under <project_root>/outputs/<order>/merged/csv
    csv_dir = os.path.join(OUTPUTS_DIR, order, 'merged', 'csv')
    if not os.path.isdir(csv_dir):
        abort(404)

    # find any CSV file
    csv_files = [f for f in os.listdir(csv_dir) if f.lower().endswith('.csv')]
    if not csv_files:
        abort(404)

    mapping = {}
    csv_path = os.path.join(csv_dir, csv_files[0])
    with open(csv_path, encoding='utf-8-sig') as cf:
        sample = cf.read(2048)
        cf.seek(0)
        # sniff delimiter
        try:
            delim = csv.Sniffer().sniff(sample, delimiters=[',',';','\t']).delimiter
        except csv.Error:
            delim = ','
        reader = csv.DictReader(cf, delimiter=delim)

        for row in reader:
            sku  = row.get('sku','').strip()
            cust = row.get('customer','').strip()
            qty  = row.get('quantity','0').strip()
            if not sku or not cust:
                continue
            try:
                q = int(qty)
            except ValueError:
                q = 0
            mapping.setdefault(sku, []).append({
                'customer': cust,
                'quantity': q
            })

    return render_template_string(
        SKU_LOOKUP_HTML,
        nav_html=NAV_HTML,
        mapping=mapping  # pass the dict itself
    )

@sku_bp.route('/')
@auth.login_required
def sku_redirect():
    # redirect bare /sku to dashboard
    return redirect(url_for('dashboard_bp.dashboard'))
