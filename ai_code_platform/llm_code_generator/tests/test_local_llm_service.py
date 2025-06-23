import pytest
import os
import json
from unittest.mock import patch, MagicMock
import requests # For requests.exceptions
from ..local_llm_service import LocalLLMService, LLMConfigurationError, LLMAPIError

@pytest.fixture
def mock_requests_post():
    with patch('requests.post') as mock_post:
        yield mock_post

@pytest.fixture(autouse=True)
def clear_local_llm_env_vars():
    env_vars_to_clear = ["LOCAL_LLM_API_BASE", "LOCAL_LLM_MODEL"]
    original_values = {}
    for var in env_vars_to_clear:
        original_values[var] = os.environ.pop(var, None)
    yield
    for var, val in original_values.items():
        if val is not None:
            os.environ[var] = val

def test_local_llm_service_init_defaults():
    """Test LocalLLMService initialization with default values."""
    service = LocalLLMService()
    assert service.api_base_url == LocalLLMService.DEFAULT_API_BASE
    assert service.model == LocalLLMService.DEFAULT_MODEL
    assert service.chat_completions_url == f"{LocalLLMService.DEFAULT_API_BASE}/chat/completions"

def test_local_llm_service_init_with_args():
    """Test LocalLLMService initialization with arguments."""
    custom_url = "http://customhost:8080/api/v1"
    custom_model = "custom-model"
    service = LocalLLMService(api_base_url=custom_url, model=custom_model)
    assert service.api_base_url == custom_url # It will not append /v1 if /api/v1 is already there
    assert service.model == custom_model
    assert service.chat_completions_url == f"{custom_url.rstrip('/')}/chat/completions"

def test_local_llm_service_init_with_env_vars():
    """Test LocalLLMService initialization with environment variables."""
    env_url = "http://envhost:11434"
    env_model = "env-model"
    with patch.dict(os.environ, {"LOCAL_LLM_API_BASE": env_url, "LOCAL_LLM_MODEL": env_model}):
        service = LocalLLMService()
        # The service appends /v1 if it's not present and "localhost" or "envhost" (common pattern) is in url
        assert service.api_base_url == f"{env_url}/v1"
        assert service.model == env_model
        assert service.chat_completions_url == f"{env_url}/v1/chat/completions"

def test_local_llm_service_init_url_cleaning():
    """Test URL cleaning logic, especially adding /v1."""
    service1 = LocalLLMService(api_base_url="http://localhost:1234")
    assert service1.api_base_url == "http://localhost:1234/v1"
    assert service1.chat_completions_url == "http://localhost:1234/v1/chat/completions"

    service2 = LocalLLMService(api_base_url="http://localhost:1234/")
    assert service2.api_base_url == "http://localhost:1234/v1" # Handles trailing slash before adding /v1

    service3 = LocalLLMService(api_base_url="http://someotherhost:5000/custom_path") # Does not add /v1
    assert service3.api_base_url == "http://someotherhost:5000/custom_path"
    assert service3.chat_completions_url == "http://someotherhost:5000/custom_path/chat/completions"

    service4 = LocalLLMService(api_base_url="http://localhost:11434/v1") # Already has /v1
    assert service4.api_base_url == "http://localhost:11434/v1"
    assert service4.chat_completions_url == "http://localhost:11434/v1/chat/completions"


