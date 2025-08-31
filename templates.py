# templates.py

NAV_HTML = '''
<nav class="navbar navbar-expand-lg navbar-light bg-light">
  <a class="navbar-brand" href="/">Order Dashboard</a>
  <div class="collapse navbar-collapse">
    <ul class="navbar-nav mr-auto">
      <li class="nav-item"><a class="nav-link" href="/cart">Cart Generation</a></li>
      <li class="nav-item"><a class="nav-link" href="/archived">Archived Orders</a></li>
    </ul>
  </div>
</nav>
'''

DASHBOARD_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Order Dashboard</title>
  <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
</head><body>
  {{ nav_html|safe }}
  <div class="container mt-4">
    <h1>Orders</h1>
    <table class="table table-striped">
      <thead><tr><th>Order</th><th>Status</th><th>Actions</th></tr></thead>
      <tbody>{{ table_rows|safe }}</tbody>
    </table>
  </div>
</body>
</html>
"""

CART_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Shein Cart Processor</title>
  <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
</head><body>
  {{ nav_html|safe }}
  <div class="container mt-5">
    <h1>Shein Cart Processor</h1>
    <form method="post" action="/process" enctype="multipart/form-data">
      <div class="form-group">
        <label>Order Number</label>
        <input type="text" name="order_number" class="form-control" required>
      </div>
      <div class="form-group">
        <label>Select HTML files</label>
        <input type="file" id="files" name="files" multiple accept=".html,.htm" class="form-control-file">
      </div>
      <div id="customers"></div>
      <button type="submit" class="btn btn-primary">Process Cart</button>
    </form>
  </div>
  <script>
    const fileInput = document.getElementById('files');
    const customersDiv = document.getElementById('customers');
    fileInput.addEventListener('change', () => {
      customersDiv.innerHTML = '';
      Array.from(fileInput.files).forEach(file => {
        const div = document.createElement('div');
        div.classList.add('form-group');
        div.innerHTML = `
          <label>Customer Name for ${file.name}</label>
          <input type="text" name="customer_names" class="form-control" placeholder="Customer Name" required>
          <label>Out-of-Stock Count for ${file.name}</label>
          <input type="number" name="oos_counts" class="form-control" placeholder="Out-of-Stock Count" min="0" value="0" required>
        `;
        customersDiv.appendChild(div);
      });
    });
  </script>
</body>
</html>
"""

SKU_LOOKUP_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>SKU Lookup</title>
  <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
</head>
<body>
  {{ nav_html|safe }}
  <div class="container mt-5">
    <h1>SKU Lookup</h1>

    <div class="row">
      <!-- Left column: lookup input, result, history -->
      <div class="col-md-8">
        <div class="form-group">
          <input id="sku-input" class="form-control mb-2" placeholder="Enter SKU or suffix and press Enter">
        </div>
        <div id="result" style="font-size:30px;" class="mb-3 font-weight-bold"></div>
        <ul id="history" class="list-group mb-4"></ul>
      </div>

      <!-- Right column: scan progress -->
      <div class="col-md-4">
        <h3>Scan Progress</h3>
        <table class="table table-bordered">
          <thead>
            <tr><th>Customer</th>
            <th>Total</th>
            <th>Out of Stock</th>
            <th>Scanned</th>
            </tr>
          </thead>
          <tbody id="scan-table-body">
            <!-- JS populates this -->
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <script>
  document.addEventListener('DOMContentLoaded', function() {
    const rawMapping = {{ mapping|tojson }};
    console.log("🔍 rawMapping:", rawMapping);

    // lowercase keys for insensitive matching
    const mapping = {};
    Object.entries(rawMapping).forEach(([sku, items]) => {
      mapping[sku.toLowerCase()] = items;
    });

    // build totals
    const customerTotals = {};
    Object.values(mapping).forEach(items =>
      items.forEach(it =>
        customerTotals[it.customer] = (customerTotals[it.customer]||0) + it.quantity
      )
    );

    // init scan table
    const scannedCounts = {}, scannedSets = {};
    const tbody = document.getElementById('scan-table-body');
    Object.keys(customerTotals).forEach(cust => {
      scannedCounts[cust] = 0;
      scannedSets[cust]   = new Set();
      const slug = cust.replace(/\\W+/g,'_');
      const row = document.createElement('tr');
      row.innerHTML = `
        <td>${cust}</td>
        <td>${customerTotals[cust]}</td>
        <td id="scanned-${slug}">0</td>
      `;
      tbody.appendChild(row);
    });

    // wire up lookup
    const input     = document.getElementById('sku-input');
    const resultDiv = document.getElementById('result');
    const historyEl = document.getElementById('history');
    input.focus();

    input.addEventListener('keyup', function(e) {
      if (e.key !== 'Enter') return;
      e.preventDefault();
      const rawValue = input.value.trim().toLowerCase();
      input.value = '';
      if (!rawValue) return;

      // exact + suffix matches
      let entries = (mapping[rawValue]||[]).map(it => ({...it, sku: rawValue}));
      if (entries.length === 0) {
        Object.entries(mapping).forEach(([sku, items]) => {
          if (sku.endsWith(rawValue))
            items.forEach(it => entries.push({...it, sku}));
        });
      }

      // display logic
      let display;
      if (!entries.length) {
        display = `❌ ${rawValue} → not found`;
      } else if (entries.length === 1) {
        const x=entries[0];
        display = `✅ ${x.sku} → ${x.customer} (qty: ${x.quantity})`;
      } else {
        display = '✅ multiple found: ' +
          entries.map(x=>`${x.sku}: ${x.customer} (qty: ${x.quantity})`).join('; ');
      }
      resultDiv.textContent = display;

      // history
      const li = document.createElement('li');
      li.textContent = display;
      li.classList.add('list-group-item');
      historyEl.prepend(li);

      // update scan counts
      entries.forEach(x => {
        const cust = x.customer, sku = x.sku, qty = x.quantity;
        if (!scannedSets[cust].has(sku)) {
          scannedSets[cust].add(sku);
          scannedCounts[cust] += qty;
          const slug = cust.replace(/\\W+/g,'_');
          document.getElementById(`scanned-${slug}`).textContent = scannedCounts[cust];
        }
      });
    });
  });
  </script>
