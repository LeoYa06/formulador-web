# app.py
import os
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
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
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
    def __init__(self, id, username, full_name):
        self.id = id
        self.username = username
        self.full_name = full_name

@login_manager.user_loader
def load_user(user_id):
    user_data = database.get_user_by_id(int(user_id))
    if user_data:
        return User(id=user_data['id'], username=user_data['username'], full_name=user_data['full_name'])
    return None

# --- 3. FUNCIONES AUXILIARES (DE TU CÓDIGO ORIGINAL) ---
def _clasificar_ingrediente_con_ia(nombre_ingrediente: str) -> str:
    if not model: return "Retenedor/No Cárnico"
    # ... (Lógica de IA sin cambios)
    return "Retenedor/No Cárnico" # Placeholder, tu lógica original va aquí

# --- 4. RUTAS DE AUTENTICACIÓN ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated: return redirect(url_for('index'))
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not all([full_name, username, password, confirm_password]):
            flash('Todos los campos son requeridos.')
            return redirect(url_for('register'))
        
        if password != confirm_password:
            flash('Las contraseñas no coinciden.')
            return redirect(url_for('register')) 
               
        if not username or not password or not full_name:
            flash('El nombre, usuario y la contraseña son requeridos.')
            return redirect(url_for('register'))
        
        if database.get_user_by_username(username):
            flash('El nombre de usuario ya existe. Por favor, elige otro.')
            return redirect(url_for('register'))
        
        if database.add_user(username, password, full_name):
            flash('¡Cuenta creada con éxito! Ahora puedes iniciar sesión.')
            return redirect(url_for('login'))
        else:
            flash('Ocurrió un error al crear la cuenta.')

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user_data = database.get_user_by_username(username)
        if user_data and check_password_hash(user_data['password_hash'], password):
            user = User(id=user_data['id'], username=user_data['username'])
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Nombre de usuario o contraseña incorrectos.')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión exitosamente.')
    return redirect(url_for('login'))

# --- 5. RUTAS DE PÁGINAS ---
@app.route("/")
@login_required
def index():
    return render_template("index.html")

@app.route("/biblioteca")
def biblioteca_page():
    # Esta página es pública, no requiere login
    return render_template("biblioteca.html")

@app.route("/gestion_ingredientes")
@login_required # Protegida
def gestion_ingredientes_page():
    return render_template("gestion_ingredientes.html")

@app.route("/gestion_bibliografia")
@login_required # Protegida
def gestion_bibliografia_page():
    return render_template("gestion_bibliografia.html")

# --- 6. RUTAS DE API (FUSIONADAS Y PROTEGIDAS) ---

# --- API para Fórmulas ---
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
    response_data = {'success': True, 'details': {'id': formula_data['id'], 'product_name': formula_data['product_name'], 'description': formula_data['description'], 'ingredients': processed_ingredients, 'totals': totals}}
    return jsonify(response_data)

@app.route("/api/formula/<int:formula_id>/rename", methods=['POST'])
@login_required
def rename_formula(formula_id):
    data = request.json
    new_name = data.get('new_name')
    if not new_name:
        return jsonify({'success': False, 'error': 'El nuevo nombre es requerido'}), 400
    success = database.update_formula_name(formula_id, new_name, current_user.id)
    if success:
        return jsonify({'success': True, 'new_name': new_name})
    else:
        return jsonify({'success': False, 'error': 'No se pudo renombrar (¿nombre duplicado?)'}), 409

@app.route("/api/formulas/<int:formula_id>/delete", methods=['POST'])
@login_required
def delete_formula_route(formula_id):
    success = database.delete_formula(formula_id, current_user.id)
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'No se pudo eliminar la fórmula'}), 403

# --- API para Ingredientes DENTRO de una Fórmula ---
@app.route("/api/formula/<int:formula_id>/ingredients/add", methods=['POST'])
@login_required
def add_ingredient(formula_id):
    # (Tu lógica original aquí, ya es segura porque la fórmula se carga con user_id)
    data = request.json
    name, quantity, unit = data.get('name'), data.get('quantity'), data.get('unit')
    database.add_ingredient_to_formula(formula_id, name, float(quantity), unit)
    return get_formula_details(formula_id)

