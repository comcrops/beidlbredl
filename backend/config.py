import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'dev-secret')
    POCKETBASE_URL = os.environ.get('POCKETBASE_URL', 'http://localhost:8090')
    AUTHENTIK_URL = os.environ.get('AUTHENTIK_URL', '')
    AUTHENTIK_APP_SLUG = os.environ.get('AUTHENTIK_APP_SLUG', '')
    AUTHENTIK_CLIENT_ID = os.environ.get('AUTHENTIK_CLIENT_ID', '')
    KIOSK_SECRET = os.environ.get('KIOSK_SECRET', '')
    TESTING = False

class TestConfig(Config):
    TESTING = True
    SECRET_KEY = 'test-secret'
