import unittest
from unittest.mock import patch, MagicMock
import requests
from scratch.test_ash import send_completion_request
import os

class TestSendCompletionRequest(unittest.TestCase):
    """Unit tests for the send_completion_request function."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.base_url = "http://localhost:8000/api/v1/completions"
        self.valid_payload = {
            "prompt": "Hello, world!",
            "max_tokens": 50,
            "temperature": 0.7
        }
        self.valid_headers = {
            "Authorization": "Bearer your-api-key-here",
            "Content-Type": "application/json"
        }
        self.minimal_headers = {"Content-Type": "application/json"}
    
    @patch('requests.post')
    def test_valid_request_success(self, mock_post):
        """Test successful completion request with valid parameters."""
        # Arrange
        expected_response = {"choices": [{"text": "Hello back to you!"}]}]
        mock_response = MagicMock()
        mock_response.json.return_value = expected_response
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # Act
        result = send_completion_request(self.base_url, self.valid_payload, self.valid_headers)
        
        # Assert
        mock_post.assert_called_once_with(
            self.base_url,
            json=self.valid_payload,
            headers=self.valid_headers
        )
        self.assertEqual(result, expected_response)
    
    @patch('requests.post')
    def test_missing_api_key_with_default_headers(self, mock_post):
        """Test that default headers are used when no headers provided and API key is missing."""
        # Arrange
        expected_response = {"choices": [{"text": "Response without auth"}]}
        mock_response = MagicMock()
        mock_response.json.return_value = expected_response
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # Act
        result = send_completion_request(self.base_url, self.valid_payload)
        
        # Assert
        expected_headers = {'Content-Type': 'application/json'}
        mock_post.assert_called_once_with(
            self.base_url,
            json=self.valid_payload,
            headers=expected_headers
        )
        self.assertEqual(result, expected_response)
    
    @patch('requests.post')
    def test_invalid_url_connection_error(self, mock_post):
        """Test handling of connection error with invalid URL."""
        # Arrange
        invalid_url = "http://invalid-url-that-does-not-exist.com/api"
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection failed")
        
        # Act & Assert
        with self.assertRaises(requests.exceptions.ConnectionError) as context:
            send_completion_request(invalid_url, self.valid_payload)
        self.assertIn("Connection failed", str(context.exception))
    
    @patch('requests.post')
    def test_network_timeout_error(self, mock_post):
        """Test handling of timeout error."""
        # Arrange
        mock_post.side_effect = requests.exceptions.Timeout("Request timed out")
        
        # Act & Assert
        with self.assertRaises(requests.exceptions.Timeout) as context:
            send_completion_request(self.base_url, self.valid_payload)
        self.assertIn("Request timed out", str(context.exception))
    
    @patch('requests.post')
    def test_http_4xx_error_response(self, mock_post):
        """Test handling of 4xx HTTP error responses."""
        # Arrange
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("400 Client Error")
        mock_post.return_value = mock_response
        
        # Act & Assert
        with self.assertRaises(requests.exceptions.HTTPError) as context:
            send_completion_request(self.base_url, self.valid_payload)
        self.assertIn("400 Client Error", str(context.exception))
    
    @patch('requests.post')
    def test_http_5xx_error_response(self, mock_post):
        """Test handling of 5xx HTTP error responses."""
        # Arrange
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")
        mock_post.return_value = mock_response
        
        # Act & Assert
        with self.assertRaises(requests.exceptions.HTTPError) as context:
            send_completion_request(self.base_url, self.valid_payload)
    
    @patch('requests.post')
    def test_invalid_json_response(self, mock_post):
        """Test handling of invalid JSON response from server."""
        # Arrange
        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # Act