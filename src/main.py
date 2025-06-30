from flask import Flask
from src.routes.webhook import webhook_bp  # 匯入 blueprint

app = Flask(__name__)
app.register_blueprint(webhook_bp)  # 註冊 webhook 路由

# 新增首頁路由，避免根目錄回傳 404
@app.route("/")
def home():
    return "LINE Anti-Takeover Bot is running."

# 運行主程式
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