@app.route("/api/ingredient/<int:formula_ingredient_id>/update", methods=['POST'])
@login_required
def update_ingredient_in_formula(formula_ingredient_id):
    # (Tu lógica original aquí)
    parent_formula_id = database.get_formula_id_for_ingredient(formula_ingredient_id)
    data = request.json
    name, quantity, unit = data.get('name'), data.get('quantity'), data.get('unit')
    database.update_ingredient(formula_ingredient_id, name, float(quantity), unit)
    return get_formula_details(parent_formula_id)

@app.route("/api/ingredient/<int:formula_ingredient_id>/delete", methods=['POST'])
@login_required
def delete_ingredient_from_formula(formula_ingredient_id):
    # (Tu lógica original aquí)
    parent_formula_id = database.get_formula_id_for_ingredient(formula_ingredient_id)
    database.delete_ingredient(formula_ingredient_id)
    return get_formula_details(parent_formula_id)

# --- API para Análisis con IA ---
@app.route("/api/formula/<int:formula_id>/analyze", methods=['POST'])
@login_required
def analyze_formula_with_ai(formula_id):
    # (Tu lógica original aquí, ya es segura)
    if not model: return jsonify({'analysis': 'El servicio de IA no está configurado.'}), 500
    formula_data = database.get_formula_by_id(formula_id, current_user.id)
    if not formula_data: return jsonify({'success': False, 'error': 'Fórmula no encontrada'}), 404
    # ... resto de tu lógica de IA
    return jsonify({'analysis': 'Análisis completado.'}) # Placeholder

# --- API para Gestión de Ingredientes MAESTROS ---
@app.route("/api/ingredientes")
@login_required
def get_all_master_ingredients():
    return jsonify(database.get_all_ingredients_with_details())

@app.route("/api/ingredientes/add", methods=['POST'])
@login_required
def add_new_master_ingredient():
    # (Tu lógica original aquí)
    data = request.json
    new_id = database.add_master_ingredient(data)
    if new_id:
        data['id'] = new_id
        return jsonify({'success': True, 'ingredient': data})
    return jsonify({'success': False, 'error': 'No se pudo añadir'}), 500

# ... (Resto de tus rutas de API para ingredientes, bibliografía y chat)
# ... (Asegúrate de que todas las que modifican datos estén protegidas)

# --- API para Bibliografía (Gestión protegida, vista pública) ---
@app.route("/api/bibliografia")
def get_bibliografia_entries():
    # Cualquiera puede ver la bibliografía
    return jsonify(database.get_all_bibliografia())

@app.route("/api/bibliografia/add", methods=['POST'])
@login_required # Pero solo usuarios logueados pueden añadir
def add_new_bibliografia_entry():
    # (Tu lógica original aquí)
    data = request.json
    new_id = database.add_bibliografia_entry(data['titulo'], data.get('tipo'), data['contenido'])
    if new_id:
        data['id'] = new_id
        return jsonify({'success': True, 'entry': data})
    return jsonify({'success': False, 'error': 'No se pudo añadir'}), 500

# ... (añade aquí tus otras rutas de API de bibliografía para update/delete con @login_required)

# --- API para Chatbot ---
@app.route("/api/chat", methods=['POST'])
@login_required # Protegemos el chat por si acaso usa contexto de usuario en el futuro
def chat_with_ai():
    # (Tu lógica original aquí)
    data = request.json
    user_question = data.get('question')
    if not user_question: return jsonify({'answer': 'Por favor, escribe una pregunta.'})
    # ... resto de tu lógica de chat con IA
    return jsonify({'answer': 'Respuesta del chat.'}) # Placeholder


# --- 7. INICIALIZACIÓN ---
# Esta línea se ejecutará cuando Gunicorn cargue la aplicación, creando las tablas.
with app.app_context():
    database.initialize_database()

if __name__ == '__main__':
    # Esto solo se usará si ejecutas el archivo directamente en tu computadora.
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=True)


