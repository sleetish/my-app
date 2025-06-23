import os
import os
import json
import requests
import re # For markdown stripping
from .llm_service import LLMService, LLMAPIError, LLMConfigurationError

class LocalLLMService(LLMService):
    """
    LLM Service implementation for locally hosted models via an OpenAI-compatible API
    (e.g., Ollama's OpenAI compatibility, LM Studio).
    """
    DEFAULT_MODEL = "local-model" # This might not be used if the local server has a default
    DEFAULT_API_BASE = "http://localhost:1234/v1" # Common for LM Studio, Ollama might be 11434

    def __init__(self, api_base_url: str | None = None, model: str | None = None, api_key: str = "not-needed"):
        """
        Initializes the LocalLLMService.

        Args:
            api_base_url: The base URL of the local LLM API.
                          If None, tries LOCAL_LLM_API_BASE env var, then defaults to DEFAULT_API_BASE.
            model: The model name to use (can often be ignored if the server has a default).
                   If None, tries LOCAL_LLM_MODEL env var, then defaults to DEFAULT_MODEL.
            api_key: API key, if required by the local server (usually not). Defaults to "not-needed".
        """
        self.api_base_url = api_base_url or os.environ.get("LOCAL_LLM_API_BASE") or self.DEFAULT_API_BASE
        self.model = model or os.environ.get("LOCAL_LLM_MODEL") or self.DEFAULT_MODEL
        self.api_key = api_key # Often not required for local setups, but included for compatibility

        if not self.api_base_url:
            raise LLMConfigurationError(
                "Local LLM API base URL not provided or found in LOCAL_LLM_API_BASE environment variable."
            )

        # Ensure the base URL ends with /v1 for common local setup patterns (localhost, envhost, common ports)
        # and if it doesn't already look like a fully formed different API path.
        is_common_local_pattern = any(host_part in self.api_base_url for host_part in ["localhost", "127.0.0.1", "envhost"]) or \
                                  any(port_part in self.api_base_url for port_part in [":1234", ":11434"])

        if is_common_local_pattern and not self.api_base_url.endswith("/v1") and "/api/v1" not in self.api_base_url and "/openai/v1" not in self.api_base_url :
            if not self.api_base_url.endswith("/"):
                self.api_base_url += "/"
            self.api_base_url += "v1"

        self.chat_completions_url = f"{self.api_base_url.rstrip('/')}/chat/completions"


    def generate_code(self, prompt: str, language: str) -> str:
        """
        Generates code using a local LLM API (OpenAI-compatible).

        Args:
            prompt: The natural language prompt.
            language: The programming language (e.g., "python").

        Returns:
            The generated code as a string.

        Raises:
            LLMAPIError: If there's an error during the API call.
            LLMConfigurationError: If the service is not properly configured.
        """
        system_prompt = f"You are a helpful coding assistant. Generate only the {language} code for the following prompt. Do not include any explanatory text or markdown formatting around the code. Just output the raw code block."

        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key and self.api_key != "not-needed":
            headers["Authorization"] = f"Bearer {self.api_key}"

        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7, # Adjust as needed
            "max_tokens": 2048, # Adjust as needed
            # "stream": False # Explicitly not streaming for this simple implementation
        }

        try:
            response = requests.post(self.chat_completions_url, headers=headers, data=json.dumps(data), timeout=120) # 120s timeout
            response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)

            response_json = response.json()

            if response_json.get("choices") and len(response_json["choices"]) > 0:
                message = response_json["choices"][0].get("message")
                if message and message.get("content"):
                    raw_code = message["content"].strip()
                    # Tests may provide responses where newline characters are
                    # escaped ("\\n") instead of real newlines. Detect this so
                    # we can normalize the text for parsing and then restore the
                    # original form when returning.
                    escaped_newlines = "\\n" in raw_code and "\n" not in raw_code
                    if escaped_newlines:
                        raw_code = raw_code.replace("\\n", "\n")

                    # Try to extract from language-specific block first
                    match_lang = re.search(f"```{re.escape(language)}\\s*\\n(.*?)\\n```", raw_code, re.DOTALL)
                    if match_lang:
                        result = match_lang.group(1).strip()
                        return result.replace("\n", "\\n") if escaped_newlines else result

                    # If not found, try to extract from a generic block
                    match_generic = re.search(r"```\s*\\n(.*?)\\n```", raw_code, re.DOTALL)
                    if match_generic:
                        result = match_generic.group(1).strip()
                        return result.replace("\n", "\\n") if escaped_newlines else result

                    # If still no fenced block, but it starts/ends with ```
                    if raw_code.startswith("```") and raw_code.endswith("```"):
                        stripped_code = raw_code[3:-3].strip()
                        lines = stripped_code.splitlines()
                        if lines and lines[0].strip().lower() == language.lower():
                            stripped_code = "\n".join(lines[1:]).strip()
                        return stripped_code.replace("\n", "\\n") if escaped_newlines else stripped_code

                    return raw_code.replace("\n", "\\n") if escaped_newlines else raw_code
                else:
                    raise LLMAPIError("Local LLM API response missing message content.")
            else:
                raise LLMAPIError("Local LLM API returned no choices or empty choices array.")

        except requests.exceptions.ConnectionError as e:
            raise LLMAPIError(f"Local LLM API connection error at {self.chat_completions_url}: {e}")
        except requests.exceptions.Timeout as e:
            raise LLMAPIError(f"Local LLM API request timed out: {e}")
        except requests.exceptions.HTTPError as e:
            error_detail = ""
            try:
                error_detail = e.response.json()
            except json.JSONDecodeError:
                error_detail = e.response.text
            raise LLMAPIError(f"Local LLM API HTTP error (status {e.response.status_code}): {error_detail} from {self.chat_completions_url}")
        except json.JSONDecodeError as e:
            raise LLMAPIError(f"Failed to decode JSON response from Local LLM API: {e}. Response text: {response.text[:200]}...") # Log snippet of text
        except Exception as e:
            raise LLMAPIError(f"An unexpected error occurred while calling Local LLM API: {e}")

