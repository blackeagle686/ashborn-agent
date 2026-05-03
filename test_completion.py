import requests

data = {
    "file_path": "test.py",
    "content_before": "def test_hello():\n",
    "content_after": ""
}

try:
    res = requests.post("http://127.0.0.1:8765/completion", json=data)
    print("Status:", res.status_code)
    print("Body:", res.json())
except Exception as e:
    print("Error:", e)
