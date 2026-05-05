"""
Ashborn Landing Page — FastAPI backend.
Serves the static site and provides a download endpoint.
"""

import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

STATIC_DIR = Path(__file__).parent / "static"
DIST_DIR = Path(__file__).parent.parent / "dist"

app = FastAPI(title="Ashborn Landing Page", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
async def landing():
    """Serve the landing page."""
    index = STATIC_DIR / "index.html"
    return HTMLResponse(index.read_text(encoding="utf-8"))


@app.get("/download")
async def download():
    """Serve the latest Ashborn IDE bundle."""
    bundle = DIST_DIR / "ashborn-ide-linux.tar.gz"
    if bundle.exists():
        return FileResponse(
            str(bundle),
            media_type="application/gzip",
            filename="ashborn-ide-linux.tar.gz",
        )
    return {"status": "error", "message": "Build not available yet. Check back soon!"}


@app.get("/api/stats")
async def stats():
    """Return basic project stats for the landing page."""
    return {
        "version": "0.1.0",
        "tools": 10,
        "brain_modules": 4,
        "api_endpoints": 12,
    }


# Mount static assets AFTER routes so they don't shadow /download etc.
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=3000, reload=True)
