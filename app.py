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
        return User(
            id=user_data['id'],
            username=user_data['username'],
            full_name=user_data.get('full_name', '')
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
        username = request.form.get('username')   # Correo
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not all([full_name, username, password, confirm_password]):
            flash('Todos los campos son requeridos.')
            return redirect(url_for('register'))
        
        if password != confirm_password:
            flash('Las contraseñas no coinciden.')
            return redirect(url_for('register'))

        if database.get_user_by_username(username):
            flash('Este correo electrónico ya está registrado.')
            return redirect(url_for('register'))
        
        if database.add_user(username, password, full_name):
            flash('¡Cuenta creada con éxito! Ahora puedes iniciar sesión.')
            return redirect(url_for('login'))
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
            user = User(
                id=user_data['id'],
                username=user_data['username'],
                full_name=user_data.get('full_name', '')
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
# (Aquí van todas tus rutas de API que ya tenías, no es necesario copiarlas de nuevo si ya están bien)
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

@app.route("/api/formula/<int:formula_id>/ingredients/add", methods=['POST'])
@login_required
def add_ingredient(formula_id):
    data = request.json
    name, quantity, unit = data.get('name'), data.get('quantity'), data.get('unit')
    database.add_ingredient_to_formula(formula_id, name, float(quantity), unit)
    return get_formula_details(formula_id)

@app.route("/api/ingredient/<int:formula_ingredient_id>/update", methods=['POST'])
@login_required
def update_ingredient_in_formula(formula_ingredient_id):
    parent_formula_id = database.get_formula_id_for_ingredient(formula_ingredient_id)
    data = request.json
    name, quantity, unit = data.get('name'), data.get('quantity'), data.get('unit')
    database.update_ingredient(formula_ingredient_id, name, float(quantity), unit)
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
    return jsonify(database.search_ingredient_names(query))

@app.route("/api/chat", methods=['POST'])
@login_required
def chat_with_ai():
    # ... tu lógica de chat ...
    return jsonify({'answer': 'Respuesta del chat.'})


# --- 6. INICIALIZACIÓN ---
with app.app_context():
    database.initialize_database()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=True)


