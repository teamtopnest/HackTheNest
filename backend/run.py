from pathlib import Path

from dotenv import load_dotenv
import uvicorn

if __name__ == "__main__":
    load_dotenv(Path(__file__).with_name(".env.local"))
    load_dotenv(Path(__file__).with_name(".env"))
    uvicorn.run("eeg_stream.app:app", host="127.0.0.1", port=8000, reload=False)
