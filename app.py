from flask import Flask
from auth import auth
from dashboard_routes import dashboard_bp
from order_routes import orders_bp
from cart_routes import cart_bp
from sku_routes import sku_bp

app = Flask(__name__)
# Secret key is required for session-based features like flash()
app.secret_key = "replace-with-a-strong-random-secret"

FLASK_PORT = 8989

# Register blueprints (avoid duplicates)
app.register_blueprint(dashboard_bp)
app.register_blueprint(orders_bp, url_prefix="/orders")
app.register_blueprint(cart_bp)
app.register_blueprint(sku_bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=FLASK_PORT, debug=True)
