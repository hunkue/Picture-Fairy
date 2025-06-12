from flask import Flask
from handler import setup_routes

app = Flask(__name__)
app = setup_routes(app)

if __name__ == "__main__":
    app.run(port=5050, debug=True)