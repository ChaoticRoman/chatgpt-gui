import os

from .constants import DATA_DIRECTORY


def ensure_key():
    if "OPENAI_API_KEY" in os.environ:
        return
    
    paths_to_search = [
        os.path.join(os.path.dirname(__file__), "..", ".api_key"),
        os.path.join(DATA_DIRECTORY, ".api_key")
    ]
    for api_key_path in paths_to_search:
        if os.path.isfile(api_key_path) or os.path.islink(api_key_path):
            with open(api_key_path, "r") as f:
                os.environ["OPENAI_API_KEY"] = f.read().strip()
            return
    raise RuntimeError("API key not found.")
