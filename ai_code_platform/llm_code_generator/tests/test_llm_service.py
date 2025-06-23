import pytest
from abc import ABC, abstractmethod
from ..llm_service import LLMService, LLMConfigurationError

# A minimal concrete implementation for testing LLMService if needed,
# or we can just test that it's an ABC.
class MockLLMService(LLMService):
    def generate_code(self, prompt: str, language: str) -> str:
        if not prompt or not language:
            raise ValueError("Prompt and language are required.")
        return f"Mock code for {prompt} in {language}"

def test_llm_service_is_abc():
    """Tests that LLMService is an abstract base class."""
    assert issubclass(LLMService, ABC)
    with pytest.raises(TypeError):
        # Cannot instantiate an ABC with abstract methods
        LLMService()

def test_llm_service_requires_generate_code_implementation():
    """Tests that a subclass must implement generate_code."""
    class IncompleteService(LLMService):
        pass # Does not implement generate_code

    with pytest.raises(TypeError) as excinfo:
        IncompleteService()
    assert "Can't instantiate abstract class IncompleteService" in str(excinfo.value)
    assert "generate_code" in str(excinfo.value)


def test_mock_llm_service_instantiation_and_use():
    """Tests our mock concrete implementation."""
    mock_service = MockLLMService()
    assert isinstance(mock_service, LLMService)
    prompt = "test prompt"
    language = "python"
    result = mock_service.generate_code(prompt, language)
    assert result == f"Mock code for {prompt} in {language}"

def test_llm_configuration_error_can_be_raised_and_caught():
    """Tests that LLMConfigurationError can be raised and caught."""
    error_message = "Test configuration error"
    with pytest.raises(LLMConfigurationError) as excinfo:
        raise LLMConfigurationError(error_message)
    assert str(excinfo.value) == error_message

# Add more tests for other custom exceptions if needed (LLMAPIError, etc.)
# These would typically be tested in the context of the services that raise them.
