import requests
from requests.exceptions import HTTPError, Timeout, RequestException
from logger import logger
from setting import (
    AZURE_OPENAI_KEY,
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_DEPLOYMENT_NAME,
    AZURE_OPENAI_API_VERSION
)

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
            timeout=10,  # 設定 10 秒超時，避免 API 長時間無響應造成的塞車
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