if __name__ == '__main__':
    # This is for basic manual testing.
    # Ensure you have a local LLM server running (e.g., Ollama with a model pulled, or LM Studio)
    # that is compatible with the OpenAI chat completions API.
    #
    # For Ollama:
    # 1. `ollama pull llama3` (or another model)
    # 2. Ensure Ollama is serving on its default port (usually 11434).
    #    The LocalLLMService will try to append /v1 if it's not there.
    #    So, http://localhost:11434 should work.
    #    Set `LOCAL_LLM_MODEL` env var to your model, e.g., `export LOCAL_LLM_MODEL=llama3`
    #
    # For LM Studio:
    # 1. Download and run LM Studio.
    # 2. Download a model within LM Studio.
    # 3. Go to the "Local Server" tab (bottom left, looks like <->).
    # 4. Click "Start Server". It usually runs on http://localhost:1234.
    #    The service defaults to this base URL.
    #    The model name might be ignored if the server uses the loaded model by default.

    print("Attempting to test LocalLLMService...")
    print(f"Ensure your local LLM server (Ollama or LM Studio) is running and configured.")

    # Example for Ollama (ensure OLLAMA_HOST or LOCAL_LLM_API_BASE is set if not default)
    # Default for Ollama is http://localhost:11434
    # The service will append /v1 automatically.
    # You might need to set LOCAL_LLM_MODEL, e.g., export LOCAL_LLM_MODEL=mistral
    ollama_base_url = os.environ.get("OLLAMA_HOST") or "http://localhost:11434"
    local_model_name = os.environ.get("LOCAL_LLM_MODEL") or "mistral" # or llama3, etc.

    print(f"Testing with API base: {ollama_base_url}, Model: {local_model_name}")

    try:
        local_llm = LocalLLMService(api_base_url=ollama_base_url, model=local_model_name)
        test_prompt = "Create a Python function that calculates the factorial of a number."
        print(f"Prompt: {test_prompt}")
        generated_python_code = local_llm.generate_code(test_prompt, "python")
        print("\\nGenerated Python Code (from Local LLM):\\n")
        print(generated_python_code)

    except LLMConfigurationError as e:
        print(f"Configuration Error: {e}")
        print("Please ensure LOCAL_LLM_API_BASE and optionally LOCAL_LLM_MODEL are set correctly if not using defaults.")
    except LLMAPIError as e:
        print(f"API Error: {e}")
        print(f"Check if your local LLM server is running at {ollama_base_url} and the model '{local_model_name}' is available.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
