# Picture-Fairy 🧚‍♀️

![Python version](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Repo size](https://img.shields.io/github/repo-size/hunkue/Picture-Fairy)
![Last commit](https://img.shields.io/github/last-commit/hunkue/Picture-Fairy)
![Issues](https://img.shields.io/github/issues/hunkue/Picture-Fairy)

Picture-Fairy is an AI-powered LINE Bot that allows users to search for images simply by sending text. The bot will:

1. Use the OpenAI API to generate a semantic explanation for the keyword  
2. Use the Google Search API to retrieve the most relevant image and return it via LINE

Perfect for learning new concepts, generating visual inspiration, or just chatting for fun.

---

## ✨ Features

- 🧠 **Semantic Explanation**: Integrates with OpenAI API to explain user-provided keywords
- 🔍 **Image Search**: Uses Google Search API to fetch the most relevant image
- 🤖 **LINE Bot Integration**: Fully compatible with LINE webhook messaging
- 🔒 **Signature Verification**: Ensures all requests are authenticated via LINE signature checks
- 🧩 **Modular Design**: Easy to maintain and extend with new features or providers

---

## 🛠️ Installation & Setup

### 1. Initialize Project

```bash
uv init        # Run once if pyproject.toml does not exist
uv venv
source .venv/bin/activate
uv sync        # Install all dependencies
```

### 2. Set Environment Variables

Create a `.env` file and add the following:

```env
LINE_CHANNEL_SECRET=your_line_secret
LINE_CHANNEL_ACCESS_TOKEN=your_line_token
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxx
GOOGLE_SEARCH_API_KEY=your_google_api_key
GOOGLE_CSE_ID=your_custom_search_engine_id
```

Alternatively, edit `setting.py` to manage configs directly.

---

## 🚀 How to Run

### Local Development (FastAPI)

```bash
uv run python app.py
```

This will start a local server on `localhost:5050` (or specified port). Use [ngrok](https://ngrok.com/) for webhook testing.

### Production Deployment (Gunicorn)

```bash
uv run gunicorn app:app --config gunicorn_config.py
```

Or use WSGI:

```bash
uv run gunicorn wsgi:app
```

---

## 💬 User Flow

1. A user sends a message via LINE (e.g., "green parrot")
2. The bot responds with:
   - A semantic explanation from OpenAI
   - A related image fetched using Google Search API

---

## 📁 Project Structure

```text
.
├── app.py                 # FastAPI entry point
├── wsgi.py                # WSGI entry point
├── handler.py             # Handles routing and message logic
├── setting.py             # Manages environment and configs
├── gunicorn_config.py     # Gunicorn configuration
├── logger.py              # Logging setup
├── bot_pf/                # Core logic modules
│   ├── __init__.py
│   ├── openai.py          # OpenAI API integration
│   ├── search.py          # Google Search API integration
│   └── validation.py      # LINE signature verification
├── pyproject.toml         # uv dependency manager config
├── uv.lock                # uv lock file
├── LICENSE
└── README.md              # This documentation file
```

---

## 🧪 Testing Tips

- Use [ngrok](https://ngrok.com/) to expose your local webhook URL to LINE
- After sending a message, check logs to verify Google/OpenAI requests
- If errors occur, double-check that your API keys are set correctly

---

## 📄 License

This project is licensed under the **MIT License**, feel free to use and modify it.

---

## 🙋‍♂️ Author

- **[hunkue](https://github.com/hunkue)**  
  If you find this project helpful, give it a ⭐ or share it with other AI/chatbot enthusiasts 🙌