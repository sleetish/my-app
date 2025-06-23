import pytest
import os
from unittest.mock import patch, MagicMock
from ..claude_service import ClaudeService, LLMConfigurationError, LLMAPIError
from anthropic import Anthropic, APIConnectionError, RateLimitError, APIStatusError, APIError

@pytest.fixture
def mock_anthropic_constructor(): # Yields the constructor mock
    with patch('anthropic.Anthropic') as mock_constructor:
        # Configure a default instance to be returned by the constructor
        mock_instance = MagicMock(spec=Anthropic)
        # Ensure 'messages' attribute exists on the mock instance and is also a mock
        mock_instance.messages = MagicMock()
        mock_instance.messages.create = MagicMock() # This is what will be called
        mock_constructor.return_value = mock_instance
        yield mock_constructor

@pytest.fixture(autouse=True)
def clear_env_vars():
    # Ensure ANTHROPIC_API_KEY is not set from the test runner's environment
    # to make tests predictable.
    original_val = os.environ.pop("ANTHROPIC_API_KEY", None)
    yield
    if original_val is not None:
        os.environ["ANTHROPIC_API_KEY"] = original_val

def test_claude_service_init_with_api_key_arg():
    """Test ClaudeService initialization with API key argument."""
    api_key = "test_claude_api_key"
    service = ClaudeService(api_key=api_key)
    assert service.api_key == api_key
    assert service.client is not None # The client is the instance from mock_anthropic_constructor.return_value

def test_claude_service_init_with_env_var(mock_anthropic_constructor):
    """Test ClaudeService initialization with ANTHROPIC_API_KEY environment variable."""
    api_key = "env_claude_api_key"
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": api_key}):
        service = ClaudeService() # Constructor is called
        assert service.api_key == api_key
        mock_anthropic_constructor.assert_called_once_with(api_key=api_key) # Assert on constructor

def test_claude_service_init_missing_api_key(mock_anthropic_constructor): # Add fixture if constructor might be called
    """Test ClaudeService initialization fails if no API key is provided."""
    with pytest.raises(LLMConfigurationError) as excinfo:
        ClaudeService()
    assert "Anthropic API key not provided" in str(excinfo.value)

def test_claude_service_init_custom_model():
    """Test ClaudeService initialization with a custom model."""
    api_key = "test_key"
    custom_model = "claude-custom-model"
    service = ClaudeService(api_key=api_key, model=custom_model)
    assert service.model == custom_model

def test_claude_service_generate_code_success(mock_anthropic_constructor):
    """Test successful code generation with ClaudeService."""
    api_key = "test_key"
    # Service instantiation will use the mock_anthropic_constructor
    service = ClaudeService(api_key=api_key)

    # Get the mock instance that the service is using
    mock_client_instance = mock_anthropic_constructor.return_value

    prompt = "create a sum function"
    language = "python"
    expected_code = "def sum(a, b):\\n  return a + b"

    mock_response = MagicMock()
    mock_text_block = MagicMock()
    mock_text_block.text = expected_code
    mock_response.content = [mock_text_block]

    # Set the return value on the 'create' method of the 'messages' mock attribute of the instance
    mock_client_instance.messages.create.return_value = mock_response

    generated_code = service.generate_code(prompt, language)

    assert generated_code == expected_code
    mock_client_instance.messages.create.assert_called_once_with(
        model=service.model,
        max_tokens=2048,
        system=f"You are a helpful coding assistant. Generate only the {language} code for the following prompt. Do not include any explanatory text or markdown formatting around the code. Just output the raw code.",
        messages=[{"role": "user", "content": prompt}],
    )

def test_claude_service_generate_code_with_markdown_stripping(mock_anthropic_constructor):
    """Test code generation where Claude wraps code in markdown."""
    api_key = "test_key"
    service = ClaudeService(api_key=api_key)
    mock_client_instance = mock_anthropic_constructor.return_value

    prompt = "create a sum function"
    language = "python"
    # Test with ```python\ncode\n```
    raw_code_from_llm_lang = f"```{language}\\ndef sum(a, b):\\n  return a + b\\n```"
    expected_stripped_code = "def sum(a, b):\\n  return a + b"

    mock_response_lang = MagicMock()
    mock_text_block_lang = MagicMock()
    mock_text_block_lang.text = raw_code_from_llm_lang
    mock_response_lang.content = [mock_text_block_lang]
    mock_client_instance.messages.create.return_value = mock_response_lang

    generated_code_lang = service.generate_code(prompt, language)
    assert generated_code_lang == expected_stripped_code

    # Test with generic ```\ncode\n```
    mock_client_instance.messages.create.reset_mock()
    raw_code_from_llm_generic = f"```\\ndef sum_generic(a, b):\\n  return a + b\\n```"
    expected_stripped_generic_code = "def sum_generic(a, b):\\n  return a + b"
    mock_response_generic = MagicMock()
    mock_text_block_generic = MagicMock()
    mock_text_block_generic.text = raw_code_from_llm_generic
    mock_response_generic.content = [mock_text_block_generic]
    mock_client_instance.messages.create.return_value = mock_response_generic

    generated_code_generic = service.generate_code(prompt, language) # language still python for system prompt
    assert generated_code_generic == expected_stripped_generic_code


