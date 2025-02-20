import os
import requests
import logging
import mimetypes
from urllib.parse import unquote, urlparse
from cachetools import TTLCache
from dotenv import load_dotenv
from flask import Flask, request, abort
from requests.exceptions import HTTPError, Timeout, RequestException, ConnectionError
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

# 設定 logging 
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()

# 檢查環境變數
required_env_vars = [
    "LINE_CHANNEL_ACCESS_TOKEN",
    "LINE_CHANNEL_SECRET",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_KEY",
    "AZURE_OPENAI_DEPLOYMENT_NAME",
    "AZURE_OPENAI_API_VERSION",
    "GOOGLE_API_KEY",
    "CSE_ID",
    "GOOGLE_SEARCH_API_URL",
]

def check_env_variables():
    for var in required_env_vars:
        if not os.getenv(var):
            logger.error(f"Enviroment variable {var} is not set. Please check your .env file.")
            raise EnvironmentError(f"Enviroment variable {var} is not set. Please check your .env file.")

check_env_variables()

app = Flask(__name__)

# 初始化 LINE Bot 的 Messaging API 客戶端與 Webhook 處理器
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
CSE_ID = os.getenv("CSE_ID")
GOOGLE_SEARCH_API_URL = os.getenv("GOOGLE_SEARCH_API_URL")


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


# 統一檢查圖片可訪問性和大小（狀態碼 200 並且是 HTTPS)
def fetch_image_head_info(image_url: str):
    try:
        response = requests.head(image_url, timeout=5)  # 使用 HEAD 方法快速確認
        if response.status_code == 200 and image_url.startswith("https://"):
            return response
        else:
            logger.warning(
                f"Image URL not accessible or not secure: {image_url} (Status code: {response.status_code})"
            )
            return None
    except RequestException as e:
        logger.error(f"Failed to access image URL: {image_url}, Error: {e}")
        return None


# 檢查是否為受限網域
def is_restricted_domain(image_url: str) -> bool:
    restricted_domains = ["fbsbx.com"]
    if any(domain in image_url for domain in restricted_domains):
        logger.info(f"Skipping restricted image URL: {image_url}")
        return True
    return False


# 驗證圖片是否支持（檢查 MIME 類型）
def validate_mime_type(image_url: str) -> bool:
    mime_type, _ = mimetypes.guess_type(image_url)
    validate_mime_types = ["image/jpeg", "image/png", "image/gif"]
    if mime_type not in validate_mime_types:
        logger.warning(
            f"Invalid MIME type based on file extension: {mime_type} for URL: {image_url}"
        )
        # 進一步嘗試請求圖片的內容
        try:
            response = requests.head(image_url, allow_redirects=True)
            mime_type = response.headers.get("Content-Type")
            if mime_type not in validate_mime_types:
                logger.warning(
                    f"Invalid MIME type from Content-Type: {mime_type} for URL: {image_url}"
                )
            return False
        except Exception as e:
            logger.error(f"Error checking MIME type for URL: {image_url}, Error: {e}")
            return False
    return True


# 檢查圖片大小
def validate_image_size(response) -> bool:
    try:
        content_length = int(response.headers.get("Content-Length", 0))
        return content_length <= 10 * 1024 * 1024
    except Exception as e:
        logger.error(f"Failed to validate image size: {e}")
        return False


# 下載圖片來確定格式（檢查圖片內容格式，過濾 WebP）
def check_image_format_by_content(image_url: str) -> bool:
    try:
        response = requests.get(image_url, stream=True)
        if response.status_code == 200:
            content_type = response.headers.get("Content-Type", "")
            if "image" not in content_type:
                logger.info(f"Not an image: {image_url}")
                return False
            # 進一步檢查圖片格式
            if "webp" in content_type:
                logger.info(f"Skipping WebP image: {image_url}")
                return False
            return True
    except Exception as e:
        logger.error(f"Error fetching image content: {image_url}, Error: {e}")
    return False


# 主驗證流程
def validate_image(image_url: str) -> bool:
    if is_restricted_domain(image_url):
        logger.info(f"Image rejected due to restricted domain: {image_url}")
        return False
    response = fetch_image_head_info(image_url)
    if not response:
        logger.info(f"Image rejected due to inaccessible or insecure URL: {image_url}")
        return False
    if not validate_mime_type(image_url):
        logger.info(f"Image rejected due to invalid MIME type: {image_url}")
        return False
    if not validate_image_size(response):
        logger.info(f"Image rejected due to size too large: {image_url}")
        return False
    if not check_image_format_by_content(image_url):
        logger.info(f"Image rejected due to unsupported format: {image_url}")
        return False
    logger.info(f"Image is valid: {image_url}")
    return True


