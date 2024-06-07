import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = 'localhost'
DB_USER = 'root'
DB_PASSWORD = ''
DB_NAME = 'museum'

BOT_TOKEN = os.getenv('BOT_TOKEN')
