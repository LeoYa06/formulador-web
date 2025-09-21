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

    # 1. Crear tabla de usuarios (si no existe)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL UNIQUE, /* Correo electrónico */
            password_hash TEXT NOT NULL,
            full_name TEXT,
            is_verified BOOLEAN DEFAULT FALSE,
            verification_code TEXT,
            code_expiry TIMESTAMP,
            session_token VARCHAR(64)
        );
    ''')

    # Añadir columnas de manera idempotente
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN full_name TEXT;')
    except psycopg2.errors.DuplicateColumn:
        conn.rollback()
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT FALSE;')
    except psycopg2.errors.DuplicateColumn:
        conn.rollback()
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN verification_code TEXT;')
    except psycopg2.errors.DuplicateColumn:
        conn.rollback()
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN code_expiry TIMESTAMP;')
    except psycopg2.errors.DuplicateColumn:
        conn.rollback()
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN session_token VARCHAR(64);')
    except psycopg2.errors.DuplicateColumn:
        conn.rollback()
    
    conn.commit()

    # 2. Crear tabla de fórmulas (si no existe)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS formulas (
            id SERIAL PRIMARY KEY,
            product_name TEXT NOT NULL,
            description TEXT,
            creation_date TEXT NOT NULL,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE
        );
    ''')
    conn.commit()

    # 3. Añadir restricción UNIQUE a formulas (user_id, product_name)
    try:
        cursor.execute('ALTER TABLE formulas ADD CONSTRAINT unique_user_product UNIQUE (user_id, product_name);')
        conn.commit()
    except (psycopg2.errors.DuplicateObject, psycopg2.errors.DuplicateTable):
        conn.rollback()

    # --- Tablas que deben existir pero no se crean aquí ---
    # Se asume que 'base_ingredients', 'user_ingredients' y 'formula_ingredients'
    # ya están creadas y configuradas correctamente en la base de datos de producción.
    # Lo mismo para la tabla 'bibliografia'.

    cursor.close()
    conn.close()
    print("Base de datos PostgreSQL inicializada y actualizada para multi-usuario.")


# --- Imports adicionales para seguridad ---
from werkzeug.security import generate_password_hash, check_password_hash

# --- Funciones para Usuarios ---
def add_user(username: str, password: str, full_name: str, verification_code: str = None, code_expiry: datetime = None) -> bool:
    """
    Añade un nuevo usuario a la base de datos.
    Hashea la contraseña para un almacenamiento seguro.
    Guarda el código de verificación y su expiración.
    Devuelve True si fue exitoso, False si el usuario ya existe.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    password_hash = generate_password_hash(password)
    try:
        cursor.execute(
            "INSERT INTO users (username, password_hash, full_name, verification_code, code_expiry) VALUES (%s, %s, %s, %s, %s)",
            (username, password_hash, full_name, verification_code, code_expiry)
        )
        conn.commit()
        return True
    except psycopg2.IntegrityError:
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

def get_user_by_username(username: str) -> dict | None:
    """
    Busca un usuario por su nombre de usuario (email).
    Devuelve los datos del usuario o None si no se encuentra.
    """
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return dict(user) if user else None

def get_user_by_id(user_id: int) -> dict | None:
    """Busca un usuario por su ID."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return dict(user) if user else None

