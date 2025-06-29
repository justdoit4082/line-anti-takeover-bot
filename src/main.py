from flask import Flask
from src.routes.webhook import webhook_bp

app = Flask(__name__)
app.register_blueprint(webhook_bp, url_prefix="/webhook")

@app.route("/")
def home():
    return "防翻群機器人已啟動"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