@pytest.mark.parametrize("anthropic_exception_class, mock_args_tuple, expected_llm_error, error_message_detail", [
    (APIConnectionError, ({"message": "Connection failed.", "request": MagicMock()},), LLMAPIError, "Claude API connection error"),
    (RateLimitError, ({"message": "Rate limit.", "response": MagicMock(), "body": None},), LLMAPIError, "Claude API rate limit exceeded"),
    (APIStatusError, ({"message": "Server Error.", "response": MagicMock(status_code=500), "body": None},), LLMAPIError, "Claude API status error (status 500)"),
    (APIError, ({"message": "Some API error", "request": MagicMock(), "body": None},), LLMAPIError, "An unexpected error occurred while calling Claude API"),  # General Anthropic APIError
    (Exception, (("Some other unexpected error",),), LLMAPIError, "An unexpected error occurred while calling Claude API")  # General non-Anthropic exception
])
def test_claude_service_generate_code_api_errors(mock_anthropic_constructor, anthropic_exception_class, mock_args_tuple, expected_llm_error, error_message_detail):
    """Test various API errors during code generation."""
    api_key = "test_key"
    service = ClaudeService(api_key=api_key)
    mock_client_instance = mock_anthropic_constructor.return_value

    prompt = "test"
    language = "python"

    # Instantiate the exception. mock_args_tuple[0] contains the args/kwargs for the exception.
    # If it's Exception, mock_args_tuple[0] is a tuple of args. Otherwise, it's a dict of kwargs.
    constructor_args = mock_args_tuple[0]
    if isinstance(constructor_args, dict):
        anthropic_exception_instance = anthropic_exception_class(**constructor_args)
    else:
        anthropic_exception_instance = anthropic_exception_class(*constructor_args)

    mock_client_instance.messages.create.side_effect = anthropic_exception_instance

    with pytest.raises(expected_llm_error) as excinfo:
        service.generate_code(prompt, language)
    assert error_message_detail in str(excinfo.value)


def test_claude_service_generate_code_empty_response(mock_anthropic_constructor):
    """Test handling of empty or unexpected response content from Claude API."""
    api_key = "test_key"
    service = ClaudeService(api_key=api_key)
    mock_client_instance = mock_anthropic_constructor.return_value
    prompt = "test"
    language = "python"

    mock_response = MagicMock()
    mock_response.content = [] # Empty content list
    mock_client_instance.messages.create.return_value = mock_response

    with pytest.raises(LLMAPIError) as excinfo:
        service.generate_code(prompt, language)
    assert "Claude API returned an empty or unexpected response content" in str(excinfo.value)

def test_claude_service_generate_code_response_no_text_block(mock_anthropic_constructor):
    """Test handling of response content block without 'text' attribute."""
    api_key = "test_key"
    service = ClaudeService(api_key=api_key)
    mock_client_instance = mock_anthropic_constructor.return_value
    prompt = "test"
    language = "python"

    mock_response = MagicMock()
    mock_non_text_block = MagicMock()
    del mock_non_text_block.text # Ensure it has no 'text' attribute
    mock_response.content = [mock_non_text_block]
    mock_client_instance.messages.create.return_value = mock_response

    with pytest.raises(LLMAPIError) as excinfo:
        service.generate_code(prompt, language)
    assert "Claude API response content block does not have text" in str(excinfo.value)

def test_anthropic_client_initialization_failure(mock_anthropic_constructor): # Use the constructor mock
    """Test LLMConfigurationError if Anthropic client fails to initialize."""
    with patch('anthropic.Anthropic', side_effect=Exception("Init failed")):
        with pytest.raises(LLMConfigurationError) as excinfo:
            ClaudeService(api_key="some_key")
        assert "Failed to initialize Anthropic client: Init failed" in str(excinfo.value)

# To run these tests, you would typically use pytest:
# Ensure pytest is installed: pip install pytest
# Navigate to the directory containing `ai_code_platform` (e.g., `/app`)
# Run: pytest ai_code_platform/llm_code_generator/tests
# Or from within `ai_code_platform`: pytest llm_code_generator/tests
