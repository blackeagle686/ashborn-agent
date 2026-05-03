import requests

def send_completion_request(file_path, content_before, content_after):
    """
    Sends a completion request to the ASHBORN server.
    
    Args:
        file_path (str): Path to the target file.
        content_before (str): Code before cursor position.
        content_after (str): Code after cursor position.
    
    Returns:
        dict: Server response or error message.
    """
    data = {
        "file_path": file_path,
        "content_before": content_before,
        "content_after": content_after
    }
    try:
        res = requests.post("http://127.0.0.1:8765/completion", json=data, timeout=10)
        res.raise_for_status()
        return res.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

if __name__ == "__main__":
    result = send_completion_request(
        file_path="test.py",
        content_before="def test_hello():",
        content_after=""
    )
    print(result)
