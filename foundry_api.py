from __future__ import annotations

import os

import uvicorn

from project_exchange.database import DEFAULT_DB_PATH
from project_exchange.foundry_api import create_app

app = create_app(os.getenv("PROVENA_DB_PATH", str(DEFAULT_DB_PATH)))


if __name__ == "__main__":
    uvicorn.run("foundry_api:app", host="0.0.0.0", port=int(os.getenv("FOUNDRY_API_PORT", "8000")), reload=False)
