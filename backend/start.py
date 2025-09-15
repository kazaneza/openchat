#!/usr/bin/env python3
import uvicorn
import os

if __name__ == "__main__":
    os.system("pip install -r ../requirements.txt")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)