import os
import requests
from dotenv import load_dotenv
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi, ReplyMessageRequest,
    TextMessage, ImageMessage
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

load_dotenv()

app = Flask(__name__)

LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRECT = os.getenv('LINE_CHANNEL_SECRECT')

configuration = Configuration(access_token = LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRECT)

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
CSE_ID = os.getenv('CSE_ID')
GOOGLE_SEARCH_API_URL = os.getenv('GOOGLE_SEARCH_API_URL')

@app.route("/callback", methods=['POST'])
def callback():
    # LINE Webhook 入口
    signature = request.headers['X-Line-Signature'] 
    body = request.get_data(as_text=True)
    app.logger.info('Request body:' + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info('Invalid signature. Please check your channel access token/channel secret.')
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message = TextMessageContent)
def handle_message(event):
    # 處理使用者訊息
    user_input = event.message.text.strip()

    # 使用 Google 搜尋圖片
    image_url = search_image_with_google(user_input)

    if not image_url:
        reply_messages = [TextMessage(text = '對不起，我找不到這個圖片')]
    else:
        # 呼叫 Azure OpenAI API 生成描述
        ai_response = get_openai_description(user_input)
        
        reply_messages = [
            TextMessage(text = ai_response),
            ImageMessage(originalContentUrl = image_url, previewImageUrl = image_url)
        ]

    with ApiClient(configuration) as api_client:
        # 回覆 LINE 使用者
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token = event.reply_token,
                messages = reply_messages
            )
        )

def search_image_with_google(query):
    params = {
        'key': GOOGLE_API_KEY,
        'cx': CSE_ID,
        'q': query, # 搜尋的關鍵字
        'searchType': 'image', # 指定搜尋圖片
        'num': 1 # 回傳1張圖片
    }

    response = requests.get(GOOGLE_SEARCH_API_URL, params = params)
    if response.status_code == 200:
        search_results = response.json()
        if 'items' in search_results and len(search_results['items']) > 0:
            image_url = search_results['items'][0]['link']
            return image_url
    return None

def get_openai_description(query):
    # 向 Azure OpenAI with Search 取得圖片網址與描述
    headers = {
        'Content-Type': 'application/json', 
        'api-key': AZURE_OPENAI_KEY,
    }
    
    payload = {
        'messages':[
            {'role': 'system', 'content': '你是一個圖片搜尋專家，請根據圖片給出一個簡短描述（50 字內）。'},
            {'role': 'user', 'content': f'請根據搜尋到的圖片給我關於 {query} 的簡短描述（50 字內）。'}
        ],
        'temperature': 0.7,
        'max_tokens': 100
    }

    response = requests.post(
        f'{AZURE_OPENAI_ENDPOINT}/openai/deployments/{AZURE_OPENAI_DEPLOYMENT_NAME}/chat/completions?api-version={AZURE_OPENAI_API_VERSION}',
        json = payload,
        headers = headers
    )

    if response.status_code == 200:
        ai_response = response.json()['choices'][0]['message']['content'].strip()
        return ai_response
    return '無法生成描述'

if __name__ == '__main__':
    app.run(port = 5000, debug = True)