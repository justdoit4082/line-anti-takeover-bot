from flask import Flask
from src.webhook import webhook_bp

app = Flask(__name__)
app.url_map.strict_slashes = False  # <<<<< 加這一行！

app.register_blueprint(webhook_bp, url_prefix="/callback")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
