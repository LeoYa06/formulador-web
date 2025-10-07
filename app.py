# app.py
import os
import random
import secrets
from datetime import datetime, timedelta
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from flask import session
from flask import Flask, render_template, jsonify, request, flash, redirect, url_for
from werkzeug.security import check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import google.generativeai as genai
from dotenv import load_dotenv

# Importamos nuestras funciones de base de datos y cálculos
import database
import calculations

# --- 1. CONFIGURACIÓN INICIAL ---
load_dotenv()
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'una-clave-secreta-muy-dificil-de-adivinar')

# Configurar la API de Google AI
try:
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    model = genai.GenerativeModel('gemini-2.5pro')
    print("INFO: API de Google AI configurada correctamente.")
except Exception as e:
    print(f"ERROR: No se pudo configurar la API de Google AI. Verifica tu clave de API. Error: {e}")
    model = None

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

# --- 3. RUTAS DE AUTENTICACIÓN ---

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
        
        # --- NUEVA LÓGICA DE VERIFICACIÓN ---
        
        # 1. Generar código y fecha de expiración
        verification_code = str(random.randint(100000, 999999))
        code_expiry = datetime.utcnow() + timedelta(minutes=15)

        # 2. Guardar el usuario como NO VERIFICADO
        if database.add_user(username, password, full_name, verification_code, code_expiry):
            
            # 3. Enviar el correo electrónico con SendGrid
            message = Mail(
                from_email='info@elmefood.com', # Un correo verificado en tu cuenta de SendGrid
                to_emails=username,
                subject='Código de Verificación - Formulador de Embutidos',
                html_content=f'<h3>Hola {full_name},</h3><p>Gracias por registrarte. Tu código de verificación es: <strong>{verification_code}</strong></p><p>Este código es válido por 15 minutos.</p>'
            )
            try:
                sendgrid_client = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
                sendgrid_client.send(message)
            except Exception as e:
                print(f"Error enviando correo: {e}")
                flash('Ocurrió un error al enviar el correo de verificación.')
                return redirect(url_for('register'))

            flash('¡Cuenta creada! Te hemos enviado un código de verificación a tu correo.')
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
                flash('Tu cuenta no está verificada. Por favor, revisa tu correo electrónico.')
                return redirect(url_for('verify', email=username))

            session_token = secrets.token_hex(32)
            database.update_session_token(user_data['id'], session_token)
            session['session_token'] = session_token
            
            user = User(
                id=user_data['id'],
                username=user_data['username'],
                full_name=user_data.get('full_name', ''),
                is_verified=user_data.get('is_verified')
            )
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Login incorrecto. Revisa tu email y contraseña.')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Cierra la sesión del usuario."""
    logout_user()
    flash('Has cerrado sesión exitosamente.')
    return redirect(url_for('login'))


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


# --- 5. RUTAS DE API ---
@app.route("/api/formulas")
@login_required
def get_formulas():
    formulas = database.get_all_formulas(current_user.id)
    return jsonify(formulas)

@app.route("/api/formulas/add", methods=['POST'])
@login_required
def add_new_formula():
    data = request.json
    product_name = data.get('product_name')
    if not product_name:
        return jsonify({'success': False, 'error': 'El nombre del producto es requerido'}), 400
    
    formula_id = database.add_formula(product_name, current_user.id)
    if formula_id:
        new_formula_data = {'id': formula_id, 'product_name': product_name}
        return jsonify({'success': True, 'formula': new_formula_data})
    else:
        return jsonify({'success': False, 'error': 'Ya tienes una fórmula con ese nombre'}), 409

@app.route("/api/formula/<int:formula_id>")
@login_required
def get_formula_details(formula_id):
    formula_data = database.get_formula_by_id(formula_id, current_user.id)
    if not formula_data:
        return jsonify({'success': False, 'error': 'Fórmula no encontrada o sin permiso'}), 404
    
    processed_ingredients = calculations.process_ingredients_for_display(formula_data.get('ingredients', []))
    totals = calculations.calculate_formula_totals(processed_ingredients)
    response_data = {'success': True, 'details': {
        'id': formula_data['id'], 
        'product_name': formula_data['product_name'], 
        'description': formula_data['description'], 
        'ingredients': processed_ingredients, 
        'totals': totals
    }}
    return jsonify(response_data)

@app.route("/api/formulas/<int:formula_id>/delete", methods=['POST'])
@login_required
def delete_formula_route(formula_id):
    success = database.delete_formula(formula_id, current_user.id)
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'No se pudo eliminar la fórmula'}), 403
    
