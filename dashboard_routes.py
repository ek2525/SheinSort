# dashboard_routes.py
from flask import Blueprint, render_template_string, url_for, redirect
from auth import auth
from config import OUTPUTS_DIR
from templates import NAV_HTML, DASHBOARD_HTML, ARCHIVED_HTML
from utils import load_status
import os

dashboard_bp = Blueprint('dashboard_bp', __name__)


@dashboard_bp.route('/')
@auth.login_required
def dashboard():
    base = OUTPUTS_DIR
    rows = ''
    if os.path.isdir(base):
        for o in sorted(os.listdir(base)):
            # skip the archived folder itself
            if o == 'archived':
                continue

            odir = os.path.join(base, o)
            if not os.path.isdir(odir):
                continue

            st = load_status(odir)
            badge_class = 'badge-danger' if st=='pending' else 'badge-success'
            badge = f'<span class="badge {badge_class}">{st}</span>'
            toggle = 'checked' if st=='pending' else 'pending'

            rows += (
                '<tr>'
                  f'<td>{o}</td>'
                  f'<td>{badge}</td>'
                  '<td>'
                    f'<a href="{url_for("sku_bp.sku_order", order=o)}" class="btn btn-sm btn-primary">Farez</a> '
                    f'<a href="{url_for("order_routes.change_status", order=o, new_status=toggle)}" class="btn btn-sm btn-info">Mark {toggle.title()}</a> '
                    f'<a href="{url_for("order_routes.download_merged_pdf", order=o)}" class="btn btn-sm btn-success">Download PDF</a> '
                    f'<a href="{url_for("order_routes.view_customers", order=o)}" class="btn btn-sm btn-warning">Customers</a> '
                    f'<a href="{url_for("order_routes.edit_order", order=o)}" class="btn btn-sm btn-secondary">Edit</a> '
                    f'<a href="{url_for("order_routes.archive_order", order=o)}" class="btn btn-sm btn-dark">Archive</a> '
                    f'<a href="{url_for("order_routes.delete_order", order=o)}" class="btn btn-sm btn-danger" onclick="return confirm(\'Delete {o}?\');">Delete</a>'
                  '</td>'
                '</tr>'
            )

    return render_template_string(DASHBOARD_HTML, nav_html=NAV_HTML, table_rows=rows)

@dashboard_bp.route('/archived')
@auth.login_required
def archived_orders():
    archived_root = os.path.join(OUTPUTS_DIR, 'archived')
    if not os.path.isdir(archived_root):
        orders = []
    else:
        # only subdirectories under `archived/`
        orders = [
            name for name in sorted(os.listdir(archived_root))
            if os.path.isdir(os.path.join(archived_root, name))
        ]

    return render_template_string(
        ARCHIVED_HTML,
        nav_html=NAV_HTML,
        orders=orders
    )