import os
from pathlib import Path
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv(override=True)

BASE_DIR = Path(__file__).resolve().parent

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
QUIZ_DEFAULT_LANG = os.getenv("QUIZ_DEFAULT_LANG", "tr")
QUIZ_QUESTION_COUNT = int(os.getenv("QUIZ_QUESTION_COUNT", "20"))
QUIZ_DEFAULT_TIME_LIMIT = int(os.getenv("QUIZ_DEFAULT_TIME_LIMIT", "20"))
SESSION_FILE = BASE_DIR / os.getenv("SESSION_FILE", "session.json")

# Quiz.com Yapılandırması
QUIZ_COM_BASE_URL = "https://quiz.com"
QUIZ_COM_NEW_URL = "https://quiz.com/edit/new/"
QUIZ_COM_LOGIN_URL = "https://quiz.com/user/login/"

# Dahili Giphy İstemci Anahtarı (Quiz.com'un web uygulamasında kullandığı hazır anahtar)
GIPHY_FALLBACK_API_KEY = "XUpZVdLfEzYWDRVl35MmGq8zPdvYX28d"
