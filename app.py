from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from datetime import datetime
from collections import deque
import os
from dotenv import load_dotenv
import unicodedata

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

# 全角数字を半角数字に変換する関数
def convert_to_half_width(text):
    return unicodedata.normalize('NFKC', text)

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text.strip()

    # 全角数字を半角数字に変換
    normalized_message = convert_to_half_width(user_message)

    # 在庫削除
    if normalized_message.isdigit():
        index = int(normalized_message)
        if 0 <= index < len(inventory):
            removed_item = inventory[index]
            inventory.remove(removed_item)
            reply_message = f"在庫「{removed_item['name']}」を削除しました。"
        else:
            reply_message = "指定された番号の在庫が見つかりません。"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_message))
        return  # 削除処理が完了したら終了

    # 在庫一覧を表示
    if normalized_message.lower() == "一覧":
        if inventory:
            inventory_list = [
                f"{index}: {item['name']}（登録日: {item['date']})"
                for index, item in enumerate(inventory)
            ]
            reply_message = "\n".join(inventory_list)
        else:
            reply_message = "在庫はありません。"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_message))
        return  # 一覧表示処理が完了したら終了

    # その他のメッセージは在庫として登録
    JST = datetime.now().strftime("%Y-%m-%d")  # 日付だけを使用
    inventory.append({"name": user_message, "date": JST})
    reply_message = f"「{user_message}」を在庫に追加しました。"
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_message))

if __name__ == "__main__":
    port = int(os.getenv("PORT", 6000))
    app.run(host="0.0.0.0", port=port)
