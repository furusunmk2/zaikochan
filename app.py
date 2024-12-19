from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from datetime import datetime
from collections import deque
import os
from dotenv import load_dotenv

# .envファイルの読み込み
load_dotenv()

# LINE設定
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
app = Flask(__name__)

if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_CHANNEL_SECRET:
    raise ValueError("LINE_CHANNEL_ACCESS_TOKEN または LINE_CHANNEL_SECRET が設定されていません")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 在庫データの管理（スタック型かつ辞書型）
inventory = deque()

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)

    if not signature:
        abort(400, "X-Line-Signature ヘッダーが欠けています")

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400, "無効な署名です")

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text.strip()

    # 在庫を追加
    if user_message.lower() not in ["一覧", "削除"]:
        JST = datetime.now().strftime("%Y-%m-%d")  # 日付だけを使用
        inventory.append({"name": user_message, "date": JST})
        reply_message = f"「{user_message}」を在庫に追加しました。"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_message))

    # 在庫一覧を表示
    elif user_message.lower() == "一覧":
        if inventory:
            inventory_list = [
                f"{index}: {item['name']}（登録日: {item['date']}"
                for index, item in enumerate(inventory)
            ]
            reply_message = "\n".join(inventory_list)
        else:
            reply_message = "在庫はありません。"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_message))

    # 在庫を削除
    elif user_message.isdigit():
        index = int(user_message)
        if 0 <= index < len(inventory):
            removed_item = inventory[index]
            inventory.remove(removed_item)
            reply_message = f"在庫「{removed_item['name']}」を削除しました。"
        else:
            reply_message = "指定された番号の在庫が見つかりません。"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_message))

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
