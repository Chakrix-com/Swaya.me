import asyncio
import os
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load from backend directory
load_dotenv("/home/vinay/Swaya.me/backend/.env")

from core.auth.email_service import send_verification_email

async def test_email():
    logger.info("Starting email test...")
    logger.info(f"SMTP HOST: {os.getenv('SMTP_HOST')}")
    logger.info(f"SMTP USER: {os.getenv('SMTP_USER')}")
    
    # Try sending to your email
    success = await send_verification_email(
        email="roliverma06@gmail.com", 
        token="test_token_123", 
        name="Test User"
    )
    
    if success:
        logger.info("Email was sent successfully according to FastAPI-Mail!")
    else:
        logger.error("Email sending failed!")

if __name__ == "__main__":
    asyncio.run(test_email())