# 搜尋圖片並過濾不合格的圖片
# 建立一個快取，最多儲存 100 筆資料，並且每筆快取保存 300 秒
image_cache = TTLCache(maxsize=100, ttl=300)
def search_image_with_google(query: str) -> str:
    # 檢查是否有快取的結果
    if query in image_cache:
        logger.info(f"Cache hit for query: {query}")
        return image_cache[query]  # 若快取中有結果，直接返回
    
    params = {
        "key": GOOGLE_API_KEY,
        "cx": CSE_ID,
        "q": query,  # 搜尋的關鍵字
        "searchType": "image",  # 指定搜尋圖片
        "num": 5,  # 回傳 5 張圖片
    }
    first_image_url = None
    valid_image_urls = []
    try:
        response = requests.get(GOOGLE_SEARCH_API_URL, params=params)
        response.raise_for_status()  # 確保狀態碼為 200
        search_results = response.json()
        # Log 回傳結果，查看 JSON 結構
        # print(f"Google search response: {search_results}")
        # 解析搜尋結果
        items = search_results.get("items", [])
        if not items:
            image_cache[query] = "找不到相關圖片"
            return "找不到相關圖片"
        for item in items:
            image_url = item["link"]
            # print(f"Checking image URL: {image_url}")  # 印出每一個檢查的圖片 URL
            if "wikimedia.org" in image_url:
                # 如果圖片來自 Wikimedia，使用 Wikimedia API 來獲取詳細訊息
                wikimedia_url = get_wikimedia_image_url(image_url)
                if wikimedia_url:
                    image_url = wikimedia_url

            if not first_image_url:
                    first_image_url = image_url
            
            try:
                if validate_image(image_url):  # 確認圖片通過所有驗證
                    valid_image_urls.append(image_url)
                else:
                    logger.info(f"Skipping restricted image URL: {image_url}")
            except Exception as e:
                    logger.error(f"Error validating image URL {image_url}: {e}")

        if valid_image_urls:
            selected_image = valid_image_urls[0]
            logger.info(f"Valid image found: {selected_image}")
            # 將結果存入快取
            image_cache[query] = selected_image
            return selected_image
        else:
            logger.info("No valid images found after filtering.")
            image_cache[query] = first_image_url or "找不到來源有效安全或可訪問的圖片"
            return first_image_url or "找不到來源有效安全或可訪問的圖片"

    except HTTPError as http_err:
        logger.error(f"HTTP error occurred: {http_err}")
        return "圖片搜尋失敗，請稍後再試"
    except Timeout as timeout_err:
        logger.error(f"Timeout error occured: {timeout_err}")
        return "請求超時，請稍後再試"
    except ConnectionError as conn_err:
        logger.error(f"Connection error occurred: {conn_err}")
        return "網路連線失敗，請檢查您的網路連線"
    except RequestException as req_err:
        logger.error(f"Request error occurred: {req_err}")
        return "請求錯誤，請稍候再試"
    except KeyError as e:
        logger.error(f"Unexpected response format: {e}")
        return "圖片解析失敗"


def get_wikimedia_image_url(image_url: str) -> str:
    """
    從 Wikimedia 取得指定標題的圖片 URL。
    :param title: Wikimedia 圖片的標題（例如 "File:Chineseboxturtle_2006.jpg"）
    :return: 圖片的完整 URL
    """
    filename = unquote(urlparse(image_url).path.split("/")[-1])

    # 從 Wikimedia API 的圖片查詢 URL
    api_url = f"https://commons.wikimedia.org/w/api.php?action=query&titles=File:{filename}&prop=imageinfo&iiprop=URL&format=json"

    try:
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()

        pages = data.get("query", {}).get("pages", {})
        for page_id, page_data in pages.items():
            logger.info(f"Processing page_id: {page_id}")  # 日誌紀錄 page_id

            if "imageinfo" in page_data:
                image_info = page_data["imageinfo"][0]
                image_url = image_info.get("url")
                if image_url:
                    return image_url
                else:
                    logger.warning(f"Image URL not found for file:{filename}")
                    return None

        logger.warning(f"No image info found for file: {filename}")
        return None  # 無法獲取圖片資訊，返回 None
    except RequestException as e:
        logger.error(f"Error fetching wikimedia image info: {e}")
        return image_url


def get_openai_description(query):
    # 向 Azure OpenAI with Search 取得圖片網址與描述
    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_OPENAI_KEY,
    }

    payload = generate_openai_payload(query)

    try:
        response = requests.post(
            f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{AZURE_OPENAI_DEPLOYMENT_NAME}/chat/completions?api-version={AZURE_OPENAI_API_VERSION}",
            json=payload,
            headers=headers,
            timeout=10  # 設定 10 秒超時，避免 API 長時間無響應造成的塞車
        )

        response.raise_for_status()  # 檢查狀態碼
        ai_response = response.json()["choices"][0]["message"]["content"].strip()
        return ai_response

    except Timeout as e:
        logger.error(f"Timeout occured while calling OpenAI API: {e}")
        return "請求超時，請稍候再試"
    except HTTPError as e:
        logger.error(f"HTTP error occurred: {e}")
        return "API 服務出現錯誤，請稍候再試"
    except RequestException as e:
        logger.error(f"Request error occurred: {e}")
        return "請求錯誤，請稍候再試"


def generate_openai_payload(query):

    return {
        "messages": [
            {
                "role": "system",
                "content": "你是一個圖片搜尋專家，請根據圖片給出一個簡短描述（50 字內）。",
            },
            {
                "role": "user",
                "content": f"請根據搜尋到的圖片給我關於 {query} 的簡短描述（50 字內）。",
            },
        ],
        "temperature": 0.7,
        "max_tokens": 100,
    }


if __name__ == "__main__":
    app.run(port=5000, debug=True)
