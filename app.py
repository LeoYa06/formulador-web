# app.py
import os
from flask import Flask, render_template, jsonify, request
import google.generativeai as genai
from dotenv import load_dotenv
import database
import calculations
import gunicorn

# --- Configuración Inicial ---
load_dotenv()
app = Flask(__name__)

# Configurar la API de Google AI
try:
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
except Exception as e:
    print(f"ERROR: No se pudo configurar la API de Google AI. Verifica tu clave de API. Error: {e}")
    model = None

# --- Funciones Auxiliares ---
def _clasificar_ingrediente_con_ia(nombre_ingrediente: str) -> str:
    if not model: return "Retenedor/No Cárnico"
    print(f"INFO: Clasificando ingrediente '{nombre_ingrediente}' con IA...")
    categorias_posibles = "Cárnico, Agua/Hielo, Retenedor/No Cárnico, Condimento/Aditivo, Colorante"
    context_results = database.search_bibliografia(nombre_ingrediente, limit=1)
    contexto = ""
    if context_results:
        contexto = "Basado en el siguiente contexto de mi biblioteca:\n"
        contexto += f"'{context_results[0]['contenido']}'\n\n"
    prompt = f"""{contexto}Clasifica el ingrediente alimentario '{nombre_ingrediente}' en una de las siguientes categorías: {categorias_posibles}. Responde únicamente con el nombre exacto de la categoría y nada más."""
    try:
        response = model.generate_content(prompt)
        categoria_limpia = response.text.strip().replace('.', '')
        if categoria_limpia in categorias_posibles:
            print(f"INFO: IA clasificó '{nombre_ingrediente}' como '{categoria_limpia}'.")
            return categoria_limpia
        else:
            return "Retenedor/No Cárnico"
    except Exception as e:
        print(f"ERROR: Fallo en la clasificación por IA: {e}")
        return "Retenedor/No Cárnico"

# --- Rutas de Páginas ---
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/biblioteca")
def biblioteca_page():
    return render_template("biblioteca.html")

@app.route("/gestion_ingredientes")
def gestion_ingredientes_page():
    return render_template("gestion_ingredientes.html")

@app.route("/gestion_bibliografia")
def gestion_bibliografia_page():
    return render_template("gestion_bibliografia.html")

# --- Rutas de API para el Formulador ---
@app.route("/api/formulas")
def get_formulas():
    """Obtiene la lista de todas las fórmulas."""
    formulas = database.get_all_formulas()
    return jsonify(formulas)

@app.route("/api/formulas/add", methods=['POST'])
def add_new_formula():
    """Añade una nueva fórmula a la base de datos."""
    data = request.json
    product_name = data.get('product_name')
    if not product_name:
        return jsonify({'success': False, 'error': 'El nombre del producto es requerido'}), 400
    
    formula_id = database.add_formula(product_name)
    if formula_id:
        new_formula_data = {'id': formula_id, 'product_name': product_name}
        return jsonify({'success': True, 'formula': new_formula_data})
    else:
        return jsonify({'success': False, 'error': 'No se pudo añadir la fórmula (¿nombre duplicado?)'}), 500

@app.route("/api/formula/<int:formula_id>")
def get_formula_details(formula_id):
    formula_data = database.get_formula_by_id(formula_id)
    if not formula_data:
        return jsonify({'success': False, 'error': 'Fórmula no encontrada'}), 404
    processed_ingredients = calculations.process_ingredients_for_display(formula_data.get('ingredients', []))
    totals = calculations.calculate_formula_totals(processed_ingredients)
    response_data = {'success': True, 'details': {'id': formula_data['id'], 'product_name': formula_data['product_name'], 'description': formula_data['description'], 'ingredients': processed_ingredients, 'totals': totals}}
    return jsonify(response_data)

@app.route("/api/formula/<int:formula_id>/ingredients/add", methods=['POST'])
def add_ingredient(formula_id):
    data = request.json
    name, quantity, unit = data.get('name'), data.get('quantity'), data.get('unit')
    try:
        quantity_float = float(quantity)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': 'La cantidad debe ser un número válido'}), 400
    if not all([name, unit]):
        return jsonify({'success': False, 'error': 'Todos los campos son requeridos'}), 400
    database.add_ingredient_to_formula(formula_id, name, quantity_float, unit)
    return get_formula_details(formula_id)

