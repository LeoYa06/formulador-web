import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv

# Carga las variables de entorno de tu archivo .env
load_dotenv()

# --- IMPORTANTE: RELLENA ESTOS DATOS ---
# 1. Asegúrate de que tu clave esté en el archivo .env
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")

# 2. El correo que verificaste como "Single Sender" en SendGrid
FROM_EMAIL = 'info@elmefood.com' 

# 3. Un correo donde quieras recibir la prueba (puede ser el mismo)
TO_EMAIL = 'lyaguana06@gmail.com' 
# ------------------------------------

print("Intentando enviar un correo...")
print(f"De: {FROM_EMAIL}")
print(f"A: {TO_EMAIL}")

if not SENDGRID_API_KEY:
    print("Error: La variable SENDGRID_API_KEY no está definida. Revisa tu archivo .env.")
else:
    message = Mail(
        from_email=FROM_EMAIL,
        to_emails=TO_EMAIL,
        subject='Prueba de SendGrid desde Script de Python',
        html_content='<strong>Este es un correo de prueba. Si lo recibiste, ¡tu clave API y tu remitente funcionan!</strong>'
    )
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        print(f"¡Correo enviado! Código de Estado: {response.status_code}")
        print("Revisa tu bandeja de entrada.")
    except Exception as e:
        print(f"Ocurrió un error: {e}")