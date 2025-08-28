# db/database.py
import os
import psycopg2
import psycopg2.extras
import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# --- Configuración para PostgreSQL ---
DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    """Establece conexión con la base de datos PostgreSQL."""
    conn = psycopg2.connect(DATABASE_URL)
    return conn

# --- Inicialización de la Base de Datos ---
def initialize_database():
    """Crea o actualiza las tablas necesarias en PostgreSQL."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Crear tabla de usuarios
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL UNIQUE, /* Correo electrónico */
            password_hash TEXT NOT NULL,
            full_name TEXT 
        );
    ''') 
   
    # Añadir la columna 'full_name' si no existe (para bases de datos antiguas)
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN full_name TEXT;')
        conn.commit()
        print("Columna 'full_name' añadida a la tabla 'users'.")
    except psycopg2.errors.DuplicateColumn:
        conn.rollback()
        print("INFO: La columna 'full_name' ya existía.")
        pass
   
    # 2. Crear tabla de fórmulas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS formulas (
            id SERIAL PRIMARY KEY,
            product_name TEXT NOT NULL,
            description TEXT,
            creation_date TEXT NOT NULL
        );
    ''')
    conn.commit() # Hacemos commit aquí para separar las transacciones

    # --- MODIFICACIONES A LA TABLA formulas (con manejo de errores individual) ---

    # 3. Añadir la columna user_id a formulas si no existe
    try:
        cursor.execute('ALTER TABLE formulas ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE;')
        conn.commit() # Commit después de un cambio exitoso
        print("Columna 'user_id' añadida a la tabla 'formulas'.")
    except psycopg2.errors.DuplicateColumn:
        conn.rollback() # Revierte la transacción fallida
        print("INFO: La columna 'user_id' ya existía.")
        pass

    # 4. Eliminar la antigua restricción UNIQUE de product_name si existe
    try:
        # El nombre de la restricción puede variar, 'formulas_product_name_key' es el default
        cursor.execute('ALTER TABLE formulas DROP CONSTRAINT formulas_product_name_key;')
        conn.commit()
        print("Restricción UNIQUE de 'product_name' eliminada.")
    except psycopg2.ProgrammingError:
        conn.rollback()
        print("INFO: La restricción 'formulas_product_name_key' no existía.")
        pass

    # 5. Añadir una nueva restricción UNIQUE para (user_id, product_name)
    try:
        cursor.execute('ALTER TABLE formulas ADD CONSTRAINT unique_user_product UNIQUE (user_id, product_name);')
        conn.commit()
        print("Restricción UNIQUE para '(user_id, product_name)' añadida.")
    except (psycopg2.errors.DuplicateObject, psycopg2.errors.DuplicateTable): # <-- CAMBIO AQUÍ
        conn.rollback()
        print("INFO: La restricción 'unique_user_product' ya existía.")
        pass


    # --- Tablas sin cambios (se crean si no existen) ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ingredients (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            protein_percent REAL,
            fat_percent REAL,
            water_percent REAL,
            "Ve_Protein_Percent" REAL,
            notes TEXT,
            water_retention_factor REAL,
            min_usage_percent REAL,
            max_usage_percent REAL,
            precio_por_kg REAL,
            categoria TEXT
        );
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS formula_ingredients (
            id SERIAL PRIMARY KEY,
            formula_id INTEGER NOT NULL REFERENCES formulas(id) ON DELETE CASCADE,
            ingredient_id INTEGER NOT NULL REFERENCES ingredients(id) ON DELETE CASCADE,
            quantity REAL NOT NULL,
            unit TEXT NOT NULL
        );
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bibliografia (
            id SERIAL PRIMARY KEY,
            titulo TEXT NOT NULL,
            tipo TEXT,
            contenido TEXT NOT NULL
        );
    ''')

    conn.commit() # Commit final para las creaciones de tablas
    cursor.close()
    conn.close()
    print("Base de datos PostgreSQL inicializada y actualizada para multi-usuario.")

# --- Imports adicionales para seguridad ---
from werkzeug.security import generate_password_hash, check_password_hash

# ... (aquí va tu función initialize_database() que ya tienes) ...

# --- Funciones para Usuarios ---
def add_user(username: str, password: str, full_name: str) -> bool:
    """
    Añade un nuevo usuario a la base de datos.
    Hashea la contraseña para un almacenamiento seguro.
    Devuelve True si fue exitoso, False si el usuario ya existe.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    # Generamos un 'hash' de la contraseña. Nunca guardamos la contraseña original.
    password_hash = generate_password_hash(password)
    try:
        cursor.execute(
            "INSERT INTO users (username, password_hash, full_name) VALUES (%s, %s, %s)",
            (username, password_hash, full_name)
        )
        conn.commit()
        return True
    except psycopg2.IntegrityError: # Esto ocurre si el username ya existe (por la restricción UNIQUE)
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

