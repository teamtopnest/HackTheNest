import sys
from pathlib import Path

import uvicorn

# `eeg_stream` is a package inside this directory, whether the command is
# `python backend/run.py` from the repo or `python run.py` from here.
sys.path.insert(0, str(Path(__file__).resolve().parent))

if __name__ == "__main__":
    uvicorn.run("eeg_stream.app:app", host="127.0.0.1", port=8000, reload=False)
