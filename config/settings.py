import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY", "")
AMADEUS_CLIENT_ID = os.getenv("AMADEUS_CLIENT_ID", "")
AMADEUS_CLIENT_SECRET = os.getenv("AMADEUS_CLIENT_SECRET", "")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")
REDIS_URL = os.getenv("REDIS_URL", "")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

LLM_MODEL = "gpt-4o-mini"
LLM_TEMPERATURE = 0.3
MAX_RETRY_ATTEMPTS = 3


def get_llm(temperature: float = LLM_TEMPERATURE):
    """Return a ChatOpenAI instance.

    Reads OPENAI_API_KEY from os.environ at call time so that a key
    entered in the frontend (which sets os.environ) always takes
    priority over the value loaded from .env at startup.
    """
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. "
            "Add it to your .env file or paste it in the app sidebar."
        )
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(model=LLM_MODEL, api_key=key, temperature=temperature)
