import requests

data = {
    "file_path": "test.py",
    "content_before": "def test_hello():\n",
    "content_after": ""
}

res = requests.post("http://127.0.0.1:8765/completion", json=data)
print(res.status_code)
print(res.json())