def verify_user(username: str) -> bool:
    """Marca a un usuario como verificado y limpia los datos de verificación."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE users SET is_verified = TRUE, verification_code = NULL, code_expiry = NULL WHERE username = %s",
            (username,)
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"ERROR al verificar usuario: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

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

    # ¡IMPORTANTE! Esta consulta asume que `formula_ingredients.ingredient_id`
    # ahora referencia a `user_ingredients.id`.
    cursor.execute('''
        SELECT
            fi.id AS formula_ingredient_id, fi.formula_id, fi.ingredient_id,
            fi.quantity, fi.unit, i.name AS ingredient_name, i.protein_percent,
            i.fat_percent, i.water_percent, i.ve_protein_percent, i.notes,
            i.water_retention_factor, i.min_usage_percent, i.max_usage_percent,
            i.precio_por_kg, i.categoria
        FROM formula_ingredients fi
        JOIN user_ingredients i ON fi.ingredient_id = i.id
        WHERE fi.formula_id = %s AND i.user_id = %s
    ''', (formula_id, user_id))

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
        conn.rollback()
        return None
    finally:
        cursor.close()
        conn.close()

def delete_formula(formula_id: int, user_id: int) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
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
    """
    Actualiza el nombre de una fórmula específica.
    
    Args:
        formula_id (int): ID de la fórmula a actualizar
        new_name (str): Nuevo nombre para la fórmula
        user_id (int): ID del usuario propietario
    
    Returns:
        bool: True si la actualización fue exitosa, False en caso contrario
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Actualizar el nombre de la fórmula solo si pertenece al usuario
        cursor.execute('''
            UPDATE formulas 
            SET product_name = %s
            WHERE id = %s AND user_id = %s
        ''', (new_name, formula_id, user_id))
        
        conn.commit()
        success = cursor.rowcount > 0  # True si se actualizó al menos una fila
        return success
        
    except Exception as e:
        print(f"Error actualizando nombre de fórmula: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

# --- Funciones para Ingredientes en Fórmulas ---
def _get_or_create_user_ingredient(cursor, name: str, user_id: int) -> int | None:
    """Helper: Busca o crea un ingrediente de usuario y devuelve su ID."""
    cursor.execute("SELECT id FROM user_ingredients WHERE name ILIKE %s AND user_id = %s", (name, user_id))
    result = cursor.fetchone()
    if result:
        return result['id']
    else:
        # Si no existe, lo crea solo con el nombre y el user_id. El resto de datos son NULL.
        cursor.execute("INSERT INTO user_ingredients (name, user_id) VALUES (%s, %s) RETURNING id", (name, user_id))
        return cursor.fetchone()['id']

# Replace the existing function in database.py with this one

def _get_user_ingredient_id_by_name(cursor, ingredient_name: str, user_id: int):
    """Finds the ID of an ingredient by its name for a specific user (case-insensitive)."""
    # Use ILIKE instead of = for a case-insensitive search
    sql = "SELECT id FROM user_ingredients WHERE name ILIKE %s AND user_id = %s"
    cursor.execute(sql, (ingredient_name, user_id))
    result = cursor.fetchone()
    if result:
        return result['id']
    return None # Ingredient not found for this user

# This is your updated main function that calls the corrected helper
def add_ingredient_to_formula(formula_id: int, ingredient_name: str, quantity: float, unit: str, user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        # Call the new, corrected helper function
        ingredient_id = _get_user_ingredient_id_by_name(cursor, ingredient_name, user_id)
        
        if ingredient_id:
            # Now we use the correct ingredient_id from the user's personal list
            cursor.execute(
                "INSERT INTO formula_ingredients (formula_id, ingredient_id, quantity, unit) VALUES (%s, %s, %s, %s)",
                (formula_id, ingredient_id, quantity, unit)
            )
            conn.commit()
        else:
            # This handles the case where the ingredient name doesn't exist for the user
            print(f"Error: Ingredient '{ingredient_name}' not found for user_id {user_id}")
            conn.rollback()
    finally:
        cursor.close()
        conn.close()

def update_ingredient(formula_ingredient_id: int, name: str, quantity: float, unit: str, user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        ingredient_user_id = _get_or_create_user_ingredient(cursor, name, user_id)
        cursor.execute("UPDATE formula_ingredients SET ingredient_id = %s, quantity = %s, unit = %s WHERE id = %s",
                       (ingredient_user_id, quantity, unit, formula_ingredient_id))
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

# --- Funciones de Ingredientes de Usuario ---
def get_user_ingredients(user_id: int) -> list[dict]:
    """Obtiene todos los ingredientes para un usuario específico."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("SELECT * FROM user_ingredients WHERE user_id = %s ORDER BY name", (user_id,))
    results = [dict(row) for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return results

def add_user_ingredient(details: dict, user_id: int) -> int | None:
    """Añade un nuevo ingrediente a la colección de un usuario."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        fields = ['name', 'protein_percent', 'fat_percent', 'water_percent', 'water_retention_factor', 'precio_por_kg', 'categoria', 'user_id']
        values = [details.get(field) for field in fields[:-1]]
        values.append(user_id)
        
        sql = f"INSERT INTO user_ingredients (name, protein_percent, fat_percent, water_percent, water_retention_factor, precio_por_kg, categoria, user_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id"
        cursor.execute(sql, values)
        new_id = cursor.fetchone()[0]
        conn.commit()
        return new_id
    except psycopg2.IntegrityError: # Ocurre si el nombre ya existe para ese usuario
        conn.rollback()
        return None
    finally:
        cursor.close()
        conn.close()

def update_user_ingredient(ingredient_id: int, details: dict, user_id: int) -> bool:
    """Actualiza un ingrediente específico de un usuario."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        fields_to_update = ['name', 'protein_percent', 'fat_percent', 'water_percent', 'water_retention_factor', 'precio_por_kg', 'categoria']
        set_clause = ", ".join([f"{field} = %s" for field in fields_to_update])
        values = [details.get(field) for field in fields_to_update]
        values.extend([ingredient_id, user_id])
        
        sql = f"UPDATE user_ingredients SET {set_clause} WHERE id = %s AND user_id = %s"
        cursor.execute(sql, values)
        conn.commit()
        return cursor.rowcount > 0
    except psycopg2.IntegrityError:
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

def delete_user_ingredient(ingredient_id: int, user_id: int) -> str:
    """Elimina un ingrediente de un usuario, si no está en uso."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM user_ingredients WHERE id = %s AND user_id = %s", (ingredient_id, user_id))
        conn.commit()
        return 'success' if cursor.rowcount > 0 else 'not_found'
    except psycopg2.IntegrityError: # Falla si el ingrediente está en uso en formula_ingredients
        conn.rollback()
        return 'in_use'
    finally:
        cursor.close()
        conn.close()

def search_user_ingredient_names(query: str, user_id: int) -> list[str]:
    """Busca nombres de ingredientes para un usuario específico."""
    conn = get_db_connection()
    cursor = conn.cursor()
    search_term = f"%{query}%"
    cursor.execute("SELECT name FROM user_ingredients WHERE name ILIKE %s AND user_id = %s ORDER BY name LIMIT 10", (search_term, user_id))
    results = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return results

# --- Funciones de Bibliografía (sin cambios) ---
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

# --- Funciones de Sesión ---
def update_session_token(user_id, token):
    """Actualiza el token de sesión de un usuario en la base de datos."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET session_token = %s WHERE id = %s", (token, user_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating session token: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

def get_session_token_for_user(user_id):
    """Obtiene el token de sesión actual de un usuario desde la base de datos."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cursor.execute("SELECT session_token FROM users WHERE id = %s", (user_id,))
        result = cursor.fetchone()
        token = result['session_token'] if result else None
        return token
    except Exception as e:
        print(f"Error getting session token: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def seed_initial_ingredients(user_id):
    """
    Copies all ingredients from the base_ingredients table to the
    user_ingredients table for a new user.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute("SELECT * FROM base_ingredients")
        base_ingredients = cursor.fetchall()

        user_ingredients_to_insert = []
        for ingredient in base_ingredients:
            user_ingredients_to_insert.append((
                ingredient['name'],
                ingredient['protein_percent'],
                ingredient['fat_percent'],
                ingredient['water_percent'],
                ingredient['Ve_Protein_Percent'],  # <-- CORREGIDO CON MAYÚSCULAS
                ingredient['notes'],
                ingredient['water_retention_factor'],
                ingredient['min_usage_percent'],
                ingredient['max_usage_percent'],
                ingredient['precio_por_kg'],
                ingredient['categoria'],
                user_id
            ))

        if user_ingredients_to_insert:
            sql = """
                INSERT INTO user_ingredients (
                    name, protein_percent, fat_percent, water_percent, ve_protein_percent,
                    notes, water_retention_factor, min_usage_percent, max_usage_percent,
                    precio_por_kg, categoria, user_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            # También corregimos el nombre de la columna en la consulta INSERT
            sql = sql.replace('ve_protein_percent', 'Ve_Protein_Percent')
            cursor.executemany(sql, user_ingredients_to_insert)
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error seeding ingredients for user {user_id}: {e}")
        conn.rollback()
        return False
