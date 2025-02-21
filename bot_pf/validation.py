import requests
import mimetypes
from logger import logger
from requests import RequestException


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