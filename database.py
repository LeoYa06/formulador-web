# db/database.py
import os
import psycopg2
import psycopg2.extras
import datetime
import decimal
from werkzeug.security import generate_password_hash, check_password_hash

def convert_row_to_dict(row):
    """
    Convierte una fila (p. ej. psycopg2.extras.DictRow) a un dict normalizando tipos:
    - decimal.Decimal -> int (si es entero) o float
    - datetime.datetime -> ISO string
    - deja otros tipos tal cual
    """
    # Si ya es un dict simple, copiarlo y normalizar valores
    try:
        items = row.items()
    except Exception:
        # Si no tiene .items(), intentamos convertir directamente
        try:
            return dict(row)
        except Exception:
            return {}

    result = {}
    for key, value in items:
        if isinstance(value, decimal.Decimal):
            # Convertir Decimal a int si no tiene parte fraccionaria, sino a float
            try:
                if value == value.to_integral():
                    result[key] = int(value)
                else:
                    result[key] = float(value)
            except Exception:
                result[key] = float(value)
        elif isinstance(value, datetime.datetime):
            # Representar fechas como ISO strings para JSON-friendliness
            result[key] = value.isoformat()
        else:
            result[key] = value
    return result

# --- Configuración para PostgreSQL ---
DATABASE_URL = os.getenv("DATABASE_URL")
print(f"DEBUG: La URL de la base de datos en el entorno es: {DATABASE_URL}")

def get_db_connection():
    """Establece conexión con la base de datos PostgreSQL."""
    print("Intentando conectar a la base de datos...")
    conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
    print("Conexión a la base de datos exitosa.")
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
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN credits INTEGER DEFAULT 0;')
    except psycopg2.errors.DuplicateColumn:
        conn.rollback()
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN credits_expiry_date TIMESTAMP;')
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
# En database.py

def add_user(username: str, password: str, full_name: str, verification_code: str = None, code_expiry: datetime = None) -> bool:
    """Añade un nuevo usuario y devuelve su ID, o None si falla."""
    conn = get_db_connection()
    cursor = conn.cursor()
    password_hash = generate_password_hash(password)
    initial_credits = 100  # Créditos de prueba

    # --- CORREGIDO ---
    expiry_date = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=3)

    try:
        cursor.execute(
            "INSERT INTO users (username, password_hash, full_name, verification_code, code_expiry, credits, credits_expiry_date) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
            (username, password_hash, full_name, verification_code, code_expiry, initial_credits, expiry_date)
        )
        new_user_id = cursor.fetchone()[0]
        conn.commit()
        return new_user_id
    except psycopg2.IntegrityError:
        conn.rollback()
        return None
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

# --- Funciones para Créditos ---