def test_local_llm_service_generate_code_success(mock_requests_post):
    """Test successful code generation with LocalLLMService."""
    service = LocalLLMService()
    prompt = "create a factorial function"
    language = "python"
    expected_code = "def factorial(n):\\n  return 1 if n == 0 else n * factorial(n-1)"

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": expected_code}}]
    }
    mock_response.raise_for_status = MagicMock() # Does nothing, simulating success
    mock_requests_post.return_value = mock_response

    generated_code = service.generate_code(prompt, language)
    assert generated_code == expected_code

    expected_payload = {
        "model": service.model,
        "messages": [
            {"role": "system", "content": f"You are a helpful coding assistant. Generate only the {language} code for the following prompt. Do not include any explanatory text or markdown formatting around the code. Just output the raw code block."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 2048,
    }
    mock_requests_post.assert_called_once_with(
        service.chat_completions_url,
        headers={"Content-Type": "application/json"},
        data=json.dumps(expected_payload),
        timeout=120
    )

def test_local_llm_service_generate_code_with_markdown_stripping(mock_requests_post):
    """Test code generation with markdown stripping for local LLM."""
    service = LocalLLMService()
    prompt = "create a factorial function"
    language = "python"
    raw_code_from_llm = f"```{language}\\ndef factorial(n):\\n  # ...\\n  pass\\n```"
    expected_stripped_code = "def factorial(n):\\n  # ...\\n  pass"

    mock_response = MagicMock()
    mock_response.json.return_value = {"choices": [{"message": {"content": raw_code_from_llm}}]}
    mock_response.raise_for_status = MagicMock()
    mock_requests_post.return_value = mock_response

    generated_code = service.generate_code(prompt, language)
    assert generated_code == expected_stripped_code


@pytest.mark.parametrize("requests_exception, expected_llm_error, error_message_detail", [
    (requests.exceptions.ConnectionError("Connection failed"), LLMAPIError, "Local LLM API connection error"),
    (requests.exceptions.Timeout("Request timed out"), LLMAPIError, "Local LLM API request timed out"),
    (requests.exceptions.HTTPError("404 Client Error", response=MagicMock(status_code=404, text="Not Found", json=lambda: {"error": "not found"})), LLMAPIError, "Local LLM API HTTP error (status 404)"),
    (requests.exceptions.HTTPError("500 Server Error", response=MagicMock(status_code=500, text="Server Error", json=lambda: {"error": "server issue"})), LLMAPIError, "Local LLM API HTTP error (status 500)")
    # json.JSONDecodeError is tested separately in test_local_llm_service_json_decode_error
])
def test_local_llm_service_generate_code_request_errors(mock_requests_post, requests_exception, expected_llm_error, error_message_detail):
    """Test various requests library errors during code generation (excluding JSONDecodeError here)."""
    service = LocalLLMService()
    prompt = "test"
    language = "python"

    mock_requests_post.side_effect = requests_exception

    # For HTTPError, ensure the response mock is attached to the exception if not already
    # This is important if the exception is instantiated without a response object in the test setup.
    if isinstance(requests_exception, requests.exceptions.HTTPError) and not getattr(requests_exception, 'response', None):
        # Create a basic mock response for HTTPError if it's missing
        mock_resp = MagicMock(spec=requests.Response)
        try:
            # Attempt to parse status code from exception args if possible (e.g. "404 Client Error")
            status_code_str = requests_exception.args[0].split(' ')[0]
            mock_resp.status_code = int(status_code_str) if status_code_str.isdigit() else 500
        except (IndexError, ValueError):
            mock_resp.status_code = 500 # Default if parsing fails
        mock_resp.text = str(requests_exception)
        mock_resp.json.side_effect = json.JSONDecodeError("Cannot decode JSON", "doc", 0) # Default behavior for .json() on error text
        requests_exception.response = mock_resp

    with pytest.raises(expected_llm_error) as excinfo:
        service.generate_code(prompt, language)
    assert error_message_detail in str(excinfo.value)


def test_local_llm_service_json_decode_error(mock_requests_post):
    """Test JSONDecodeError specifically if API returns malformed JSON."""
    service = LocalLLMService()
    prompt = "test"
    language = "python"

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock() # Simulate successful HTTP status
    mock_response.json.side_effect = json.JSONDecodeError("Expecting value", "doc", 0)
    mock_response.text = "This is not JSON" # Add text attribute for error message
    mock_requests_post.return_value = mock_response

    with pytest.raises(LLMAPIError) as excinfo:
        service.generate_code(prompt, language)
    assert "Failed to decode JSON response from Local LLM API" in str(excinfo.value)
    assert "Response text: This is not JSON" in str(excinfo.value)


def test_local_llm_service_generate_code_no_choices(mock_requests_post):
    """Test handling of API response with no 'choices'."""
    service = LocalLLMService()
    mock_response = MagicMock()
    mock_response.json.return_value = {"error": "No choices here"} # Missing 'choices'
    mock_response.raise_for_status = MagicMock()
    mock_requests_post.return_value = mock_response

    with pytest.raises(LLMAPIError) as excinfo:
        service.generate_code("test", "python")
    assert "Local LLM API returned no choices or empty choices array" in str(excinfo.value)

def test_local_llm_service_generate_code_empty_choices(mock_requests_post):
    """Test handling of API response with empty 'choices' list."""
    service = LocalLLMService()
    mock_response = MagicMock()
    mock_response.json.return_value = {"choices": []} # Empty 'choices'
    mock_response.raise_for_status = MagicMock()
    mock_requests_post.return_value = mock_response

    with pytest.raises(LLMAPIError) as excinfo:
        service.generate_code("test", "python")
    assert "Local LLM API returned no choices or empty choices array" in str(excinfo.value)


def test_local_llm_service_generate_code_missing_message_content(mock_requests_post):
    """Test handling of API response choice missing 'message' or 'content'."""
    service = LocalLLMService()
    mock_response = MagicMock()
    # Case 1: 'message' key is missing
    mock_response.json.return_value = {"choices": [{"something_else": "data"}]}
    mock_response.raise_for_status = MagicMock()
    mock_requests_post.return_value = mock_response

    with pytest.raises(LLMAPIError) as excinfo:
        service.generate_code("test", "python")
    assert "Local LLM API response missing message content" in str(excinfo.value)

    # Case 2: 'content' key is missing from message
    mock_response.json.return_value = {"choices": [{"message": {"role": "assistant"}}]} # Missing 'content'
    with pytest.raises(LLMAPIError) as excinfo:
        service.generate_code("test", "python")
    assert "Local LLM API response missing message content" in str(excinfo.value)

def test_local_llm_service_init_no_api_base_url_if_not_localhost_does_not_auto_add_v1():
    """Ensure /v1 is not appended if URL is not localhost-like and doesn't have it."""
    url = "https://api.example.com/custom"
    service = LocalLLMService(api_base_url=url)
    assert service.api_base_url == url
    assert service.chat_completions_url == f"{url}/chat/completions"

def test_local_llm_service_with_api_key(mock_requests_post):
    """Test that API key is included in headers if provided."""
    api_key = "my-local-secure-key"
    service = LocalLLMService(api_key=api_key)
    expected_code = "code"
    mock_response = MagicMock()
    mock_response.json.return_value = {"choices": [{"message": {"content": expected_code}}]}
    mock_response.raise_for_status = MagicMock()
    mock_requests_post.return_value = mock_response

    service.generate_code("prompt", "python")

    expected_headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    call_args = mock_requests_post.call_args
    assert call_args is not None
    assert call_args[1]['headers'] == expected_headers

# To run:
# cd /app
# pytest ai_code_platform/llm_code_generator/tests