@app.route("/api/ingredient/<int:formula_ingredient_id>/update", methods=['POST'])
def update_ingredient_in_formula(formula_ingredient_id):
    parent_formula_id = database.get_formula_id_for_ingredient(formula_ingredient_id)
    if not parent_formula_id: return jsonify({'success': False, 'error': 'El ingrediente no existe'}), 404
    data = request.json
    name, quantity, unit = data.get('name'), data.get('quantity'), data.get('unit')
    try:
        quantity_float = float(quantity)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': 'La cantidad debe ser un número válido'}), 400
    database.update_ingredient(formula_ingredient_id, name, quantity_float, unit)
    return get_formula_details(parent_formula_id)

@app.route("/api/ingredient/<int:formula_ingredient_id>/delete", methods=['POST'])
def delete_ingredient_from_formula(formula_ingredient_id):
    parent_formula_id = database.get_formula_id_for_ingredient(formula_ingredient_id)
    if not parent_formula_id: return jsonify({'success': False, 'error': 'El ingrediente no existe'}), 404
    database.delete_ingredient(formula_ingredient_id)
    return get_formula_details(parent_formula_id)

@app.route("/api/formula/<int:formula_id>/analyze", methods=['POST'])
def analyze_formula_with_ai(formula_id):
    if not model:
        return jsonify({'analysis': 'El servicio de IA no está configurado.'}), 500
    formula_data = database.get_formula_by_id(formula_id)
    if not formula_data:
        return jsonify({'success': False, 'error': 'Fórmula no encontrada'}), 404
    processed_ingredients = calculations.process_ingredients_for_display(formula_data.get('ingredients', []))
    totals = calculations.calculate_formula_totals(processed_ingredients)
    formula_str = f"Producto: {formula_data.get('product_name', 'N/A')}\nIngredientes:\n"
    for ing in processed_ingredients:
        formula_str += f"- {ing['name']}: {ing['kg_total']:.3f} kg\n"
    results_str = (f"Resultados:\n- Peso Total: {totals.get('total_kg', 0):.3f} kg\n- Costo/Kg: ${totals.get('costo_por_kg', 0):.2f}\n- % Proteína: {totals.get('protein_perc', 0):.2f}%\n- % Grasa: {totals.get('fat_perc', 0):.2f}%\n- % Humedad: {totals.get('water_perc', 0):.2f}%\n- Ratio Agua/Proteína: {totals.get('aw_fp_ratio_str', 'N/A')}\n")
    context_results = database.search_bibliografia(formula_data.get('product_name', ''), limit=2)
    contexto = ""
    if context_results:
        contexto += "--- CONTEXTO DE LA BIBLIOTECA ---\n"
        for entry in context_results:
            contexto += f"Título: {entry['titulo']}\nContenido: {entry['contenido']}\n\n"
    prompt = f"""Eres un tecnólogo de alimentos experto. Analiza la siguiente formulación y proporciona un informe conciso en Markdown:\n\n**Formulación:**\n{formula_str}\n**Resultados:**\n{results_str}\n**Contexto:**\n{contexto}\n\n**Tu Tarea:** Proporciona un análisis, puntos fuertes y sugerencias de mejora."""
    try:
        response = model.generate_content(prompt)
        return jsonify({'analysis': response.text})
    except Exception as e:
        print(f"Error en la API de IA para análisis: {e}")
        return jsonify({'analysis': 'Hubo un error al generar el análisis.'}), 500
    
@app.route("/api/formulas/<int:formula_id>/delete", methods=['POST'])
def delete_formula_route(formula_id):
    """Maneja la solicitud para eliminar una fórmula."""
    success = database.delete_formula(formula_id)
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'No se pudo eliminar la fórmula'}), 500

@app.route("/api/formula/<int:formula_id>/rename", methods=['POST'])
def rename_formula(formula_id):
    """Renames a formula."""
    data = request.json
    new_name = data.get('new_name')
    if not new_name:
        return jsonify({'success': False, 'error': 'El nuevo nombre es requerido'}), 400

    success = database.update_formula_name(formula_id, new_name)
    if success:
        return jsonify({'success': True, 'new_name': new_name})
    else:
        return jsonify({'success': False, 'error': 'No se pudo renombrar la fórmula (¿nombre duplicado?)'}), 500

# --- Rutas de API para Gestión de Ingredientes ---
@app.route("/api/ingredientes")
def get_all_master_ingredients():
    return jsonify(database.get_all_ingredients_with_details())