@app.route("/api/formulas/<int:formula_id>/update", methods=['POST'])
@login_required
def update_formula_name(formula_id):
    """Actualiza el nombre de una fórmula."""
    data = request.json
    new_name = data.get('product_name', '').strip()
    
    if not new_name:
        return jsonify({'success': False, 'error': 'El nombre del producto es requerido'}), 400
    
    formula_data = database.get_formula_by_id(formula_id, current_user.id)
    if not formula_data:
        return jsonify({'success': False, 'error': 'Fórmula no encontrada o sin permiso'}), 404
    
    existing_formulas = database.get_all_formulas(current_user.id)
    for formula in existing_formulas:
        if formula['id'] != formula_id and formula['product_name'].lower() == new_name.lower():
            return jsonify({'success': False, 'error': 'Ya tienes una fórmula con ese nombre'}), 409
    
    success = database.update_formula_name(formula_id, new_name, current_user.id)
    
    if success:
        return jsonify({'success': True, 'formula': {'id': formula_id, 'product_name': new_name}})
    else:
        return jsonify({'success': False, 'error': 'No se pudo actualizar la fórmula'}), 500

@app.route("/api/formula/<int:formula_id>/ingredients/add", methods=['POST'])
@login_required
def add_ingredient(formula_id):
    data = request.json
    name, quantity, unit = data.get('name'), data.get('quantity'), data.get('unit')
    # Pasa el user_id a la función de la base de datos
    database.add_ingredient_to_formula(formula_id, name, float(quantity), unit, current_user.id)
    return get_formula_details(formula_id)

@app.route("/api/ingredient/<int:formula_ingredient_id>/update", methods=['POST'])
@login_required
def update_ingredient_in_formula(formula_ingredient_id):
    parent_formula_id = database.get_formula_id_for_ingredient(formula_ingredient_id)
    data = request.json
    name, quantity, unit = data.get('name'), data.get('quantity'), data.get('unit')
    # Pasa el user_id a la función de la base de datos
    database.update_ingredient(formula_ingredient_id, name, float(quantity), unit, current_user.id)
    return get_formula_details(parent_formula_id)

@app.route("/api/ingredient/<int:formula_ingredient_id>/delete", methods=['POST'])
@login_required
def delete_ingredient_from_formula(formula_ingredient_id):
    parent_formula_id = database.get_formula_id_for_ingredient(formula_ingredient_id)
    database.delete_ingredient(formula_ingredient_id)
    return get_formula_details(parent_formula_id)

@app.route("/api/ingredients/search")
@login_required
def search_ingredients():
    query = request.args.get('q', '')
    # Llama a la nueva función y pasa el user_id
    return jsonify(database.search_user_ingredient_names(query, current_user.id))

# --- Rutas para Gestión de Ingredientes de Usuario ---

@app.route("/api/ingredientes")
@login_required
def get_user_ingredients_route():
    """Obtiene todos los ingredientes del usuario actual."""
    ingredients = database.get_user_ingredients(current_user.id)
    return jsonify(ingredients)

