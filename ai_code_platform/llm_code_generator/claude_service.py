import os
import os
import anthropic
import re # For markdown stripping
from .llm_service import LLMService, LLMAPIError, LLMConfigurationError

class ClaudeService(LLMService):
    """
    LLM Service implementation for Anthropic's Claude API.
    """
    DEFAULT_MODEL = "claude-3-opus-20240229" # Or a smaller/faster model like claude-3-haiku-20240307

    def __init__(self, api_key: str | None = None, model: str | None = None):
        """
        Initializes the ClaudeService.

        Args:
            api_key: The Anthropic API key. If None, it will try to read from
                     the ANTHROPIC_API_KEY environment variable.
            model: The Claude model to use (e.g., "claude-3-opus-20240229").
                   Defaults to ClaudeService.DEFAULT_MODEL.

        Raises:
            LLMConfigurationError: If the API key is not provided or found in env variables.
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise LLMConfigurationError(
                "Anthropic API key not provided or found in ANTHROPIC_API_KEY environment variable."
            )
        self.model = model or self.DEFAULT_MODEL
        try:
            self.client = anthropic.Anthropic(api_key=self.api_key)
        except Exception as e:
            raise LLMConfigurationError(f"Failed to initialize Anthropic client: {e}")


    def generate_code(self, prompt: str, language: str) -> str:
        """
        Generates code using the Claude API.

        Args:
            prompt: The natural language prompt.
            language: The programming language (e.g., "python").

        Returns:
            The generated code as a string.

        Raises:
            LLMAPIError: If there's an error during the API call.
        """
        system_prompt = f"You are a helpful coding assistant. Generate only the {language} code for the following prompt. Do not include any explanatory text or markdown formatting around the code. Just output the raw code."

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048, # Adjust as needed
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )

            if response.content and isinstance(response.content, list) and len(response.content) > 0:
                # Assuming the first content block is the code
                # Further checks might be needed if Claude sends multiple blocks or non-text blocks
                block = response.content[0]
                if hasattr(block, 'text'):
                    raw_code = block.text.strip()

                    # Try to extract from language-specific block first
                    # Pattern: ```python\n(.*?)```
                    match_lang = re.search(f"```{re.escape(language)}\\s*\\n(.*?)\\n```", raw_code, re.DOTALL)
                    if match_lang:
                        return match_lang.group(1).strip()

                    # If not found, try to extract from a generic block: ```\n(.*?)```
                    match_generic = re.search(r"```\s*\\n(.*?)\\n```", raw_code, re.DOTALL)
                    if match_generic:
                        return match_generic.group(1).strip()

                    # If still no fenced block, but it starts/ends with ``` (e.g. ```code``` on one line, or ```\ncode\n```)
                    if raw_code.startswith("```") and raw_code.endswith("```"):
                        # Strip initial ``` and final ```
                        stripped_code = raw_code[3:-3].strip()
                        # If what remains starts with the language (e.g. "python\n..."), remove that line.
                        # This handles cases like ```python\ncode``` where the earlier regex didn't match due to no newline after lang.
                        lines = stripped_code.splitlines()
                        if lines and lines[0].strip().lower() == language.lower(): # Check if first line is just the language
                            stripped_code = "\n".join(lines[1:]).strip()
                        return stripped_code

                    # If none of the above, assume it's raw code or LLM didn't use fences as expected
                    return raw_code
                else:
                    raise LLMAPIError("Claude API response content block does not have text.")
            else:
                raise LLMAPIError("Claude API returned an empty or unexpected response content.")

        except anthropic.APIConnectionError as e:
            raise LLMAPIError(f"Claude API connection error: {e}")
        except anthropic.RateLimitError as e:
            raise LLMAPIError(f"Claude API rate limit exceeded: {e}")
        except anthropic.APIStatusError as e:
            raise LLMAPIError(f"Claude API status error (status {e.status_code}): {e.response}")
        except Exception as e:
            raise LLMAPIError(f"An unexpected error occurred while calling Claude API: {e}")

if __name__ == '__main__':
    # This is for basic manual testing.
    # Ensure ANTHROPIC_API_KEY is set in your environment.
    print("Attempting to test ClaudeService...")
    try:
        # Replace with a smaller, faster model for testing if Opus is too slow/expensive
        # For example, "claude-3-haiku-20240307"
        # Ensure you have access to the model you specify.
        claude = ClaudeService(model="claude-3-haiku-20240307")
        test_prompt = "Create a Python function that takes two numbers and returns their sum."
        print(f"Prompt: {test_prompt}")
        generated_python_code = claude.generate_code(test_prompt, "python")
        print("\\nGenerated Python Code:\\n")
        print(generated_python_code)

        print("\\n" + "="*20 + "\\n")

        test_js_prompt = "Create a JavaScript function that takes a string and returns its length."
        print(f"Prompt: {test_js_prompt}")
        generated_js_code = claude.generate_code(test_js_prompt, "javascript")
        print("\\nGenerated JavaScript Code:\\n")
        print(generated_js_code)

    except LLMConfigurationError as e:
        print(f"Configuration Error: {e}")
        print("Please ensure ANTHROPIC_API_KEY is set in your environment variables.")
    except LLMAPIError as e:
        print(f"API Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