</body>
</html>
"""

CUSTOMER_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Customers of {{ order }}</title>
  <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
</head>
<body>
  {{ nav_html|safe }}
  <div class="container mt-5">
    <h1>Customers in Order {{ order }}</h1>

    {# Flash messages #}
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        {% for category, msg in messages %}
          <div class="alert alert-{{ 'success' if category=='success' else 'danger' }} alert-dismissible fade show mt-3" role="alert">
            {{ msg }}
            <button type="button" class="close" data-dismiss="alert" aria-label="Close">
              <span aria-hidden="true">&times;</span>
            </button>
          </div>
        {% endfor %}
      {% endif %}
    {% endwith %}

    {# Shipping Label Dropdown #}
    {{ dropdown_html|safe }}

    {# QR Code Dropdown #}
    {{ qr_dropdown_html|safe }}

    <table class="table table-bordered mt-3">
      <thead>
        <tr>
          <th>Customer</th>
          <th>Total Items</th>
          <th>Out of Stock</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {% for c in customers %}
        <tr>
          <td>{{ c.real_name }}</td>
          <td>{{ c.total }}</td>
          <td>{{ c.oos }}</td>
          <td>
            <a href="{{ url_for('order_routes.download_customer_pdf', order=order, cust=c.cust_key) }}"
               class="btn btn-sm btn-primary">View PDF</a>
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

  <script src="https://code.jquery.com/jquery-3.5.1.slim.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@4.5.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

EDIT_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Edit Order</title>
  <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
</head><body>
  {{ nav_html|safe }}
  <div class="container mt-5">
    <h1>Edit Order {{ order }}</h1>
    <form method="post">
      <div class="form-group">
        <label>New Order Number</label>
        <input type="text" name="new_order" class="form-control" value="{{ order }}" required>
      </div>
      <button type="submit" class="btn btn-primary">Save</button>
      <a href="{{ url_for('dashboard_bp.dashboard') }}" class="btn btn-secondary">Cancel</a>
    </form>
  </div>
</body>
</html>
"""

ARCHIVED_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Archived Orders</title>
  <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
</head>
<body>
  {{ nav_html|safe }}
  <div class="container mt-5">
    <h1>Archived Orders</h1>
    <table class="table table-striped">
      <thead>
        <tr>
          <th>Order</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {% for o in orders %}
        <tr>
          <td>{{ o }}</td>
          <td>
            <a href="{{ url_for('order_routes.unarchive_order', order=o) }}" class="btn btn-sm btn-success">Restore</a>
            <a href="{{ url_for('order_routes.delete_order',      order=o) }}" class="btn btn-sm btn-danger"
               onclick="return confirm('Delete {{ o }} forever?');">Delete</a>
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</body>
</html>
"""