def get_user_by_username(username: str) -> dict | None:
    """
    Busca un usuario por su nombre de usuario.
    Devuelve los datos del usuario (incluyendo el hash de la contraseña) o None si no se encuentra.
    """
    conn = get_db_connection()
    # Usamos DictCursor para obtener los resultados como un diccionario fácil de usar
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    if user:
        return dict(user)
    return None

def get_user_by_id(user_id: int) -> dict | None:
    """Busca un usuario por su ID."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    if user:
        return dict(user)
    return None

# --- Funciones para Fórmulas ---
def get_all_formulas(user_id: int) -> list[dict]:
    """Obtiene lista simple de todas las fórmulas para un usuario específico."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("SELECT id, product_name, creation_date FROM formulas WHERE user_id = %s ORDER BY product_name", (user_id,))
    formulas = [dict(row) for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return formulas

def get_formula_by_id(formula_id: int, user_id: int) -> dict | None:
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("SELECT * FROM formulas WHERE id = %s AND user_id = %s", (formula_id, user_id))
    formula_row = cursor.fetchone()
    if not formula_row:
        cursor.close()
        conn.close()
        return None

    formula_data = dict(formula_row)
    formula_data['ingredients'] = []

    cursor.execute("""
        SELECT
            fi.id AS formula_ingredient_id, fi.formula_id, fi.ingredient_id,
            fi.quantity, fi.unit, i.name AS ingredient_name, i.protein_percent, 
            i.fat_percent, i.water_percent, i."Ve_Protein_Percent", i.notes,
            i.water_retention_factor, i.min_usage_percent, i.max_usage_percent, 
            i.precio_por_kg, i.categoria
        FROM formula_ingredients fi
        JOIN ingredients i ON fi.ingredient_id = i.id
        WHERE fi.formula_id = %s
    """, (formula_id,))
    
    ingredient_rows = cursor.fetchall()
    formula_data['ingredients'] = [dict(row) for row in ingredient_rows]
    cursor.close()
    conn.close()
    return formula_data

def add_formula(product_name: str, user_id: int, description: str = "") -> int | None:
    conn = get_db_connection()
    cursor = conn.cursor()
    creation_date = datetime.datetime.now().isoformat()
    try:
        cursor.execute("INSERT INTO formulas (product_name, description, creation_date, user_id) VALUES (%s, %s, %s, %s) RETURNING id", 
                       (product_name, description, creation_date, user_id))
        formula_id = cursor.fetchone()[0]
        conn.commit()
        return formula_id
    except psycopg2.IntegrityError:
        return None
    finally:
        cursor.close()
        conn.close()

def delete_formula(formula_id: int, user_id: int) -> bool:
    """Elimina una fórmula y sus ingredientes asociados de la base de datos, verificando el propietario."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # La verificación de user_id asegura que un usuario no pueda borrar fórmulas de otro.
        cursor.execute("DELETE FROM formulas WHERE id = %s AND user_id = %s", (formula_id, user_id))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"ERROR eliminando fórmula: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

def update_formula_name(formula_id: int, new_name: str, user_id: int) -> bool:
    """Actualiza el nombre de una fórmula específica, verificando el propietario."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # La restricción UNIQUE(user_id, product_name) se encarga de evitar duplicados por usuario.
        cursor.execute("UPDATE formulas SET product_name = %s WHERE id = %s AND user_id = %s", (new_name, formula_id, user_id))
        conn.commit()
        return cursor.rowcount > 0
    except psycopg2.IntegrityError: # Falla si el nombre ya existe para ese usuario.
        conn.rollback()
        return False
    except Exception as e:
        print(f"ERROR actualizando nombre de fórmula: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

# --- Funciones para Ingredientes en Fórmulas ---
def _get_or_create_ingredient(cursor, name: str) -> int | None:
    """Helper: Busca o crea un ingrediente maestro y devuelve su ID."""
    cursor.execute("SELECT id FROM ingredients WHERE name ILIKE %s", (name,))
    result = cursor.fetchone()
    if result:
        return result['id']
    else:
        cursor.execute("INSERT INTO ingredients (name) VALUES (%s) RETURNING id", (name,))
        return cursor.fetchone()['id']

def add_ingredient_to_formula(formula_id: int, ingredient_name: str, quantity: float, unit: str):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        ingredient_master_id = _get_or_create_ingredient(cursor, ingredient_name)
        cursor.execute("INSERT INTO formula_ingredients (formula_id, ingredient_id, quantity, unit) VALUES (%s, %s, %s, %s)",
                       (formula_id, ingredient_master_id, quantity, unit))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

def update_ingredient(formula_ingredient_id: int, name: str, quantity: float, unit: str):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        ingredient_master_id = _get_or_create_ingredient(cursor, name)
        cursor.execute("UPDATE formula_ingredients SET ingredient_id = %s, quantity = %s, unit = %s WHERE id = %s",
                       (ingredient_master_id, quantity, unit, formula_ingredient_id))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

def delete_ingredient(formula_ingredient_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM formula_ingredients WHERE id = %s", (formula_ingredient_id,))
    conn.commit()
    cursor.close()
    conn.close()

def get_formula_id_for_ingredient(formula_ingredient_id: int) -> int | None:
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("SELECT formula_id FROM formula_ingredients WHERE id = %s", (formula_ingredient_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result['formula_id'] if result else None

# --- Funciones de Ingredientes Maestros ---
def get_all_ingredients_with_details() -> list[dict]:
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("SELECT * FROM ingredients ORDER BY name")
    results = [dict(row) for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return results

def add_master_ingredient(details: dict) -> int | None:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        fields = ['name', 'protein_percent', 'fat_percent', 'water_percent', 'water_retention_factor', 'precio_por_kg', 'categoria']
        values = [details.get(field) for field in fields]
        sql = f"INSERT INTO ingredients (name, protein_percent, fat_percent, water_percent, water_retention_factor, precio_por_kg, categoria) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id"
        cursor.execute(sql, values)
        new_id = cursor.fetchone()[0]
        conn.commit()
        return new_id
    except psycopg2.IntegrityError:
        return None
    finally:
        cursor.close()
        conn.close()

def update_master_ingredient(ingredient_id: int, details: dict) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        fields_to_update = ['name', 'protein_percent', 'fat_percent', 'water_percent', 'water_retention_factor', 'precio_por_kg', 'categoria']
        set_clause = ", ".join([f"{field} = %s" for field in fields_to_update])
        values = [details.get(field) for field in fields_to_update]
        values.append(ingredient_id)
        sql = f"UPDATE ingredients SET {set_clause} WHERE id = %s"
        cursor.execute(sql, values)
        conn.commit()
        return cursor.rowcount > 0
    finally:
        cursor.close()
        conn.close()

def delete_master_ingredient(ingredient_id: int) -> str:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM ingredients WHERE id = %s", (ingredient_id,))
        conn.commit()
        return 'success' if cursor.rowcount > 0 else 'not_found'
    except psycopg2.IntegrityError:
        return 'in_use'
    finally:
        cursor.close()
        conn.close()

def search_ingredient_names(query: str) -> list[str]:
    conn = get_db_connection()
    cursor = conn.cursor()
    search_term = f"%{query}%"
    cursor.execute("SELECT name FROM ingredients WHERE name ILIKE %s ORDER BY name LIMIT 10", (search_term,))
    results = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return results
    
def get_distinct_ingredient_names() -> list[str]:
    """Obtiene la lista de todos los nombres de ingredientes maestros."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM ingredients ORDER BY name")
    names = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return names

# --- Funciones de Bibliografía ---
def get_all_bibliografia() -> list[dict]:
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("SELECT * FROM bibliografia ORDER BY titulo")
    results = [dict(row) for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return results

def add_bibliografia_entry(titulo: str, tipo: str, contenido: str) -> int | None:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO bibliografia (titulo, tipo, contenido) VALUES (%s, %s, %s) RETURNING id", (titulo, tipo, contenido))
        new_id = cursor.fetchone()[0]
        conn.commit()
        return new_id
    finally:
        cursor.close()
        conn.close()

def update_bibliografia_entry(entry_id: int, titulo: str, tipo: str, contenido: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE bibliografia SET titulo = %s, tipo = %s, contenido = %s WHERE id = %s", (titulo, tipo, contenido, entry_id))
    conn.commit()
    success = cursor.rowcount > 0
    cursor.close()
    conn.close()
    return success

def delete_bibliografia_entry(entry_id: int) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM bibliografia WHERE id = %s", (entry_id,))
    conn.commit()
    success = cursor.rowcount > 0
    cursor.close()
    conn.close()
    return success

def search_bibliografia(query: str, limit: int = 3) -> list[dict]:
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    stopwords = {'a', 'con', 'cual', 'de', 'del', 'el', 'en', 'es', 'ideal', 'la', 'las', 'los', 'o', 'para', 'que', 'se', 'segun', 'sin', 'un', 'una', 'y'}
    keywords = [word for word in query.lower().split() if len(word) > 2 and word not in stopwords]
    if not keywords: return []
    where_clauses = " OR ".join(["contenido ILIKE %s"] * len(keywords))
    sql_query = f"SELECT * FROM bibliografia WHERE {where_clauses} LIMIT %s"
    values = [f"%{key}%" for key in keywords]
    values.append(limit)
    cursor.execute(sql_query, values)
    results = [dict(row) for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return results