@app.route("/api/ingredientes/add", methods=['POST'])
@login_required
def add_user_ingredient_route():
    """Añade un nuevo ingrediente a la colección del usuario."""
    data = request.json
    try:
        database.add_user_ingredient(data, current_user.id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/api/ingredientes/<int:ing_id>/update", methods=['POST'])
@login_required
def update_user_ingredient_route(ing_id):
    """Actualiza un ingrediente en la colección del usuario."""
    data = request.json
    try:
        success = database.update_user_ingredient(ing_id, data, current_user.id)
        if success:
            return jsonify({'success': True})
        else:
            # Podría ser que el ingrediente no exista o no pertenezca al usuario
            return jsonify({'success': False, 'error': 'No se pudo actualizar el ingrediente'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/api/ingredientes/<int:ing_id>/delete", methods=['POST'])
@login_required
def delete_user_ingredient_route(ing_id):
    """Elimina un ingrediente de la colección del usuario."""
    try:
        result = database.delete_user_ingredient(ing_id, current_user.id)
        if result == 'success':
            return jsonify({'success': True})
        elif result == 'in_use':
            return jsonify({'success': False, 'error': 'El ingrediente está en uso en una o más fórmulas y no puede ser eliminado.'}), 409
        else: # not_found
            return jsonify({'success': False, 'error': 'Ingrediente no encontrado.'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# --- Rutas para Gestión de Bibliografía ---

@app.route("/api/bibliografia")
@login_required
def get_bibliografia():
    """Obtiene todas las entradas de la bibliografía."""
    entries = database.get_all_bibliografia()
    return jsonify(entries)

@app.route("/api/bibliografia/add", methods=['POST'])
@login_required
def add_bibliografia():
    """Añade una nueva entrada a la bibliografía."""
    data = request.json
    try:
        entry_id = database.add_bibliografia_entry(data['titulo'], data['tipo'], data['contenido'])
        if entry_id:
            return jsonify({'success': True, 'id': entry_id})
        else:
            return jsonify({'success': False, 'error': 'No se pudo crear la entrada'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/api/bibliografia/<int:entry_id>/update", methods=['POST'])
@login_required
def update_bibliografia(entry_id):
    """Actualiza una entrada de la bibliografía."""
    data = request.json
    try:
        success = database.update_bibliografia_entry(entry_id, data['titulo'], data['tipo'], data['contenido'])
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'No se pudo actualizar la entrada'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/api/bibliografia/<int:entry_id>/delete", methods=['POST'])
@login_required
def delete_bibliografia(entry_id):
    """Elimina una entrada de la bibliografía."""
    try:
        success = database.delete_bibliografia_entry(entry_id)
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'No se pudo eliminar la entrada'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route("/api/chat", methods=['POST'])
@login_required
def chat_with_ai():
    """
    Maneja las conversaciones del chatbot con la IA generativa, usando la bibliografía como contexto.
    """
    if not model:
        return jsonify({'answer': 'Error: La API de IA no está configurada.'}), 500

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

    prompt = f'''
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

    **Pregunta del usuario:** "{user_question}"
    '''

    try:
        response = model.generate_content(prompt)
        ai_answer = response.text
    except Exception as e:
        print(f"ERROR: Error al llamar a la API de Google en el chat: {e}")
        return jsonify({'answer': f'Error al contactar el servicio de IA: {e}'}), 500

    return jsonify({'answer': ai_answer})

@app.route('/verify', methods=['GET', 'POST'])
def verify():
    """Maneja la verificación del código enviado por correo."""
    email = request.args.get('email')
    if not email:
        return redirect(url_for('register'))

    if request.method == 'POST':
        code = request.form.get('verification_code')
        user = database.get_user_by_username(email)

        if not user:
            flash('Usuario no encontrado.')
            return redirect(url_for('register'))
        
        if user['is_verified']:
            flash('Tu cuenta ya ha sido verificada. Por favor, inicia sesión.')
            return redirect(url_for('login'))
        
        if user.get('code_expiry') and datetime.utcnow() > user['code_expiry']:
            flash('Tu código de verificación ha expirado. Por favor, solicita uno nuevo.')
            return redirect(url_for('verify', email=email))

        if user['verification_code'] == code:
            database.verify_user(email)
            
            # Sembrar ingredientes iniciales para el usuario verificado
            verified_user = database.get_user_by_username(email)
            if verified_user:
                database.seed_initial_ingredients(verified_user['id'])

            flash('¡Verificación exitosa! Ahora puedes iniciar sesión.')
            return redirect(url_for('login'))
        else:
            flash('El código de verificación es incorrecto. Inténtalo de nuevo.')

    return render_template('verify.html', email=email)

@app.route("/api/formula/<int:formula_id>/analyze", methods=['POST'])
@login_required
def analyze_formula_route(formula_id):
    """
    Analiza una fórmula utilizando la IA generativa.
    """
    if not model:
        return jsonify({'analysis': 'Error: La API de IA no está configurada.'}), 500

    formula_data = database.get_formula_by_id(formula_id, current_user.id)
    if not formula_data:
        return jsonify({'success': False, 'error': 'Fórmula no encontrada o sin permiso'}), 404

    processed_ingredients = calculations.process_ingredients_for_display(formula_data.get('ingredients', []))
    totals = calculations.calculate_formula_totals(processed_ingredients)

    prompt = f'''
    Eres un experto en tecnología de alimentos y formulación de productos.
    Analiza la siguiente fórmula y proporciona una evaluación y recomendaciones.

    **Nombre del Producto:** {formula_data['product_name']}

    **Ingredientes:**
    '''
    for ing in processed_ingredients:
        prompt += f"- {ing['ingredient_name']}: {ing['original_qty_display']} {ing['original_unit']} ({ing['percentage']:.2f}%)\n"

    prompt += f'''
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

    Proporciona una respuesta concisa y fácil de entender en formato Markdown.
    '''

    try:
        response = model.generate_content(prompt)
        analysis_text = response.text
    except Exception as e:
        print(f"ERROR: Error al llamar a la API de Google: {e}")
        return jsonify({'analysis': f'Error al contactar el servicio de IA: {e}'}), 500

    return jsonify({'analysis': analysis_text})

@app.route('/terms')
def terms():
    return render_template('terms.html')

# --- 6. INICIALIZACIÓN ---

with app.app_context():
    database.initialize_database()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=True)

@app.before_request
def check_session():
    if current_user.is_authenticated:
        browser_session_token = session.get('session_token')
        db_session_token = database.get_session_token_for_user(current_user.id)

        if browser_session_token != db_session_token:
            logout_user()
            flash("Has iniciado sesión en otro dispositivo. Esta sesión ha sido cerrada.")
            return redirect(url_for('login'))
