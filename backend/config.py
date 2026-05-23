import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'dev-secret')
    POCKETBASE_URL = os.environ.get('POCKETBASE_URL', 'http://localhost:8090')
    TESTING = False

class TestConfig(Config):
    TESTING = True
    SECRET_KEY = 'test-secret'