@app.route("/api/ingredientes/add", methods=['POST'])
def add_new_master_ingredient():
    data = request.json
    if not data.get('name'): return jsonify({'success': False, 'error': 'El nombre es requerido'}), 400
    categoria_ia = _clasificar_ingrediente_con_ia(data['name'])
    data['categoria'] = categoria_ia
    new_id = database.add_master_ingredient(data)
    if new_id:
        data['id'] = new_id
        return jsonify({'success': True, 'ingredient': data})
    else:
        return jsonify({'success': False, 'error': 'No se pudo añadir (¿nombre duplicado?)'}), 500

@app.route("/api/ingredientes/<int:ingredient_id>/update", methods=['POST'])
def update_master_ingredient_route(ingredient_id):
    data = request.json
    if not data.get('name'): return jsonify({'success': False, 'error': 'El nombre es requerido'}), 400
    categoria_ia = _clasificar_ingrediente_con_ia(data['name'])
    data['categoria'] = categoria_ia
    success = database.update_master_ingredient(ingredient_id, data)
    if success:
        data['id'] = ingredient_id
        return jsonify({'success': True, 'ingredient': data})
    else:
        return jsonify({'success': False, 'error': 'No se pudo actualizar'}), 500

@app.route("/api/ingredientes/<int:ingredient_id>/delete", methods=['POST'])
def delete_master_ingredient_route(ingredient_id):
    result_status = database.delete_master_ingredient(ingredient_id)
    if result_status == 'success': return jsonify({'success': True})
    elif result_status == 'in_use': return jsonify({'success': False, 'error': 'No se puede eliminar. Ingrediente en uso.'}), 409
    else: return jsonify({'success': False, 'error': 'No se pudo eliminar (no encontrado o error).'}), 500

@app.route("/api/ingredients/search")
def search_ingredients():
    query = request.args.get('q', '')
    return jsonify(database.search_ingredient_names(query))

# --- Rutas de API para Bibliografía ---
@app.route("/api/bibliografia")
def get_bibliografia_entries():
    return jsonify(database.get_all_bibliografia())

@app.route("/api/bibliografia/add", methods=['POST'])
def add_new_bibliografia_entry():
    data = request.json
    if not all([data.get('titulo'), data.get('contenido')]): return jsonify({'success': False, 'error': 'Título y contenido requeridos'}), 400
    new_id = database.add_bibliografia_entry(data['titulo'], data['tipo'], data['contenido'])
    if new_id:
        data['id'] = new_id
        return jsonify({'success': True, 'entry': data})
    else:
        return jsonify({'success': False, 'error': 'No se pudo añadir la entrada'}), 500

@app.route("/api/bibliografia/<int:entry_id>/update", methods=['POST'])
def update_bibliografia_entry_route(entry_id):
    data = request.json
    if not all([data.get('titulo'), data.get('contenido')]): return jsonify({'success': False, 'error': 'Título y contenido requeridos'}), 400
    success = database.update_bibliografia_entry(entry_id, data['titulo'], data['tipo'], data['contenido'])
    if success:
        data['id'] = entry_id
        return jsonify({'success': True, 'entry': data})
    else:
        return jsonify({'success': False, 'error': 'No se pudo actualizar'}), 500

@app.route("/api/bibliografia/<int:entry_id>/delete", methods=['POST'])
def delete_bibliografia_entry_route(entry_id):
    success = database.delete_bibliografia_entry(entry_id)
    if success: return jsonify({'success': True})
    else: return jsonify({'success': False, 'error': 'No se pudo eliminar'}), 500

# --- Ruta de API para el Chatbot ---
@app.route("/api/chat", methods=['POST'])
def chat_with_ai():
    data = request.json
    user_question = data.get('question')
    if not user_question: return jsonify({'answer': 'Por favor, escribe una pregunta.'})
    try:
        context_results = database.search_bibliografia(user_question)
        contexto = ""
        if context_results:
            contexto += "--- CONTEXTO DE LA BIBLIOTECA ---\n"
            for entry in context_results:
                contexto += f"Título: {entry['titulo']}\nContenido: {entry['contenido']}\n\n"
        prompt = f"""Eres un asistente experto en tecnología de alimentos y formulación de embutidos. Basándote principalmente en el siguiente CONTEXTO, responde a la PREGUNTA del usuario. Si el contexto no es suficiente, puedes usar tu conocimiento general.\n\n{contexto}\n\n--- PREGUNTA DEL USUARIO ---\n{user_question}"""
        response = model.generate_content(prompt)
        return jsonify({'answer': response.text})
    except Exception as e:
        print(f"Error en la API de IA: {e}")
        return jsonify({'answer': 'Lo siento, no puedo responder en este momento.'}), 500

# --- Inicialización para Render ---
with app.app_context():
    database.initialize_database()




