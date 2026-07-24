import os
from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
ADMIN_PHONE = os.getenv("ADMIN_PHONE")
DATABASE_URL = os.getenv("DATABASE_URL")
