import argparse
import os
import sys

# Add the parent directory (ai_code_platform) to sys.path
# to allow importing from llm_code_generator
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir) # This should be the project root if cli.py is in ai_code_platform
# This script (cli.py) is intended to be in the `ai_code_platform` directory.
# Imports are relative to this location.
from ai_code_platform.llm_code_generator.llm_service import (
    LLMService,
    LLMConfigurationError,
    LLMAPIError,
)
from ai_code_platform.llm_code_generator.claude_service import ClaudeService
from ai_code_platform.llm_code_generator.local_llm_service import LocalLLMService

# Capture default values at import time so that tests patching the service
# classes don't replace these with mocks.
CLAUDE_DEFAULT_MODEL = ClaudeService.DEFAULT_MODEL
LOCAL_DEFAULT_API_BASE = LocalLLMService.DEFAULT_API_BASE
LOCAL_DEFAULT_MODEL = LocalLLMService.DEFAULT_MODEL


def main():
    parser = argparse.ArgumentParser(description="Generate code using an LLM.")
    parser.add_argument("prompt", type=str, help="The natural language prompt for code generation.")
    parser.add_argument(
        "--service",
        type=str,
        choices=["claude", "local"],
        default="local", # Default to local for easier testing without API keys
        help="The LLM service to use (claude or local). Default: local",
    )
    parser.add_argument(
        "--language",
        type=str,
        default="python",
        help="The programming language for the generated code. Default: python",
    )
    parser.add_argument(
        "--claude-model",
        type=str,
        default=CLAUDE_DEFAULT_MODEL,
        help=(
            "Claude model to use (e.g., claude-3-opus-20240229, "
            f"claude-3-haiku-20240307). Default: {CLAUDE_DEFAULT_MODEL}"
        ),
    )
    parser.add_argument(
        "--local-url",
        type=str,
        default=LOCAL_DEFAULT_API_BASE,
        help=f"Base URL for the local LLM API. Default: {LOCAL_DEFAULT_API_BASE}",
    )
    parser.add_argument(
        "--local-model",
        type=str,
        default=LOCAL_DEFAULT_MODEL,
        help=f"Model name for the local LLM. Default: {LOCAL_DEFAULT_MODEL}",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        help="API key for the LLM service (e.g., Anthropic API Key for Claude, or a key for a secured local LLM). Can also be set via environment variables.",
    )

    args = parser.parse_args()

    llm: LLMService | None = None

    try:
        if args.service == "claude":
            print(f"Using Claude service with model: {args.claude_model}")
            # API key can be passed directly or read from ANTHROPIC_API_KEY env var by the service
            llm = ClaudeService(api_key=args.api_key, model=args.claude_model)
        elif args.service == "local":
            print(f"Using local LLM service. API URL: {args.local_url}, Model: {args.local_model}")
            llm = LocalLLMService(
                api_base_url=args.local_url,
                model=args.local_model,
                api_key=args.api_key or "not-needed" # Pass explicitly if provided
            )
        else:
            # Should not happen due to choices in argparse
            print(f"Error: Unknown service '{args.service}'", file=sys.stderr)
            sys.exit(1)

        print(f"Generating {args.language} code for prompt: '{args.prompt}'")
        generated_code = llm.generate_code(args.prompt, args.language)

        print("\\n--- Generated Code ---")
        print(generated_code)
        print("--- End of Code ---")

    except LLMConfigurationError as e:
        print(f"Configuration Error: {e}", file=sys.stderr)
        if args.service == "claude" and "ANTHROPIC_API_KEY" in str(e):
            print("Hint: Set the ANTHROPIC_API_KEY environment variable or use the --api-key option.", file=sys.stderr)
        elif args.service == "local" and "LOCAL_LLM_API_BASE" in str(e):
            print("Hint: Ensure your local LLM server is running and accessible, or set LOCAL_LLM_API_BASE or use --local-url.", file=sys.stderr)
        sys.exit(1)
    except LLMAPIError as e:
        print(f"API Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    # To make this runnable from the project root as `python ai_code_platform/cli.py ...`
    # and also allow `python cli.py ...` when inside `ai_code_platform` directory,
    # we need to ensure `llm_code_generator` can be found.
    # The try-except at the top for imports handles this.
    # If `ai_code_platform` is in PYTHONPATH, it should also work.

    # For running `python -m ai_code_platform.cli` from the directory *containing* `ai_code_platform`:
    # The imports should be `from .llm_code_generator...` if this was part of a package run with -m.
    # However, for a simple script, the current setup is common.

    main()
