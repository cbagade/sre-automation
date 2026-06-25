"""Configuration package."""

# Import from parent config.py to maintain compatibility
import sys
from pathlib import Path

# Add parent directory to path to import config.py
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

# Import all config variables from config.py
try:
    from config import (
        PROJECT_ROOT,
        DATA_DIR,
        CHROMA_DB_PATH,
        RCA_DATA_INGEST_PATH,
        RCA_DATA_DISPLAY_PATH,
        OPENAI_DEFAULT_MODEL,
        DEBUG,
        LANGFUSE_PUBLIC_KEY,
        LANGFUSE_SECRET_KEY,
        LANGFUSE_HOST,
        LANGFUSE_ENABLED,
    )
except ImportError:
    # Fallback if config.py is not found
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    PROJECT_ROOT = Path(__file__).parent.parent.absolute()
    DATA_DIR = PROJECT_ROOT / "data"
    CHROMA_DB_PATH = DATA_DIR / "chroma"
    RCA_DATA_INGEST_PATH = DATA_DIR / "rca_data_ingest.json"
    RCA_DATA_DISPLAY_PATH = DATA_DIR / "rca_data_display.json"
    OPENAI_DEFAULT_MODEL = "gpt-4o-mini"
    DEBUG = True
    LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
    LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
    LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
    LANGFUSE_ENABLED = os.getenv("LANGFUSE_ENABLED", "false").lower() == "true"

# Made with Bob
