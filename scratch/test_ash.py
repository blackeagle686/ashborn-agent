import requests

def send_completion_request(url: str, payload: dict, headers: dict = None) -> dict:
    """
    Send a completion request to the ASHBORN API.

    Args:
        url (str): The API endpoint URL.
        payload (dict): The JSON payload to send.
        headers (dict, optional): Additional HTTP headers.

    Returns:
        dict: The JSON response from the server.

    Raises:
        requests.exceptions.RequestException: If the request fails.
        ValueError: If the response is not valid JSON.
    """
    try:
        if headers is None:
            headers = {'Content-Type': 'application/json'}
        
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        raise
    except ValueError as e:
        print(f"Invalid JSON response: {e}")
        raise

if __name__ == "__main__":
    # Test the send_completion_request function
    test_url = "http://localhost:8000/api/v1/completions"
    test_payload = {
        "prompt": "Hello, world!",
        "max_tokens": 50,
        "temperature": 0.7
    }
    test_headers = {
        "Authorization": "Bearer your-api-key-here",
        "Content-Type": "application/json"
    }
    
    try:
        result = send_completion_request(test_url, test_payload, test_headers)
        print("Completion request successful:")
        print(result)
    except Exception as e:
        print(f"Test failed: {e}")