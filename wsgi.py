from app import app

if __name__ != "__main__":
    # 確保 Gunicorn 可以正確載入 app
    app = app