def get_user_credits(user_id: int) -> int:
    """Obtiene los créditos de un usuario."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT credits FROM users WHERE id = %s", (user_id,))
        result = cursor.fetchone()
        return result[0] if result and result[0] is not None else 0
    except Exception as e:
        print(f"ERROR obteniendo créditos: {e}")
        return 0
    finally:
        cursor.close()
        conn.close()

# En database.py

def add_user_credits(user_id: int, amount: int) -> bool:
    """Añade créditos a un usuario y extiende su expiración por 30 días."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # --- CORREGIDO ---
    # Calcula la nueva fecha de expiración usando una fecha "aware" (con zona horaria UTC)
    new_expiry_date = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)
    
    try:
        # Primero, obtenemos los créditos actuales para asegurarnos de que no sean NULL
        cursor.execute("SELECT credits FROM users WHERE id = %s", (user_id,))
        result = cursor.fetchone()
        current_credits = result[0] if result and result[0] is not None else 0
        
        # Calculamos los nuevos créditos
        new_total_credits = current_credits + amount
        
        # Actualizamos
        cursor.execute(
            "UPDATE users SET credits = %s, credits_expiry_date = %s WHERE id = %s",
            (new_total_credits, new_expiry_date, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"ERROR añadiendo créditos: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

def decrement_user_credits(user_id: int, amount: int) -> bool:
    """Descuenta créditos de un usuario si tiene suficientes."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET credits = credits - %s WHERE id = %s AND credits >= %s", (amount, user_id, amount))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"ERROR descontando créditos: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

# En database.py

def check_and_handle_credit_expiration(user_id: int) -> int:
    """Verifica la expiración de créditos y los resetea si es necesario."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cursor.execute("SELECT credits, credits_expiry_date FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            return 0

        current_credits = user['credits']
        expiry_date = user['credits_expiry_date'] # Esta fecha de Supabase es "aware" (con zona horaria)

        # Si no hay fecha de expiración (ej. NULL), no puede expirar.
        if not expiry_date:
            return current_credits if current_credits is not None else 0

        # --- CORREGIDO ---
        # Obtenemos la hora actual en UTC, pero como un objeto "aware" (con zona horaria)
        # para poder compararlo correctamente con 'expiry_date'.
        ahora_utc = datetime.datetime.now(datetime.timezone.utc) 

        # Ahora la comparación (aware > aware) funciona
        if ahora_utc > expiry_date:
            print(f"Créditos expirados para el usuario {user_id}. Reseteando.")
            cursor.execute("UPDATE users SET credits = 0, credits_expiry_date = NULL WHERE id = %s", (user_id,))
            conn.commit()
            return 0  # Devuelve 0 créditos porque acaban de expirar

        # Si no ha expirado, devuelve los créditos actuales
        return current_credits if current_credits is not None else 0

    except Exception as e:
        # El TypeError de la comparación "simple vs completa" caía aquí.
        print(f"Error manejando la expiración de créditos: {e}")
        conn.rollback()
        return 0 # Asumir 0 créditos en caso de error
    finally:
        cursor.close()
        conn.close()

# --- Funciones para Fórmulas ---
def get_all_formulas(user_id: int) -> list[dict]:
    """Obtiene lista simple de todas las fórmulas para un usuario específico."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute("SELECT id, product_name, creation_date FROM formulas WHERE user_id = %s ORDER BY product_name", (user_id,))
        formulas = [dict(row) for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return formulas
    except Exception as e:
        print(f"ERROR obteniendo todas las fórmulas: {e}")
        return [] # Devuelve lista vacía en caso de error

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
# (Pégala alrededor de la línea 525)

def _get_base_ingredient_data_by_name(cursor, ingredient_name: str) -> dict | None:
    """Obtiene los datos completos de un ingrediente de la tabla base (case-insensitive)."""
    # Esta función usa 'cursor' y no maneja la conexión (es un helper)
    sql = 'SELECT * FROM base_ingredients WHERE name ILIKE %s'
    try:
        cursor.execute(sql, (ingredient_name,))
        result = cursor.fetchone()
        return dict(result) if result else None
    except Exception as e:
        print(f"ERROR en _get_base_ingredient_data_by_name: {e}")
        return None

# REEMPLAZA la función _get_user_ingredient_id_by_name (en la línea 528) CON ESTA:

def _get_or_create_user_ingredient_id_by_name(cursor, ingredient_name: str, user_id: int) -> int | None:
    """
    Busca el ID de un ingrediente en la lista del usuario.
    Si no existe, lo busca en la lista base ('base_ingredients').
    Si existe en la base, lo copia a la lista del usuario ('user_ingredients') y devuelve el nuevo ID.
    Si no existe en ningún lado, devuelve None.
    """
    # 1. Buscar en la lista de ingredientes del usuario (como antes)
    sql_user = "SELECT id FROM user_ingredients WHERE name ILIKE %s AND user_id = %s"
    cursor.execute(sql_user, (ingredient_name, user_id))
    result_user = cursor.fetchone()
    
    if result_user:
        # ¡Encontrado! Devolver el ID existente.
        return result_user['id']
    
    # 2. No encontrado. Buscar en la lista de ingredientes base.
    print(f"Ingrediente '{ingredient_name}' no encontrado para user {user_id}. Buscando en la tabla base...")
    base_ingredient_data = _get_base_ingredient_data_by_name(cursor, ingredient_name)
    
    if base_ingredient_data:
        # 3. ¡Encontrado en la base! Copiarlo a la lista del usuario.
        print(f"Encontrado en la base. Copiando a la lista del usuario {user_id}...")
        
        # --- Lógica de Copia (basada en tu 'seed_initial_ingredients') ---
        try:
            # Usamos comillas dobles para el nombre de columna con mayúsculas
            # (basado en tu función 'seed_initial_ingredients' línea 797)
            sql_insert = """
                INSERT INTO user_ingredients (
                    name, protein_percent, fat_percent, water_percent, "Ve_Protein_Percent",
                    notes, water_retention_factor, min_usage_percent, max_usage_percent,
                    precio_por_kg, categoria, user_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """
            
            values = (
                base_ingredient_data['name'],
                base_ingredient_data.get('protein_percent'),
                base_ingredient_data.get('fat_percent'),
                base_ingredient_data.get('water_percent'),
                base_ingredient_data.get('Ve_Protein_Percent'), # Clave con V mayúscula
                base_ingredient_data.get('notes'),
                base_ingredient_data.get('water_retention_factor'),
                base_ingredient_data.get('min_usage_percent'),
                base_ingredient_data.get('max_usage_percent'),
                base_ingredient_data.get('precio_por_kg'),
                base_ingredient_data.get('categoria'),
                user_id
            )
            
            cursor.execute(sql_insert, values)
            new_user_ingredient_id = cursor.fetchone()['id']
            print(f"Ingrediente copiado exitosamente. Nuevo ID de user_ingredient: {new_user_ingredient_id}")
            return new_user_ingredient_id

        except psycopg2.errors.UndefinedColumn:
            # ¡FALLBACK! La columna NO se llama "Ve_Protein_Percent" (mayúscula)
            # Probemos con 've_protein_percent' (minúscula)
            print("ADVERTENCIA: Falló 'Ve_Protein_Percent'. Intentando con 've_protein_percent' (minúscula)...")
            cursor.connection.rollback() # Deshacer el INSERT fallido
            
            sql_insert_lowercase = """
                INSERT INTO user_ingredients (
                    name, protein_percent, fat_percent, water_percent, ve_protein_percent,
                    notes, water_retention_factor, min_usage_percent, max_usage_percent,
                    precio_por_kg, categoria, user_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """
            # Los valores son los mismos, el nombre de la columna en el SQL es diferente
            cursor.execute(sql_insert_lowercase, values)
            new_user_ingredient_id_lc = cursor.fetchone()['id']
            print(f"Ingrediente copiado exitosamente (usando minúscula). Nuevo ID: {new_user_ingredient_id_lc}")
            return new_user_ingredient_id_lc

        except Exception as e:
            print(f"ERROR FATAL al copiar ingrediente de base a usuario: {e}")
            cursor.connection.rollback()
            return None
        # --- Fin Lógica de Copia ---

    # 4. No encontrado en ningún lado.
    return None

# REEMPLAZA la función add_ingredient_to_formula (en la línea 538) CON ESTA:

def add_ingredient_to_formula(formula_id: int, ingredient_name: str, quantity: float, unit: str, user_id: int):
    """
    Añade un ingrediente a una fórmula, buscándolo o creándolo
    en la lista de ingredientes del usuario (user_ingredients).
    """
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        # Llamar a la NUEVA función orquestadora
        # (Fíjate que el nombre de la función cambió)
        ingredient_id = _get_or_create_user_ingredient_id_by_name(cursor, ingredient_name, user_id)
        
        if ingredient_id:
            # El ingrediente ya existe (o se acaba de crear) en user_ingredients.
            # Ahora podemos añadirlo a formula_ingredients.
            cursor.execute(
                "INSERT INTO formula_ingredients (formula_id, ingredient_id, quantity, unit) VALUES (%s, %s, %s, %s)",
                (formula_id, ingredient_id, quantity, unit)
            )
            conn.commit()
            print(f"Ingrediente '{ingredient_name}' (ID: {ingredient_id}) añadido exitosamente a la fórmula {formula_id}.")
        else:
            # Este 'else' ahora significa que el ingrediente NO EXISTE EN NINGUNA TABLA
            print(f"Error FATAL: Ingrediente '{ingredient_name}' no fue encontrado NI en user_ingredients NI en base_ingredients.")
            conn.rollback()
    except Exception as e:
        print(f"ERROR en add_ingredient_to_formula: {e}")
        conn.rollback()
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

def update_ingredient(formula_ingredient_id: int, new_name: str, new_quantity: float, new_unit: str, user_id: int) -> bool:
    """
    Actualiza un ingrediente dentro de una fórmula.
    Esto implica:
    1. Encontrar/crear el 'user_ingredient_id' basado en el nuevo nombre.
    2. Actualizar la entrada en 'formula_ingredients' con el nuevo ID, cantidad y unidad.
    """
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        # 1. Usamos el helper que ya existe para encontrar el ID del ingrediente
        # (ya sea que exista en 'user_ingredients' o lo copie de 'base_ingredients')
        new_ingredient_id = _get_or_create_user_ingredient_id_by_name(cursor, new_name, user_id)

        if not new_ingredient_id:
            # Esto no debería pasar si el helper funciona
            print(f"ERROR: No se pudo encontrar o crear el ID para el ingrediente '{new_name}'")
            conn.rollback()
            return False

        # 2. Actualizamos la tabla 'formula_ingredients'
        sql = """
            UPDATE formula_ingredients
            SET ingredient_id = %s, quantity = %s, unit = %s
            WHERE id = %s
        """
        cursor.execute(sql, (new_ingredient_id, new_quantity, new_unit, formula_ingredient_id))
        conn.commit()
        return cursor.rowcount > 0 # Devuelve True si se actualizó 1 fila

    except Exception as e:
        print(f"ERROR en update_ingredient: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

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

def get_master_ingredients() -> list[dict]:
    """
    Obtiene SÓLO los ingredientes MAESTROS (de la tabla base)
    para evitar duplicados.
    """
    conn = get_db_connection()
    results = []
    
    if conn is None:
        print("ERROR: No se pudo obtener conexión a la base de datos en get_master_ingredients.")
        return []

    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            
            # Consultamos SÓLO la tabla 'base_ingredients'.
            # Esto soluciona el problema de los duplicados.
            cursor.execute("SELECT * FROM base_ingredients ORDER BY name")
            
            # Usamos la función auxiliar 'convert_row_to_dict' que ya deberías tener
            # de nuestras correcciones anteriores (la que maneja 'Decimal' y 'datetime').
            for row in cursor.fetchall():
                results.append(convert_row_to_dict(row))
                
    except Exception as e:
        print(f"ERROR al consultar base_ingredients en get_master_ingredients: {e}")
        if conn:
            conn.rollback()
    
    finally:
        if conn:
            conn.close()
            
    # La lista ya viene ordenada de la consulta SQL (ORDER BY name)
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

def search_base_ingredient_names(query: str) -> list[str]:
    """Busca nombres de ingredientes en la tabla base (base_ingredients)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    search_term = f"%{query}%"
    
    results = []
    try:
        # Asegúrate de que el nombre de la tabla 'base_ingredients' sea correcto
        cursor.execute("SELECT name FROM base_ingredients WHERE name ILIKE %s ORDER BY name LIMIT 10", (search_term,))
        results = [row[0] for row in cursor.fetchall()]
    except Exception as e:
        print(f"ERROR en search_base_ingredient_names: {e}")
    finally:
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
