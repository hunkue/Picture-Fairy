from logger import logger
from setting import (
    LINE_CHANNEL_ACCESS_TOKEN,
    LINE_CHANNEL_SECRET
)
from bot_pf.openai import get_openai_description
from bot_pf.search import search_image_with_google
from bot_pf.validation import validate_image
from flask import request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    ImageMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

# 初始化 LINE Bot 的 Messaging API 客戶端與 Webhook 處理器
configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

def setup_routes(app):
    @app.route("/callback", methods=["POST"])
    def callback():
        # LINE Webhook 入口
        # 取得簽名
        signature = request.headers.get("X-Line-Signature", "")
        if not signature:
            logger.warning("Missing X-Line-Signature.")
            abort(400)
        # 取得請求 body
        body = request.get_data(as_text=True)
        logger.info("Request body:" + body)
        # print(f"Request body: {body}")  # Log 訊息

        # 處理訊息
        try:
            handler.handle(body, signature)
        except InvalidSignatureError:
            logger.error(
                "Invalid signature. Please check your channel access token/channel secret."
            )
            abort(400)
        return "OK"
    
    return app

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    # 處理使用者訊息
    user_input = event.message.text.strip()
    logger.info(f"Received message: {user_input}")  # Log 訊息

    # 使用 Google 搜尋圖片
    image_url = search_image_with_google(user_input)

    if "找不到" in image_url or "圖片搜尋失敗" in image_url:
        reply_messages = [
            TextMessage(text="對不起，我找不到符合的圖片，請稍後再試，或更換搜尋關鍵字")
        ]
    else:
        # 嘗試回傳圖片
        if validate_image(image_url):  # 如果圖片有效
            # 呼叫 Azure OpenAI API 生成描述
            ai_response = get_openai_description(user_input)

            reply_messages = [
                TextMessage(text=ai_response),
                ImageMessage(originalContentUrl=image_url, previewImageUrl=image_url),
            ]
        else:
            # 如果圖片無法上傳，則回傳圖片 URL 給用戶
            reply_messages = [
                TextMessage(
                    text=f"搜尋到相關圖片但無法上傳，僅提供連結查看圖片：{image_url}"
                )
            ]

    with ApiClient(configuration) as api_client:
        # 回覆 LINE 使用者
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(reply_token=event.reply_token, messages=reply_messages)
        )