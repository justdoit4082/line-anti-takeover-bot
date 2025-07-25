import os
from flask import Flask
from src.webhook import webhook_bp

app = Flask(__name__)
app.register_blueprint(webhook_bp)

@app.route("/")
def home():
    return "LINE Anti-Takeover Bot is running."

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))  # Render 可接受你指定 10000
    app.run(host="0.0.0.0", port=port)
