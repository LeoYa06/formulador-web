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
from flask_wtf.csrf import CSRFProtect
from openai import OpenAI, APIConnectionError
from dotenv import load_dotenv

# Importamos nuestras funciones de base de datos y cálculos
import database
import calculations

# --- 1. CONFIGURACIÓN INICIAL ---
load_dotenv()
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'una-clave-secreta-muy-dificil-de-adivinar')
csrf = CSRFProtect(app)

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
            success_url=url_for('pago_exitoso', _external=True),
            cancel_url=url_for('pago_cancelado', _external=True),
            client_reference_id=current_user.id
        )
        return jsonify({'url': checkout_session.url})
    except Exception as e:
        return jsonify(error=str(e)), 500

@app.route('/webhook', methods=['POST'])
@csrf.exempt
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

@app.route('/terms')
def terms():
    """Muestra la página de términos y condiciones."""
    return render_template('terms.html')

# --- 5. RUTAS DE API ---

@app.route('/api/formulas', methods=['GET'])
@login_required
def get_formulas():
    formulas = database.get_all_formulas(current_user.id)
    return jsonify(formulas)

@app.route('/api/formulas/add', methods=['POST'])
@login_required
def add_formula_route():
    data = request.get_json()
    product_name = data.get('product_name')
    description = data.get('description', '')
    if not product_name:
        return jsonify({'success': False, 'error': 'El nombre del producto es requerido.'}), 400
    
    formula_id = database.add_formula(product_name, current_user.id, description)
    
    if formula_id:
        return jsonify({'success': True, 'formula_id': formula_id})
    else:
        return jsonify({'success': False, 'error': 'Ya existe una fórmula con este nombre.'}), 409

@app.route('/api/formulas/<int:formula_id>/delete', methods=['POST'])
@login_required
def delete_formula_route(formula_id):
    success = database.delete_formula(formula_id, current_user.id)
    return jsonify({'success': success})

@app.route('/api/formulas/<int:formula_id>/update', methods=['POST'])
@login_required
def update_formula_route(formula_id):
    data = request.get_json()
    new_name = data.get('product_name')
    if not new_name:
        return jsonify({'success': False, 'error': 'El nombre del producto es requerido.'}), 400
    
    success = database.update_formula_name(formula_id, new_name, current_user.id)
    
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'No se pudo actualizar la fórmula.'}), 500

@app.route('/api/formula/<int:formula_id>', methods=['GET'])
@login_required
def get_formula_details(formula_id):
    formula_data = database.get_formula_by_id(formula_id, current_user.id)
    if not formula_data:
        return jsonify({"error": "Fórmula no encontrada"}), 404

    processed_ingredients = calculations.process_ingredients_for_display(formula_data.get('ingredients', []))
    totals = calculations.calculate_formula_totals(processed_ingredients)

    # Combinar los datos para la respuesta
    details = {
        **formula_data,
        'ingredients': processed_ingredients,
        'totals': totals
    }

    return jsonify({"details": details})

@app.route('/api/formula/<int:formula_id>/ingredients/add', methods=['POST'])
@login_required
def add_ingredient_to_formula_route(formula_id):
    # Primero, verificar que la fórmula pertenece al usuario actual
    formula_data = database.get_formula_by_id(formula_id, current_user.id)
    if not formula_data:
        return jsonify({'success': False, 'error': 'Fórmula no encontrada o sin permiso.'}), 404

    data = request.get_json()
    ingredient_name = data.get('name')
    quantity = data.get('quantity')
    unit = data.get('unit')

    if not all([ingredient_name, quantity, unit]):
        return jsonify({'success': False, 'error': 'Faltan datos del ingrediente.'}), 400

    # La función de base de datos se encarga de la lógica de añadir
    database.add_ingredient_to_formula(formula_id, ingredient_name, float(quantity), unit, current_user.id)

    # Después de añadir, obtenemos y devolvemos el estado actualizado de la fórmula
    updated_formula_data = database.get_formula_by_id(formula_id, current_user.id)
    processed_ingredients = calculations.process_ingredients_for_display(updated_formula_data.get('ingredients', []))
    totals = calculations.calculate_formula_totals(processed_ingredients)
    
    response_data = {
        'success': True,
        'details': {
            **updated_formula_data,
            'ingredients': processed_ingredients,
            'totals': totals
        }
    }
    return jsonify(response_data)

