from flask import Flask
from src.routes.webhook import webhook_bp

app = Flask(__name__)
app.register_blueprint(webhook_bp, url_prefix="/callback")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
