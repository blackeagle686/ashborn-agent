from fastapi.testclient import TestClient
from ashborn.server import app

client = TestClient(app)
response = client.post("/config", json={"settings": {"OPENAI_API_KEY": "sk-test"}})
print("Status:", response.status_code)
print("Response:", response.text)
