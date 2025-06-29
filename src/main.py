import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from flask_cors import CORS
from src.models.group import db
from src.routes.webhook import webhook_bp
from src.routes.admin import admin_bp

from flask import Flask, send_from_directory
from flask_cors import CORS
from src.routes.webhook import webhook_bp  # ✅

app = Flask(__name__)
CORS(app)

# ✅ 註冊 webhook 路由
app.register_blueprint(webhook_bp, url_prefix='/')


app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'line-anti-takeover-bot-secret-key')

# 啟用CORS
CORS(app)

# 註冊藍圖
app.register_blueprint(webhook_bp, url_prefix='/')
app.register_blueprint(admin_bp, url_prefix='/api')

# 資料庫設定
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
with app.app_context():
    db.create_all()

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
            return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
