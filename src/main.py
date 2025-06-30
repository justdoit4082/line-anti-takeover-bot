from flask import Flask
from src.routes.webhook import webhook_bp  # ✅ 匯入 webhook blueprint

app = Flask(__name__)
app.register_blueprint(webhook_bp)         # ✅ 註冊 webhook

@app.route("/")                             # ✅ 新增根目錄路由
def home():
    return "LINE Anti-Takeover Bot is running."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)     # ✅ 改為正確 port（你目前是 10000）
