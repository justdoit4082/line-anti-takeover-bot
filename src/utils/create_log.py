# src/utils/create_log.py
import os
from datetime import datetime

LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

def create_event_log(event_type: str, user_id: str, group_id: str, message: str = ""):
    """
    寫入事件 log 檔
    :param event_type: 事件類型（如 warn, ban, join 等）
    :param user_id: 使用者 ID
    :param group_id: 群組 ID
    :param message: 附加訊息
    """
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    filename = f"{LOG_DIR}/{group_id}_{event_type}.log"

    with open(filename, "a", encoding="utf-8") as f:
        f.write(f"[{now}] {event_type.upper()} - {user_id}: {message}\n")