@app.route('/api/ingredient/<int:formula_ingredient_id>/delete', methods=['POST'])
@login_required
def delete_ingredient_route(formula_ingredient_id):
    formula_id = database.get_formula_id_for_ingredient(formula_ingredient_id)
    if not formula_id:
        return jsonify({'success': False, 'error': 'Ingrediente no encontrado.'}), 404

    # Verificar que la fórmula pertenece al usuario antes de borrar
    if not database.get_formula_by_id(formula_id, current_user.id):
        return jsonify({'success': False, 'error': 'No tienes permiso para esta acción.'}), 403

    database.delete_ingredient(formula_ingredient_id)
    
    return get_formula_details(formula_id) # Reutilizamos la función para devolver la fórmula actualizada

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

    bibliografia_entries = database.get_all_bibliografia()
    contexto_bibliografico = "\n\n".join([
        f"**Título:** {entry['titulo']}\n"
        f"**Tipo:** {entry['tipo']}\n"
        f"**Contenido:** {entry['contenido']}"
        for entry in bibliografia_entries
    ])

    system_prompt = f"""
Eres un asistente experto en tecnología de alimentos y formulación de productos. Tu tarea es responder a las preguntas del usuario de la forma más completa y actualizada posible.

Para ello, debes combinar información de tres fuentes:
1.  **La Bibliografía Interna:** Este es tu principal punto de partida. Úsala para obtener información de base y contexto específico de la empresa.
2.  **Tu Conocimiento General como IA:** Complementa la información de la bibliografía con tu conocimiento profundo sobre el tema.
3.  **Simulación de Búsqueda Web:** Imagina que has realizado una búsqueda en tiempo real en Google sobre el tema. Incorpora en tu respuesta las últimas tendencias, investigaciones o noticias que encontrarías.

**Proceso de Respuesta:**
- Comienza con la información de la bibliografía si es relevante.
- Enriquece la respuesta con tu conocimiento general.
- Finaliza añadiendo los hallazgos más recientes que una búsqueda web proporcionaría, indicando que son "tendencias recientes" o "información actualizada".

--- INICIO DE LA BIBLIOGRAFÍA ---
{contexto_bibliografico}
--- FIN DE LA BIBLIOGRAFÍA ---
"""

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

    if database.get_user_credits(current_user.id) <= 5:
        return jsonify({'analysis': 'No tienes créditos suficientes (se requieren 5) para realizar un análisis. Por favor, recarga.'}), 402

    formula_data = database.get_formula_by_id(formula_id, current_user.id)
    if not formula_data:
        return jsonify({'success': False, 'error': 'Fórmula no encontrada o sin permiso'}), 404

    processed_ingredients = calculations.process_ingredients_for_display(formula_data.get('ingredients', []))
    totals = calculations.calculate_formula_totals(processed_ingredients)

    system_prompt = "Eres un experto en tecnología de alimentos y formulación de productos. Analiza la siguiente fórmula y proporciona una evaluación y recomendaciones concisas y fáciles de entender en formato Markdown."

    user_prompt = f"**Nombre del Producto:** {formula_data['product_name']}\n\n"
    user_prompt += "**Ingredientes:**\n"
    for ing in processed_ingredients:
        user_prompt += f"- {ing['ingredient_name']}: {ing['original_qty_display']} {ing['original_unit']} ({ing['percentage']:.2f}%)\n"

    user_prompt += f'''
    **Resultados del Cálculo:**
    - Peso Total: {totals.get('total_kg', 0):.3f} kg
    - Costo Total: {totals.get('costo_total', 0):.2f}
    - Costo por Kg: {totals.get('costo_por_kg', 0):.2f}
    - % Proteína: {totals.get('protein_perc', 0):.2f}%
    - % Grasa: {totals.get('fat_perc', 0):.2f}%
    - % Humedad Total: {totals.get('water_perc', 0):.2f}%
    - Ratio Agua/Proteína: {totals.get('aw_fp_ratio_str', 'N/A')}
    - Ratio Grasa/Proteína: {totals.get('af_fp_ratio_str', 'N/A')}

**Análisis Solicitado:**
1.  **Evaluación General:** ¿Qué tipo de producto es? ¿La fórmula parece balanceada para su propósito?
2.  **Puntos Fuertes:** ¿Cuáles son los aspectos positivos de esta formulación? (ej. buen perfil nutricional, bajo costo, etc.)
3.  **Posibles Mejoras:** ¿Qué cambios sugerirías? (ej. ajustar un ingrediente para mejorar la textura, reducir costos, mejorar el perfil nutricional).
4.  **Riesgos Potenciales:** ¿Hay algún riesgo a considerar? (ej. problemas de estabilidad, alérgenos comunes, vida útil).
'''

    print(f"INFO: Tamaño del user_prompt: {len(user_prompt)} caracteres")

    retries = 3
    for attempt in range(retries):
        try:
            print(f"INFO: Intento {attempt + 1}/{retries} de solicitud a OpenAI para formula_id: {formula_id}")
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            print(f"INFO: Solicitud a OpenAI exitosa para formula_id: {formula_id}")
            analysis_text = response.choices[0].message.content
            database.decrement_user_credits(current_user.id, 5)
            return jsonify({'analysis': analysis_text})
        except APIConnectionError as e:
            print(f"ERROR: Intento {attempt + 1}/{retries} fallido: {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            else:
                print(f"ERROR TYPE: {type(e)}")
                print(f"ERROR ARGS: {e.args}")
                print(f"ERROR: Error al llamar a la API de OpenAI: {e}")
                return jsonify({'analysis': f'Error al contactar el servicio de IA: {e}'}), 500

# ... (resto del archivo sin cambios)