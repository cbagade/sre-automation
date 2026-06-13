"""Application configuration settings

This file contains non-sensitive configuration that can be checked into version control.
Sensitive data like API keys should remain in .env file.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Model configuration
OPENAI_DEFAULT_MODEL = "gpt-4o-mini"  # Options: gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo

# Debug mode
DEBUG = True

# Langfuse configuration
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST") or os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")
LANGFUSE_ENABLED = os.getenv("LANGFUSE_ENABLED", "false").lower() == "true"

# Made with Bob
