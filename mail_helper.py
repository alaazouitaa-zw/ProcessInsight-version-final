import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from html import escape

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
SENDER_EMAIL = "appthermoadmin@gmail.com"
SENDER_PASSWORD = "jyno yywp zkad fmlf"

def send_email(to_email, subject, html_content, reply_to=None):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"ProcessInsight Admin <{SENDER_EMAIL}>"
    msg["To"] = to_email
    if reply_to:
        msg["Reply-To"] = reply_to
    
    part = MIMEText(html_content, "html")
    msg.attach(part)
    
    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=5) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        print(f"Email sent to {to_email}")
        return True
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")
        return False

def send_verification_email(user_email, token, base_url=None):
    if base_url:
        link = f"{base_url}/verify/{token}"
    else:
        link = f"http://127.0.0.1:5000/verify/{token}"
    subject = "ProcessInsight - Activation de votre compte"
    html_content = f"""
    <html>
      <body style="font-family: 'Outfit', 'Inter', Arial, sans-serif; background-color: #0b0f19; color: #f8fafc; padding: 40px 20px; margin: 0;">
        <div style="max-width: 550px; margin: 0 auto; background: rgba(15, 23, 42, 0.9); padding: 40px; border-radius: 20px; border: 1px solid rgba(245, 158, 11, 0.2); box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5); text-align: center;">
          <div style="font-size: 2.5rem; margin-bottom: 20px; filter: drop-shadow(0 0 10px rgba(245,158,11,0.2));">🚀</div>
          <h2 style="color: #fff; font-size: 1.8rem; font-weight: 700; margin-bottom: 10px; font-family: 'Outfit', sans-serif;">Bienvenue sur ProcessInsight !</h2>
          <p style="color: #f59e0b; font-size: 1rem; font-weight: 500; margin-top: 0; margin-bottom: 25px;">Intelligence Thermodynamique</p>
          
          <p style="color: #cbd5e1; font-size: 1rem; line-height: 1.6; text-align: left; margin-bottom: 30px;">
            Merci de vous être inscrit sur notre plateforme. Pour activer votre compte et commencer vos simulations thermodynamiques assistées par IA, veuillez cliquer sur le bouton ci-dessous :
          </p>
          
          <div style="text-align: center; margin: 35px 0;">
            <a href="{link}" style="background: linear-gradient(135deg, #d97706 0%, #f43f5e 100%); color: white; padding: 14px 32px; text-decoration: none; border-radius: 30px; font-weight: 700; display: inline-block; box-shadow: 0 4px 15px rgba(217, 119, 6, 0.4); font-size: 1.05rem;">Activer mon compte ➔</a>
          </div>
          
          <p style="font-size: 0.85rem; color: #64748b; text-align: left; margin-top: 30px;">
            Si le bouton ne fonctionne pas, vous pouvez copier et coller ce lien dans votre navigateur :<br>
            <a href="{link}" style="color: #f59e0b; text-decoration: none; word-break: break-all;">{link}</a>
          </p>
          <hr style="border: 0; border-top: 1px solid rgba(255, 255, 255, 0.08); margin: 30px 0;">
          <p style="font-size: 0.8rem; color: #64748b; margin-bottom: 0;">Cet e-mail a été généré automatiquement par ProcessInsight. Merci de ne pas y répondre.</p>
        </div>
      </body>
    </html>
    """
    return send_email(user_email, subject, html_content)

def send_reset_email(user_email, token, base_url=None):
    if base_url:
        link = f"{base_url}/reset_password/{token}"
    else:
        link = f"http://127.0.0.1:5000/reset_password/{token}"
    subject = "ProcessInsight - Réinitialisation de votre mot de passe"
    html_content = f"""
    <html>
      <body style="font-family: 'Outfit', 'Inter', Arial, sans-serif; background-color: #0b0f19; color: #f8fafc; padding: 40px 20px; margin: 0;">
        <div style="max-width: 550px; margin: 0 auto; background: rgba(15, 23, 42, 0.9); padding: 40px; border-radius: 20px; border: 1px solid rgba(245, 158, 11, 0.2); box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5); text-align: center;">
          <div style="font-size: 2.5rem; margin-bottom: 20px; filter: drop-shadow(0 0 10px rgba(244, 63, 94, 0.2));">🔒</div>
          <h2 style="color: #fff; font-size: 1.8rem; font-weight: 700; margin-bottom: 10px; font-family: 'Outfit', sans-serif;">Réinitialisation de mot de passe</h2>
          <p style="color: #f43f5e; font-size: 1rem; font-weight: 500; margin-top: 0; margin-bottom: 25px;">Sécurité & Protection</p>
          
          <p style="color: #cbd5e1; font-size: 1rem; line-height: 1.6; text-align: left; margin-bottom: 30px;">
            Nous avons reçu une demande de réinitialisation de mot de passe pour votre compte ProcessInsight. Si vous êtes à l'origine de cette demande, veuillez cliquer sur le bouton ci-dessous :
          </p>
          
          <div style="text-align: center; margin: 35px 0;">
            <a href="{link}" style="background: linear-gradient(135deg, #d97706 0%, #f43f5e 100%); color: white; padding: 14px 32px; text-decoration: none; border-radius: 30px; font-weight: 700; display: inline-block; box-shadow: 0 4px 15px rgba(217, 119, 6, 0.4); font-size: 1.05rem;">Réinitialiser mon mot de passe ➔</a>
          </div>
          
          <p style="color: #cbd5e1; font-size: 0.9rem; line-height: 1.6; text-align: left; margin-bottom: 25px;">
            Si vous n'avez pas demandé cette réinitialisation, vous pouvez ignorer cet e-mail en toute sécurité. Votre mot de passe restera inchangé.
          </p>
          
          <p style="font-size: 0.85rem; color: #64748b; text-align: left; margin-top: 30px;">
            Si le bouton ne fonctionne pas, vous pouvez copier et coller ce lien dans votre navigateur :<br>
            <a href="{link}" style="color: #f59e0b; text-decoration: none; word-break: break-all;">{link}</a>
          </p>
          <hr style="border: 0; border-top: 1px solid rgba(255, 255, 255, 0.08); margin: 30px 0;">
          <p style="font-size: 0.8rem; color: #64748b; margin-bottom: 0;">Cet e-mail a été généré automatiquement par ProcessInsight. Merci de ne pas y répondre.</p>
        </div>
      </body>
    </html>
    """
    return send_email(user_email, subject, html_content)

def send_contact_email(name, email, subject, message):
    safe_name = escape(name.strip())
    safe_email = escape(email.strip())
    safe_subject = escape(subject.strip())
    safe_message = escape(message.strip()).replace("\n", "<br>")

    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background-color: #0b0f19; color: #f8fafc; padding: 30px;">
        <div style="max-width: 650px; margin: 0 auto; background: #111827; border: 1px solid rgba(245, 158, 11, 0.25); border-radius: 16px; padding: 28px;">
          <h2 style="margin-top: 0; color: #f59e0b;">Nouveau message depuis ProcessInsight</h2>
          <p><strong>Nom :</strong> {safe_name}</p>
          <p><strong>E-mail :</strong> {safe_email}</p>
          <p><strong>Sujet :</strong> {safe_subject}</p>
          <div style="margin-top: 24px; padding: 18px; background: rgba(255,255,255,0.04); border-radius: 10px; line-height: 1.6;">
            {safe_message}
          </div>
        </div>
      </body>
    </html>
    """
    return send_email(SENDER_EMAIL, f"Contact ProcessInsight - {safe_subject}", html_content, reply_to=email.strip())
