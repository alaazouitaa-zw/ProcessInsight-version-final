import sys
import os

# Ajout du chemin parent
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from mail_helper import send_verification_email
    print("Import mail_helper successful!")
    
    # We won't actually send a mail unless required, but let's test if it handles connectivity or invalid login
    # Actually, we can test it with a dummy email to see if it executes without Python errors.
    # Note: this will actually try to connect to smtp.gmail.com.
    # Let's do a dry run of send_email with a non-existent email, it should at least connect and authenticate.
    from mail_helper import send_email
    print("Testing SMTP connection and authentication...")
    # This might fail if the app password or email is invalid, which is a good test.
    res = send_email("test@example.com", "Test ProcessInsight", "<p>Test</p>")
    print(f"Result of send_email: {res}")
except Exception as e:
    print(f"Error during import or test: {e}")
