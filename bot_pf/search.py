import requests
from urllib.parse import unquote, urlparse
from cachetools import TTLCache
from logger import logger
from setting import(
    GOOGLE_API_KEY,
    GOOGLE_SEARCH_API_URL,
    CSE_ID
)
from requests.exceptions import HTTPError, Timeout, RequestException, ConnectionError
from .validation import validate_image

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
        "imgSize" : "MEDIUM",
        "start": 0,
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