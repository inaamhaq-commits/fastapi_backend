import os

import uvicorn


def main() -> None:
    host = os.getenv("APP_HOST", "127.0.0.1")
    port = int(os.getenv("APP_PORT", "8000"))
    uvicorn.run("linkedin.main:app", host=host, port=port, reload=False)
