from dotenv import load_dotenv
from os import getenv
from pathlib import Path


env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

SECRET_KEY = getenv("SECRET_KEY", "dev_secret_key_123")
ALGORITHM = "HS256"


DATABASE_URL = getenv("DATABASE_URL", "sqlite:///./casino.db")


ADMIN_TOKEN = getenv("ADMIN_TOKEN", "changeme_admin_token")