from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
import os

app = FastAPI(title="FastAPI Web App", description="Serves static HTML content")

@app.get("/", response_class=HTMLResponse)
def read_root():
    """
    Serve the index.html file from the ./web/ directory.
    Returns:
        HTMLResponse: The content of index.html as an HTML response
    """
    html_file_path = "./web/index.html"
    
    if not os.path.exists(html_file_path):
        raise HTTPException(status_code=404, detail="index.html not found")
    
    try:
        with open(html_file_path, 'r', encoding='utf-8') as file:
            html_content = file.read()
        return html_content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading index.html: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)