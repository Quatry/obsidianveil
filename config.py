import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
PAYMENT_TOKEN = os.getenv("PAYMENT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///bot.db")

PRIVATE_GROUP_CHAT_ID = int(os.getenv("PRIVATE_GROUP_CHAT_ID", 0))

PUBLIC_GROUP_URL = os.getenv("PUBLIC_GROUP_URL")

BLOG_URL = os.getenv("BLOG_URL")

ADMIN_URL = os.getenv("ADMIN_URL")