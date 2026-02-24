import os
from pathlib import Path


def load_dotenv() -> None:
    """Load .env file from project root into os.environ (if it exists)."""
    # Walk up from this file to find the project root (where pyproject.toml lives)
    current = Path(__file__).resolve().parent
    for ancestor in [current, *current.parents]:
        env_file = ancestor / ".env"
        if env_file.is_file():
            for line in env_file.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip("\"'")
                if not os.environ.get(key):
                    os.environ[key] = value
            return
