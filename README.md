# 防翻群機器人 (LINE Anti-Takeover Bot)

一個專為保護LINE群組免受惡意攻擊的機器人，具備自動檢測異常加入、防止未授權操作、通知管理員和自動處理惡意帳號等功能。

## 🚀 主要功能

1. **自動檢查異常加入** - 監控短時間內大量成員加入，識別潛在翻群行為
2. **操作權限管理** - 防止特定使用者執行踢人、改群名等高風險操作
3. **管理員通知系統** - 即時通知管理員可疑活動和安全威脅
4. **自動處理惡意帳號** - 自動封鎖或踢出被識別為惡意的帳號

## 📋 部署到Render

### 1. 準備LINE Bot

1. 前往 [LINE Developers Console](https://developers.line.biz/)
2. 建立新的Provider（如果沒有的話）
3. 建立新的Messaging API頻道
4. 記錄以下資訊：
   - Channel Access Token
   - Channel Secret

### 2. 部署到Render

1. Fork或下載此專案到您的GitHub帳號
2. 前往 [Render](https://render.com/) 並登入
3. 點擊「New +」→「Web Service」
4. 連接您的GitHub倉庫
5. 選擇此專案
6. 設定以下環境變數：
   - `LINE_CHANNEL_ACCESS_TOKEN`: 您的LINE Bot Channel Access Token
   - `LINE_CHANNEL_SECRET`: 您的LINE Bot Channel Secret
   - `SECRET_KEY`: 隨機生成的密鑰（Render會自動生成）
7. 點擊「Create Web Service」開始部署

### 3. 設定Webhook URL

1. 部署完成後，複製Render提供的服務URL
2. 回到LINE Developers Console
3. 在您的Messaging API頻道設定中：
   - 設定Webhook URL為：`https://your-service-url.onrender.com/webhook`
   - 啟用「Use webhook」
   - 啟用「Allow bot to join group chats」

## 🔧 本地開發

### 環境需求

- Python 3.11+
- pip

### 安裝步驟

1. 複製專案：
```bash
git clone <repository-url>
cd line-anti-takeover-bot
```

2. 建立虛擬環境：
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
```

3. 安裝依賴：
```bash
pip install -r requirements.txt
```

4. 設定環境變數：
```bash
cp .env.example .env
# 編輯 .env 檔案，填入您的LINE Bot資訊
```

5. 啟動應用程式：
```bash
python src/main.py
```

## 📱 使用說明

### 將機器人加入群組

1. 在LINE中搜尋您的機器人（使用Bot的Basic ID或QR Code）
2. 將機器人加入需要保護的群組
3. 機器人會發送歡迎訊息並說明功能

### 設定管理員

群組中的任何人都可以使用以下指令來設定管理員：

```
/addadmin @使用者名稱
```

### 可用指令

- `/help` - 顯示指令說明
- `/status` - 查看群組狀態
- `/threshold <數字>` - 設定異常加入閾值（僅管理員）
- `/addadmin @使用者` - 新增管理員（僅管理員）
- `/removeadmin @使用者` - 移除管理員（僅管理員）
- `/blacklist` - 查看黑名單
- `/block @使用者` - 封鎖使用者（僅管理員）
- `/unblock @使用者` - 解除封鎖（僅管理員）

## 🛡️ 安全機制

### 異常加入檢測

- 監控1分鐘內的成員加入數量
- 可自訂閾值（預設：5人/分鐘）
- 超過閾值時自動通知管理員

### 黑名單系統

- 支援群組特定和全域黑名單
- 黑名單使用者嘗試加入時自動踢出
- 記錄封鎖原因和時間

### 操作日誌

- 記錄所有群組活動
- 標記可疑操作
- 提供完整的審計追蹤

## 📊 管理介面

訪問您的Render服務URL即可查看管理介面，包含：

- 整體統計資訊
- 群組列表和狀態
- 即時活動監控

## ⚠️ 注意事項

1. **API限制**：LINE Bot API目前不支援直接踢人功能，機器人只能通知管理員手動處理
2. **權限**：機器人需要在群組中有適當權限才能正常運作
3. **隱私**：機器人只記錄必要的操作資訊，不會儲存訊息內容
4. **免費方案**：Render免費方案有使用限制，高流量群組建議升級付費方案

## 🔧 技術架構

- **後端**：Flask + SQLite
- **LINE SDK**：line-bot-sdk-python
- **部署**：Render Platform
- **資料庫**：SQLite（可擴展至PostgreSQL）

## 📝 授權

此專案採用MIT授權條款。

## 🤝 貢獻

歡迎提交Issue和Pull Request來改善此專案。

## 📞 支援

如有問題或需要協助，請：

1. 查看此README文件
2. 檢查Issues頁面
3. 聯繫專案維護者

