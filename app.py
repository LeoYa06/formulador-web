# app.py
import os
import random
import secrets
import time
import httpx
import certifi
import stripe
from datetime import datetime, timedelta
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from flask import session
from flask import Flask, render_template, jsonify, request, flash, redirect, url_for
from werkzeug.security import check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from openai import OpenAI, APIConnectionError
from dotenv import load_dotenv

# Importamos nuestras funciones de base de datos y cálculos
import database
import calculations

# --- 1. CONFIGURACIÓN INICIAL ---
load_dotenv()
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'una-clave-secreta-muy-dificil-de-adivinar')

# Configuración de Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
stripe_price_id = os.getenv('STRIPE_PRICE_ID')
stripe_webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')

# Verificar y sanear la clave de API
api_key_raw = os.getenv('OPENAI_API_KEY')
client = None # Inicializar cliente como None

if not api_key_raw:
    print("ERROR: No se encontró OPENAI_API_KEY en las variables de entorno")
else:
    # Eliminar espacios en blanco y saltos de línea
    api_key = api_key_raw.strip()
    if not api_key:
        print("ERROR: La variable OPENAI_API_KEY está vacía después de sanearla.")
    else:
        print(f"INFO: Clave de API de OpenAI: {api_key[:4]}... (truncada por seguridad)")
        # Configurar el cliente de OpenAI
        try:
            # Pasando explícitamente la clave saneada
            client = OpenAI(api_key=api_key, timeout=60.0)
            print("INFO: Cliente de OpenAI configurado con la clave de API saneada.")
        except Exception as e:
            print(f"ERROR: No se pudo configurar el cliente de OpenAI. Error: {e}")
            client = None

# --- 2. CONFIGURACIÓN DE FLASK-LOGIN ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Por favor, inicia sesión para acceder a esta página."

class User(UserMixin):
    def __init__(self, id, username, full_name, is_verified=False):
        self.id = id
        self.username = username
        self.full_name = full_name
        self.is_verified = is_verified

@login_manager.user_loader
def load_user(user_id):
    user_data = database.get_user_by_id(int(user_id))
    if user_data:
        return User(
            id=user_data['id'],
            username=user_data['username'],
            full_name=user_data.get('full_name', ''),
            is_verified=user_data.get('is_verified', False)
        )
    return None

# --- 3. RUTAS DE AUTENTICACIÓN Y PAGO ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Maneja el registro de nuevos usuarios."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        username = request.form.get('username')  # Correo
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        terms_accepted = request.form.get('terms')

        if not all([full_name, username, password, confirm_password, terms_accepted]):
            flash('Todos los campos son requeridos.')
            return redirect(url_for('register'))
        
        if password != confirm_password:
            flash('Las contraseñas no coinciden.')
            return redirect(url_for('register'))

        if database.get_user_by_username(username):
            flash('Este correo electrónico ya está registrado.')
            return redirect(url_for('register'))
        
        verification_code = str(random.randint(100000, 999999))
        code_expiry = datetime.utcnow() + timedelta(minutes=15)

        if database.add_user(username, password, full_name, verification_code, code_expiry):
            message = Mail(
                from_email='info@elmefood.com',
                to_emails=username,
                subject='Código de Verificación - Formulador de Embutidos',
                html_content=f'<h3>Hola {full_name},</h3><p>Tu código de verificación es: <strong>{verification_code}</strong></p>'
            )
            try:
                sendgrid_client = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
                sendgrid_client.send(message)
            except Exception as e:
                print(f"Error enviando correo: {e}")
                flash('Ocurrió un error al enviar el correo de verificación.')
                return redirect(url_for('register'))

            flash('¡Cuenta creada! Te hemos enviado un código de verificación.')
            return redirect(url_for('verify', email=username))
        else:
            flash('Ocurrió un error al crear la cuenta.')

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Maneja el inicio de sesión de los usuarios."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user_data = database.get_user_by_username(username)

        if user_data and check_password_hash(user_data['password_hash'], password):
            if not user_data.get('is_verified'):
                flash('Tu cuenta no está verificada.')
                return redirect(url_for('verify', email=username))

            session_token = secrets.token_hex(32)
            database.update_session_token(user_data['id'], session_token)
            session['session_token'] = session_token
            
            user = User(id=user_data['id'], username=user_data['username'], full_name=user_data.get('full_name', ''), is_verified=user_data.get('is_verified'))
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Login incorrecto. Revisa tu email y contraseña.')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión exitosamente.')
    return redirect(url_for('login'))

