import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv("/home/vinay/Swaya.me/backend/.env")

smtp_server = os.getenv("SMTP_HOST", "smtp.titan.email")
port = int(os.getenv("SMTP_PORT", 465))
username = os.getenv("SMTP_USER", "info@chakrix.com")
password = os.getenv("SMTP_PASSWORD", "REDACTED_SMTP_PASSWORD")

print(f"Connecting to {smtp_server}:{port} as {username}...")
print(f"Password length: {len(password) if password else 0}")

try:
    if port == 465:
        server = smtplib.SMTP_SSL(smtp_server, port)
    else:
        server = smtplib.SMTP(smtp_server, port)
        server.starttls()
        
    server.set_debuglevel(1)
    
    # Try logging in
    server.login(username, password)
    print("Login successful!")
    
    server.quit()
    print("Test passed.")
except Exception as e:
    print(f"Failed: {e}")
