import os
import imaplib
from dotenv import load_dotenv

load_dotenv("/home/vinay/Swaya.me/backend/.env")

imap_server = os.getenv("IMAP_HOST", "imap.titan.email")
port = int(os.getenv("IMAP_PORT", 993))
username = os.getenv("SMTP_USER", "info@chakrix.com")
password = os.getenv("SMTP_PASSWORD", "REDACTED_SMTP_PASSWORD")

print(f"Connecting to {imap_server}:{port} as {username}...")

try:
    if port == 993:
        server = imaplib.IMAP4_SSL(imap_server, port)
    else:
        server = imaplib.IMAP4(imap_server, port)
        
    # Try logging in
    server.login(username, password)
    print("Login successful!")
    
    server.logout()
    print("Test passed.")
except Exception as e:
    print(f"Failed: {e}")