@app.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    try:
        checkout_session = stripe.checkout.Session.create(
            line_items=[{'price': stripe_price_id, 'quantity': 1}],
            mode='subscription',
            success_url='https://elmefood.com/pago-exitoso',
            cancel_url='https://elmefood.com/pago-cancelado',
            client_reference_id=current_user.id
        )
        return jsonify({'url': checkout_session.url})
    except Exception as e:
        return jsonify(error=str(e)), 500

@app.route('/webhook', methods=['POST'])
def webhook():
    event = None
    payload = request.data
    sig_header = request.headers.get('stripe-signature')

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, stripe_webhook_secret)
    except ValueError as e:
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError as e:
        return 'Invalid signature', 400

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        user_id = session.get('client_reference_id')
        if user_id:
            print(f"Pago exitoso para el usuario: {user_id}. Añadiendo 1000 créditos...")
            database.add_user_credits(int(user_id), 1000)
            print(f"Créditos actualizados para el usuario {user_id}.")

    return 'Success', 200

@app.route('/pago-exitoso')
def pago_exitoso():
    return "¡Pago exitoso! Gracias por tu compra."

@app.route('/pago-cancelado')
def pago_cancelado():
    return "El pago ha sido cancelado. Puedes volver a intentarlo cuando quieras."


# --- 4. RUTAS DE PÁGINAS PRINCIPALES ---
@app.route("/")
@login_required
def index():
    return render_template("index.html", current_user=current_user)

@app.route("/biblioteca")
def biblioteca_page():
    return render_template("biblioteca.html")

@app.route("/gestion_ingredientes")
@login_required
def gestion_ingredientes_page():
    return render_template("gestion_ingredientes.html")

@app.route("/gestion_bibliografia")
@login_required
def gestion_bibliografia_page():
    return render_template("gestion_bibliografia.html")

@app.route('/cuenta')
@login_required
def cuenta_page():
    credits = database.get_user_credits(current_user.id)
    return render_template('cuenta.html', credits=credits)

# --- 5. RUTAS DE API ---

@app.route("/api/chat", methods=['POST'])
@login_required
def chat_with_ai():
    if not client:
        return jsonify({'answer': 'Error: La API de IA no está configurada.'}), 500

    if database.get_user_credits(current_user.id) <= 0:
        return jsonify({'answer': 'No tienes créditos suficientes. Por favor, recarga para continuar.'}), 402

    data = request.json
    user_question = data.get('question')
    if not user_question:
        return jsonify({'answer': 'No se recibió ninguna pregunta.'}), 400

    # ... (lógica de prompt sin cambios)

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_question}
            ]
        )
        ai_answer = response.choices[0].message.content
        database.decrement_user_credits(current_user.id, 1)
    except Exception as e:
        print(f"ERROR: Error al llamar a la API de OpenAI en el chat: {e}")
        return jsonify({'answer': f'Error al contactar el servicio de IA: {e}'}), 500

    return jsonify({'answer': ai_answer})

@app.route("/api/formula/<int:formula_id>/analyze", methods=['POST'])
@login_required
def analyze_formula_route(formula_id):
    if not client:
        return jsonify({'analysis': 'Error: La API de IA no está configurada.'}), 500

    if database.get_user_credits(current_user.id) <= 0:
        return jsonify({'analysis': 'No tienes créditos suficientes para realizar un análisis. Por favor, recarga.'}), 402

    # ... (lógica de la función sin cambios hasta la llamada a la API)

    try:
        # ... (código de la llamada a la API)
        analysis_text = response.choices[0].message.content
        database.decrement_user_credits(current_user.id, 5) # Descontar 5 créditos por análisis
        return jsonify({'analysis': analysis_text})
    except APIConnectionError as e:
        # ... (manejo de errores)
        return jsonify({'analysis': f'Error al contactar el servicio de IA: {e}'}), 500

# ... (resto del archivo sin cambios)