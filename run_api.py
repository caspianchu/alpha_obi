from uvicorn import run
from src.web.api import app

if __name__ == "__main__":
    run(app, host="0.0.0.0", port=8000)
