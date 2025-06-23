from abc import ABC, abstractmethod

class LLMService(ABC):
    """
    Abstract base class for LLM services.
    This interface allows for different LLM backends to be used interchangeably.
    """

    @abstractmethod
    def generate_code(self, prompt: str, language: str) -> str:
        """
        Generates code based on a natural language prompt and a specified language.

        Args:
            prompt: The natural language prompt describing the code to be generated.
            language: The programming language for the generated code (e.g., "python", "javascript").

        Returns:
            A string containing the generated code.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
            Exception: For any errors during the API call or code generation process.
        """
        pass

class LLMServiceError(Exception):
    """Custom exception for LLM service-related errors."""
    pass

class LLMAPIError(LLMServiceError):
    """Raised when there's an error communicating with the LLM API."""
    pass

class LLMConfigurationError(LLMServiceError):
    """Raised when the LLM service is not configured correctly (e.g., missing API key)."""
    pass
