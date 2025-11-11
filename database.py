import os
import psycopg2
import psycopg2.extras
import psycopg2.pool
import datetime
import decimal
import logging 
import time
import atexit
from functools import wraps
from contextlib import contextmanager 
from werkzeug.security import generate_password_hash, check_password_hash

# --- Configuración de Logging ---
logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO').upper(), 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

def convert_row_to_dict(row):
    """
    Convierte una fila (p. ej. psycopg2.extras.DictRow) a un dict normalizando tipos.
    """
    try:
        items = row.items()
    except Exception:
        try:
            return dict(row)
        except Exception:
            return {}

    result = {}
    for key, value in items:
        if isinstance(value, decimal.Decimal):
            try:
                if value == value.to_integral():
                    result[key] = int(value)
                else:
                    result[key] = float(value)
            except Exception:
                result[key] = float(value)
        elif isinstance(value, datetime.datetime):
            result[key] = value.isoformat()
        else:
            result[key] = value
    return result

# --- Configuración para PostgreSQL ---
DATABASE_URL = os.getenv("DATABASE_URL")

# --- Forzar SSL para entornos de producción como Render ---
if DATABASE_URL and 'sslmode' not in DATABASE_URL and 'localhost' not in DATABASE_URL:
    DATABASE_URL += "?sslmode=require"
    log.info("Añadiendo '?sslmode=require' a la DATABASE_URL para conexión de producción.")

log.info(f"Conectando a la URL de la base de datos: {DATABASE_URL[:30]}...") 

# --- CREACIÓN DEL POOL DE CONEXIONES ---
try:
    db_pool = psycopg2.pool.SimpleConnectionPool(
        1,  # minconn
        10, # maxconn
        dsn=DATABASE_URL
    )
    log.info("Pool de conexiones de base de datos creado exitosamente.")
except Exception as e:
    log.error(f"FATAL: No se pudo crear el pool de conexiones. {e}")
    db_pool = None

def get_db_connection():
    """
    Obtiene una conexión del POOL.
    Lanza una excepción si el pool no está disponible.
    """
    global db_pool
    if db_pool is None:
        log.error("El pool de conexiones no está inicializado. Intentando recrear...")
        try:
            db_pool = psycopg2.pool.SimpleConnectionPool(1, 10, dsn=DATABASE_URL)
            log.info("Pool de conexiones recreado exitosamente.")
        except Exception as e:
            log.error(f"ERROR CRÍTICO: No se pudo recrear el pool de conexiones. {e}")
            raise psycopg2.OperationalError(f"No se pudo recrear el pool: {e}")
            
    try:
        conn = db_pool.getconn()
        log.debug("Conexión obtenida del pool.")
        return conn
    except Exception as e:
        log.error(f"ERROR: No se pudo obtener conexión del pool. {e}")
        raise psycopg2.OperationalError(f"No se pudo obtener conexión del pool: {e}")


def release_db_connection(conn):
    """
    Devuelve una conexión al POOL.
    """
    global db_pool
    if db_pool and conn:
        log.debug("Devolviendo conexión al pool.")
        db_pool.putconn(conn)

# --- ¡NUEVO! DECORADOR DE REINTENTO ---
def retry_on_connection_error(retries=3, delay=1):
    """
    Decorador que reintenta una función si falla con un error de conexión.
    Maneja errores operacionales (conexión caída) e interface (pool vacío).
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            for attempt in range(retries):
                try:
                    return f(*args, **kwargs)
                except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                    log.warning(f"Error de conexión/pool en {f.__name__} (intento {attempt + 1}/{retries}): {e}")
                    if attempt + 1 == retries:
                        log.error(f"Error de conexión final en {f.__name__} después de {retries} intentos.")
                        raise # Re-lanza la última excepción
                    # Espera exponencial (1s, 2s, 4s...)
                    time.sleep(delay * (2 ** attempt))
        return wrapper
    return decorator

# --- ¡NUEVO! GESTOR DE CONTEXTO CON REINTENTO ---
@contextmanager
def get_db_connection_context():
    """
    Gestor de contexto para obtener y liberar una conexión del pool.
    Reintenta automáticamente si falla al *obtener* la conexión.
    """
    conn = None
    retries = 3
    delay = 1
    for attempt in range(retries):
        try:
            conn = get_db_connection()
            if conn is None:
                raise psycopg2.OperationalError("No se pudo obtener una conexión del pool (None).")
            
            yield conn # Proporciona la conexión al bloque 'with'
            
            # Si salimos del 'yield' sin error, rompemos el bucle
            break 
            
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
            log.warning(f"Error al obtener conexión del pool (intento {attempt + 1}/{retries}): {e}")
            if conn:
                # Si obtuvimos una conexión pero falló antes del yield
                release_db_connection(conn)
                conn = None # Para que no se libere en el finally
            
            if attempt + 1 == retries:
                log.error(f"Error final al obtener conexión del pool después de {retries} intentos.")
                raise # Re-lanza la última excepción
            time.sleep(delay * (2 ** attempt)) # Espera exponencial
        
        except Exception as e:
            log.error(f"Error inesperado en el gestor de contexto de la DB: {e}")
            raise # Re-lanza la excepción
        finally:
            if conn:
                # Esto se ejecuta si el 'yield' fue exitoso
                release_db_connection(conn)

# --- ¡NUEVO! FUNCIONES DE MONITOREO Y CIERRE ---
def check_pool_health():
    """
    Intenta obtener una conexión y ejecutar 'SELECT 1'.
    Devuelve True si tiene éxito, False si falla.
    """
    try:
        with get_db_connection_context() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
        return True
    except Exception as e:
        log.error(f"Fallo en el chequeo de salud del pool: {e}")
        return False

def close_pool():
    """Cierra todas las conexiones en el pool."""
    global db_pool
    if db_pool:
        log.info("Cerrando el pool de conexiones de la base de datos...")
        db_pool.closeall()
        db_pool = None

# ¡NUEVO! Registra la función de cierre para que se ejecute al salir de la app
atexit.register(close_pool)


# --- Inicialización de la Base de Datos ---
# No aplicamos reintento a la inicialización, si esto falla, la app no debe iniciar.
def initialize_database():
    """Crea o actualiza las tablas necesarias en PostgreSQL."""
    try:
        with get_db_connection_context() as conn:
            with conn: # Gestor de transacción (commit/rollback)
                cursor = conn.cursor()
                # ... (código de CREATE TABLE y ALTER TABLE sin cambios) ...
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY, username TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL,
                        full_name TEXT, is_verified BOOLEAN DEFAULT TRUE, session_token VARCHAR(64)
                    );
                ''')
                try: cursor.execute('ALTER TABLE users ADD COLUMN full_name TEXT;')
                except psycopg2.errors.DuplicateColumn: conn.rollback()
                try: cursor.execute('ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT TRUE;')
                except psycopg2.errors.DuplicateColumn: conn.rollback()
                try: cursor.execute('ALTER TABLE users ADD COLUMN session_token VARCHAR(64);')
                except psycopg2.errors.DuplicateColumn: conn.rollback()
                try: cursor.execute('ALTER TABLE users ADD COLUMN credits INTEGER DEFAULT 0;')
                except psycopg2.errors.DuplicateColumn: conn.rollback()
                try: cursor.execute('ALTER TABLE users ADD COLUMN credits_expiry_date TIMESTAMP;')
                except psycopg2.errors.DuplicateColumn: conn.rollback()
                
                conn.commit() # Commit explícito para DDL

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS formulas (
                        id SERIAL PRIMARY KEY, product_name TEXT NOT NULL, description TEXT,
                        creation_date TEXT NOT NULL, user_id INTEGER REFERENCES users(id) ON DELETE CASCADE
                    );
                ''')
                conn.commit()

                try:
                    cursor.execute('ALTER TABLE formulas ADD CONSTRAINT unique_user_product UNIQUE (user_id, product_name);')
                    conn.commit()
                except (psycopg2.errors.DuplicateObject, psycopg2.errors.DuplicateTable):
                    conn.rollback()

                cursor.close()
                log.info("Base de datos PostgreSQL inicializada y actualizada para multi-usuario.")
            
    except Exception as e:
        log.error(f"ERROR: No se pudo inicializar la DB. {e}")


# --- Funciones para Usuarios ---

@retry_on_connection_error()
def add_user(username: str, password: str, full_name: str) -> bool:
    """Añade un nuevo usuario y devuelve su ID, o None si falla."""
    password_hash = generate_password_hash(password)
    initial_credits = 100
    expiry_date = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=3)
    sql = """
        INSERT INTO users (username, password_hash, full_name, is_verified, credits, credits_expiry_date) 
        VALUES (%s, %s, %s, TRUE, %s, %s) RETURNING id
    """
    try:
        with get_db_connection_context() as conn:
            with conn: # Gestor de transacción
                with conn.cursor() as cursor:
                    cursor.execute(sql, (username, password_hash, full_name, initial_credits, expiry_date))
                    new_user_id = cursor.fetchone()[0]
                    return new_user_id
    except psycopg2.IntegrityError:
        log.warning(f"Error de integridad al añadir usuario {username}. Ya existe.")
        return None
    except Exception as e:
        log.error(f"Error inesperado en add_user: {e}")
        return None

@retry_on_connection_error()
def get_user_by_username(username: str) -> dict | None:
    """Busca un usuario por su nombre de usuario (email)."""
    sql = "SELECT * FROM users WHERE username = %s"
    try:
        with get_db_connection_context() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute(sql, (username,))
                user = cursor.fetchone()
                return dict(user) if user else None
    except Exception as e:
        log.error(f"Error en get_user_by_username: {e}")
        return None

@retry_on_connection_error()
def get_user_by_id(user_id: int) -> dict | None:
    """Busca un usuario por su ID."""
    sql = "SELECT * FROM users WHERE id = %s"
    try:
        with get_db_connection_context() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute(sql, (user_id,))
                user = cursor.fetchone()
                return dict(user) if user else None
    except Exception as e:
        log.error(f"Error en get_user_by_id: {e}")
        return None

@retry_on_connection_error()
def verify_user(username: str) -> bool:
    sql = "UPDATE users SET is_verified = TRUE, verification_code = NULL, code_expiry = NULL WHERE username = %s"
    try:
        with get_db_connection_context() as conn:
            with conn: # Gestor de transacción
                with conn.cursor() as cursor:
                    cursor.execute(sql, (username,))
                    return cursor.rowcount > 0
    except Exception as e:
        log.error(f"ERROR al verificar usuario: {e}")
        return False

# --- Funciones para Créditos ---

@retry_on_connection_error()
def get_user_credits(user_id: int) -> int:
    sql = "SELECT credits FROM users WHERE id = %s"
    try:
        with get_db_connection_context() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (user_id,))
                result = cursor.fetchone()
                return result[0] if result and result[0] is not None else 0
    except Exception as e:
        log.error(f"ERROR obteniendo créditos: {e}")
        return 0

@retry_on_connection_error()
def add_user_credits(user_id: int, amount: int) -> bool:
    new_expiry_date = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)
    try:
        with get_db_connection_context() as conn:
            with conn: # Gestor de transacción
                with conn.cursor() as cursor:
                    cursor.execute("SELECT credits FROM users WHERE id = %s", (user_id,))
                    result = cursor.fetchone()
                    current_credits = result[0] if result and result[0] is not None else 0
                    new_total_credits = current_credits + amount
                    cursor.execute(
                        "UPDATE users SET credits = %s, credits_expiry_date = %s WHERE id = %s",
                        (new_total_credits, new_expiry_date, user_id)
                    )
                    return cursor.rowcount > 0
    except Exception as e:
        log.error(f"ERROR añadiendo créditos: {e}")
        return False

@retry_on_connection_error()
def decrement_user_credits(user_id: int, amount: int) -> bool:
    sql = "UPDATE users SET credits = credits - %s WHERE id = %s AND credits >= %s"
    try:
        with get_db_connection_context() as conn:
            with conn: # Gestor de transacción
                with conn.cursor() as cursor:
                    cursor.execute(sql, (amount, user_id, amount))
                    return cursor.rowcount > 0
    except Exception as e:
        log.error(f"ERROR descontando créditos: {e}")
        return False

@retry_on_connection_error()
def check_and_handle_credit_expiration(user_id: int) -> int:
    try:
        with get_db_connection_context() as conn:
            with conn: # Gestor de transacción
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                    cursor.execute("SELECT credits, credits_expiry_date FROM users WHERE id = %s", (user_id,))
                    user = cursor.fetchone()
                    if not user: return 0
                    current_credits = user['credits']
                    expiry_date = user['credits_expiry_date'] 
                    if not expiry_date: return current_credits if current_credits is not None else 0
                    ahora_utc = datetime.datetime.now(datetime.timezone.utc) 
                    if ahora_utc > expiry_date:
                        log.info(f"Créditos expirados para el usuario {user_id}. Reseteando.")
                        cursor.execute("UPDATE users SET credits = 0, credits_expiry_date = NULL WHERE id = %s", (user_id,))
                        return 0 
                    return current_credits if current_credits is not None else 0
    except Exception as e:
        log.error(f"Error manejando la expiración de créditos: {e}")
        return 0

# --- Funciones para Fórmulas ---
@retry_on_connection_error()
def get_all_formulas(user_id: int) -> list[dict]:
    sql = "SELECT id, product_name, creation_date FROM formulas WHERE user_id = %s ORDER BY product_name"
    try:
        with get_db_connection_context() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute(sql, (user_id,))
                formulas = [dict(row) for row in cursor.fetchall()]
                return formulas
    except Exception as e:
        log.error(f"ERROR obteniendo todas las fórmulas: {e}")
        return []

@retry_on_connection_error()
def get_formula_by_id(formula_id: int, user_id: int) -> dict | None:
    sql_formula = "SELECT * FROM formulas WHERE id = %s AND user_id = %s"
    sql_ingredients = """
        SELECT
            fi.id AS formula_ingredient_id, fi.formula_id, fi.ingredient_id,
            fi.quantity, fi.unit, i.name AS ingredient_name, i.protein_percent,
            i.fat_percent, i.water_percent, i.ve_protein_percent, i.notes,
            i.water_retention_factor, i.min_usage_percent, i.max_usage_percent,
            i.precio_por_kg, i.categoria
        FROM formula_ingredients fi
        JOIN user_ingredients i ON fi.ingredient_id = i.id
        WHERE fi.formula_id = %s AND i.user_id = %s
    """
    try:
        with get_db_connection_context() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute(sql_formula, (formula_id, user_id))
                formula_row = cursor.fetchone()
                if not formula_row: return None
                formula_data = dict(formula_row)
                cursor.execute(sql_ingredients, (formula_id, user_id))
                ingredient_rows = cursor.fetchall()
                formula_data['ingredients'] = [dict(row) for row in ingredient_rows]
                return formula_data
    except Exception as e:
        log.error(f"Error en get_formula_by_id: {e}")
        return None

@retry_on_connection_error()
def add_formula(product_name: str, user_id: int, description: str = "") -> int | None:
    creation_date = datetime.datetime.now().isoformat()
    sql = "INSERT INTO formulas (product_name, description, creation_date, user_id) VALUES (%s, %s, %s, %s) RETURNING id"
    try:
        with get_db_connection_context() as conn:
            with conn: # Gestor de transacción
                with conn.cursor() as cursor:
                    cursor.execute(sql, (product_name, description, creation_date, user_id))
                    formula_id = cursor.fetchone()[0]
                    return formula_id
    except psycopg2.IntegrityError:
        log.warning(f"Error de integridad al añadir fórmula. ¿Duplicada? user_id={user_id}, name={product_name}")
        return None
    except Exception as e:
        log.error(f"Error inesperado en add_formula: {e}")
        return None

@retry_on_connection_error()
def delete_formula(formula_id: int, user_id: int) -> bool:
    sql = "DELETE FROM formulas WHERE id = %s AND user_id = %s"
    try:
        with get_db_connection_context() as conn:
            with conn: # Gestor de transacción
                with conn.cursor() as cursor:
                    cursor.execute(sql, (formula_id, user_id))
                    return cursor.rowcount > 0
    except Exception as e:
        log.error(f"ERROR eliminando fórmula: {e}")
        return False

@retry_on_connection_error()
def update_formula_name(formula_id: int, new_name: str, user_id: int) -> bool:
    sql = "UPDATE formulas SET product_name = %s WHERE id = %s AND user_id = %s"
    try:
        with get_db_connection_context() as conn:
            with conn: # Gestor de transacción
                with conn.cursor() as cursor:
                    cursor.execute(sql, (new_name, formula_id, user_id))
                    return cursor.rowcount > 0
    except Exception as e:
        log.error(f"Error actualizando nombre de fórmula: {e}")
        return False

# --- Funciones para Ingredientes en Fórmulas ---

# Helper interno, no necesita reintento por sí mismo
def _get_base_ingredient_data_by_name(cursor, ingredient_name: str) -> dict | None:
    # ... (código sin cambios) ...
    sql = 'SELECT * FROM base_ingredients WHERE name ILIKE %s'
    try:
        cursor.execute(sql, (ingredient_name,))
        result = cursor.fetchone()
        return dict(result) if result else None
    except Exception as e:
        log.error(f"ERROR en _get_base_ingredient_data_by_name: {e}")
        return None

# Helper interno, no necesita reintento por sí mismo
def _get_or_create_user_ingredient_id_by_name(cursor, ingredient_name: str, user_id: int) -> int | None:
    # ... (código sin cambios) ...
    sql_user_select = "SELECT id FROM user_ingredients WHERE name ILIKE %s AND user_id = %s"
    cursor.execute(sql_user_select, (ingredient_name, user_id))
    result_user = cursor.fetchone()
    
    if result_user: return result_user['id']
    
    log.info(f"Ingrediente '{ingredient_name}' no encontrado para user {user_id}. Buscando en la tabla base...")
    base_ingredient_data = _get_base_ingredient_data_by_name(cursor, ingredient_name)
    
    if not base_ingredient_data:
        log.error(f"Error FATAL: Ingrediente '{ingredient_name}' no fue encontrado NI en user_ingredients NI en base_ingredients.")
        return None

    exact_name = base_ingredient_data['name']
    values = (
        exact_name, base_ingredient_data.get('protein_percent'), base_ingredient_data.get('fat_percent'),
        base_ingredient_data.get('water_percent'), base_ingredient_data.get('ve_protein_percent'), 
        base_ingredient_data.get('notes'), base_ingredient_data.get('water_retention_factor'),
        base_ingredient_data.get('min_usage_percent'), base_ingredient_data.get('max_usage_percent'),
        base_ingredient_data.get('precio_por_kg'), base_ingredient_data.get('categoria'), user_id
    )

    try:
        sql_insert_atomic = """
            INSERT INTO user_ingredients (
                name, protein_percent, fat_percent, water_percent, ve_protein_percent,
                notes, water_retention_factor, min_usage_percent, max_usage_percent,
                precio_por_kg, categoria, user_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (name, user_id) DO NOTHING
        """
        cursor.execute(sql_insert_atomic, values)
    except psycopg2.errors.UndefinedColumn:
        log.warning("ADVERTENCIA: Falló 've_protein_percent'. Intentando con 'Ve_Protein_Percent' (mayúscula)...")
        cursor.connection.rollback() # Rollback de la transacción fallida
        values_uc = (
            exact_name, base_ingredient_data.get('protein_percent'), base_ingredient_data.get('fat_percent'),
            base_ingredient_data.get('water_percent'), base_ingredient_data.get('Ve_Protein_Percent'), 
            base_ingredient_data.get('notes'), base_ingredient_data.get('water_retention_factor'),
            base_ingredient_data.get('min_usage_percent'), base_ingredient_data.get('max_usage_percent'),
            base_ingredient_data.get('precio_por_kg'), base_ingredient_data.get('categoria'), user_id
        )
        sql_insert_uppercase_atomic = """
            INSERT INTO user_ingredients (
                name, protein_percent, fat_percent, water_percent, "Ve_Protein_Percent",
                notes, water_retention_factor, min_usage_percent, max_usage_percent,
                precio_por_kg, categoria, user_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (name, user_id) DO NOTHING
        """
        cursor.execute(sql_insert_uppercase_atomic, values_uc)
    except Exception as e:
        log.error(f"ERROR FATAL al copiar ingrediente de base a usuario (atomic): {e}")
        return None

    log.debug(f"Buscando ID final para '{ingredient_name}' después del insert atómico.")
    cursor.execute(sql_user_select, (ingredient_name, user_id))
    result_final = cursor.fetchone()
    
    if result_final:
        return result_final['id']
    else:
        log.error(f"ERROR CRÍTICO: No se encontró el ingrediente '{ingredient_name}' después del INSERT ON CONFLICT.")
        return None

@retry_on_connection_error()
def add_ingredient_to_formula(formula_id: int, ingredient_name: str, quantity: float, unit: str, user_id: int):
    sql = "INSERT INTO formula_ingredients (formula_id, ingredient_id, quantity, unit) VALUES (%s, %s, %s, %s)"
    try:
        with get_db_connection_context() as conn:
            with conn: # Gestor de transacción
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                    ingredient_id = _get_or_create_user_ingredient_id_by_name(cursor, ingredient_name, user_id)
                    if ingredient_id:
                        cursor.execute(sql, (formula_id, ingredient_id, quantity, unit))
                        log.info(f"Ingrediente '{ingredient_name}' (ID: {ingredient_id}) añadido exitosamente a la fórmula {formula_id}.")
                    else:
                        log.error(f"Error FATAL: Ingrediente '{ingredient_name}' no fue encontrado.")
                        raise Exception(f"Ingrediente no encontrado: {ingredient_name}") # Forzar rollback
    except Exception as e:
        log.error(f"ERROR en add_ingredient_to_formula: {e}")

@retry_on_connection_error()
def delete_ingredient(formula_ingredient_id: int):
    sql = "DELETE FROM formula_ingredients WHERE id = %s"
    try:
        with get_db_connection_context() as conn:
            with conn: # Gestor de transacción
                with conn.cursor() as cursor:
                    cursor.execute(sql, (formula_ingredient_id,))
    except Exception as e:
        log.error(f"Error en delete_ingredient: {e}")

@retry_on_connection_error()
def get_formula_id_for_ingredient(formula_ingredient_id: int) -> int | None:
    sql = "SELECT formula_id FROM formula_ingredients WHERE id = %s"
    try:
        with get_db_connection_context() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute(sql, (formula_ingredient_id,))
                result = cursor.fetchone()
                return result['formula_id'] if result else None
    except Exception as e:
        log.error(f"Error en get_formula_id_for_ingredient: {e}")
        return None

@retry_on_connection_error()
def update_ingredient(formula_ingredient_id: int, new_name: str, new_quantity: float, new_unit: str, user_id: int) -> bool:
    sql_update = "UPDATE formula_ingredients SET ingredient_id = %s, quantity = %s, unit = %s WHERE id = %s"
    try:
        with get_db_connection_context() as conn:
            with conn: # Gestor de transacción
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                    new_ingredient_id = _get_or_create_user_ingredient_id_by_name(cursor, new_name, user_id)
                    if not new_ingredient_id:
                        log.error(f"ERROR: No se pudo encontrar o crear el ID para el ingrediente '{new_name}'")
                        return False
                    cursor.execute(sql_update, (new_ingredient_id, new_quantity, new_unit, formula_ingredient_id))
                    return cursor.rowcount > 0 
    except Exception as e:
        log.error(f"ERROR en update_ingredient: {e}")
        return False

# --- Funciones de Ingredientes de Usuario ---
@retry_on_connection_error()
def get_user_ingredients(user_id: int) -> list[dict]:
    sql = "SELECT * FROM user_ingredients WHERE user_id = %s ORDER BY name"
    try:
        with get_db_connection_context() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute(sql, (user_id,))
                results = [dict(row) for row in cursor.fetchall()]
                return results
    except Exception as e:
        log.error(f"Error en get_user_ingredients: {e}")
        return []

@retry_on_connection_error()
def get_master_ingredients() -> list[dict]:
    sql = "SELECT * FROM base_ingredients ORDER BY name"
    results = []
    try:
        with get_db_connection_context() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute(sql)
                for row in cursor.fetchall():
                    results.append(convert_row_to_dict(row))
        return results
    except Exception as e:
        log.error(f"ERROR al consultar base_ingredients en get_master_ingredients: {e}")
        return []

@retry_on_connection_error()
def add_user_ingredient(details: dict, user_id: int) -> int | None:
    sql = """
        INSERT INTO user_ingredients (
            name, protein_percent, fat_percent, water_percent, 
            water_retention_factor, precio_por_kg, categoria, user_id
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
    """
    try:
        with get_db_connection_context() as conn:
            with conn: # Gestor de transacción
                with conn.cursor() as cursor:
                    values = (
                        details.get('name'), details.get('protein_percent'), details.get('fat_percent'),
                        details.get('water_percent'), details.get('water_retention_factor'),
                        details.get('precio_por_kg'), details.get('categoria'), user_id
                    )
                    cursor.execute(sql, values)
                    new_id = cursor.fetchone()[0]
                    return new_id
    except psycopg2.IntegrityError: 
        log.warning(f"Error de integridad al añadir ingrediente de usuario. ¿Duplicado? name={details.get('name')}")
        return None
    except Exception as e:
        log.error(f"Error inesperado en add_user_ingredient: {e}")
        return None

@retry_on_connection_error()
def update_user_ingredient(ingredient_id: int, details: dict, user_id: int) -> bool:
    sql = """
        UPDATE user_ingredients SET 
            name = %s, protein_percent = %s, fat_percent = %s, water_percent = %s, 
            water_retention_factor = %s, precio_por_kg = %s, categoria = %s 
        WHERE id = %s AND user_id = %s
    """
    try:
        with get_db_connection_context() as conn:
            with conn: # Gestor de transacción
                with conn.cursor() as cursor:
                    values = (
                        details.get('name'), details.get('protein_percent'), details.get('fat_percent'),
                        details.get('water_percent'), details.get('water_retention_factor'),
                        details.get('precio_por_kg'), details.get('categoria'),
                        ingredient_id, user_id
                    )
                    cursor.execute(sql, values)
                    return cursor.rowcount > 0
    except psycopg2.IntegrityError:
        log.warning(f"Error de integridad al actualizar ingrediente de usuario. ¿Nombre duplicado? id={ingredient_id}")
        return False
    except Exception as e:
        log.error(f"Error inesperado en update_user_ingredient: {e}")
        return False

@retry_on_connection_error()
def delete_user_ingredient(ingredient_id: int, user_id: int) -> str:
    sql = "DELETE FROM user_ingredients WHERE id = %s AND user_id = %s"
    try:
        with get_db_connection_context() as conn:
            with conn: # Gestor de transacción
                with conn.cursor() as cursor:
                    cursor.execute(sql, (ingredient_id, user_id))
                    return 'success' if cursor.rowcount > 0 else 'not_found'
    except psycopg2.IntegrityError: 
        log.warning(f"No se pudo eliminar ingrediente {ingredient_id}, está en uso.")
        return 'in_use'
    except Exception as e:
        log.error(f"Error inesperado en delete_user_ingredient: {e}")
        return 'error'

@retry_on_connection_error()
def search_user_ingredient_names(query: str, user_id: int) -> list[str]:
    sql = "SELECT name FROM user_ingredients WHERE name ILIKE %s AND user_id = %s ORDER BY name LIMIT 10"
    search_term = f"%{query}%"
    try:
        with get_db_connection_context() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (search_term, user_id))
                results = [row[0] for row in cursor.fetchall()]
                return results
    except Exception as e:
        log.error(f"Error en search_user_ingredient_names: {e}")
        return []

@retry_on_connection_error()
def search_base_ingredient_names(query: str) -> list[str]:
    sql = "SELECT name FROM base_ingredients WHERE name ILIKE %s ORDER BY name LIMIT 10"
    search_term = f"%{query}%"
    try:
        with get_db_connection_context() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (search_term,))
                results = [row[0] for row in cursor.fetchall()]
                return results
    except Exception as e:
        log.error(f"ERROR en search_base_ingredient_names: {e}")
        return []
        
# --- Funciones de Bibliografía ---
@retry_on_connection_error()
def get_all_bibliografia() -> list[dict]:
    sql = "SELECT * FROM bibliografia ORDER BY titulo"
    try:
        with get_db_connection_context() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute(sql)
                results = [dict(row) for row in cursor.fetchall()]
                return results
    except Exception as e:
        log.error(f"Error en get_all_bibliografia: {e}")
        return []

@retry_on_connection_error()
def add_bibliografia_entry(titulo: str, tipo: str, contenido: str) -> int | None:
    sql = "INSERT INTO bibliografia (titulo, tipo, contenido) VALUES (%s, %s, %s) RETURNING id"
    try:
        with get_db_connection_context() as conn:
            with conn: # Gestor de transacción
                with conn.cursor() as cursor:
                    cursor.execute(sql, (titulo, tipo, contenido))
                    new_id = cursor.fetchone()[0]
                    return new_id
    except Exception as e:
        log.error(f"Error en add_bibliografia_entry: {e}")
        return None

@retry_on_connection_error()
def update_bibliografia_entry(entry_id: int, titulo: str, tipo: str, contenido: str) -> bool:
    sql = "UPDATE bibliografia SET titulo = %s, tipo = %s, contenido = %s WHERE id = %s"
    try:
        with get_db_connection_context() as conn:
            with conn: # Gestor de transacción
                with conn.cursor() as cursor:
                    cursor.execute(sql, (titulo, tipo, contenido, entry_id))
                    return cursor.rowcount > 0
    except Exception as e:
        log.error(f"Error en update_bibliografia_entry: {e}")
        return False

@retry_on_connection_error()
def delete_bibliografia_entry(entry_id: int) -> bool:
    sql = "DELETE FROM bibliografia WHERE id = %s"
    try:
        with get_db_connection_context() as conn:
            with conn: # Gestor de transacción
                with conn.cursor() as cursor:
                    cursor.execute(sql, (entry_id,))
                    return cursor.rowcount > 0
    except Exception as e:
        log.error(f"Error en delete_bibliografia_entry: {e}")
        return False

import re # Asegúrate de tener 'import re' al principio de tu database.py

def search_bibliografia(query, max_results=5):
    """
    Busca en la bibliografía títulos o contenidos que coincidan con la consulta.
    Esta versión es más inteligente:
    1. Limpia la consulta (saca palabras comunes).
    2. Califica los resultados basándose en cuántas palabras clave coinciden.
    3. Devuelve los resultados con mayor puntuación (más relevantes).
    """
    
    # 1. Definir "palabras vacías" (palabras comunes que no aportan a la búsqueda)
    PALABRAS_VACIAS = set([
        'a', 'al', 'con', 'de', 'del', 'dame', 'como', 'cual', 'el', 'ella', 'ellos', 'en', 
        'es', 'esta', 'este', 'para', 'por', 'que', 'quien', 'la', 'las', 'le', 'lo', 
        'los', 'mas', 'me', 'mi', 'o', 'pero', 'se', 'si', 'su', 'tu', 'un', 'una', 
        'uno', 'y', 'ya', 'valor', 'optimo', 'sobre', 'dime', 'info', 'informacion'
    ])

    # 2. Limpiar la consulta y extraer palabras clave
    # 're.sub' quita puntuación, 'lower()' la hace minúscula
    texto_limpio = re.sub(r'[^\w\s]', '', query.lower())
    # 'split()' la divide en palabras
    palabras = texto_limpio.split()
    
    # Filtramos las palabras vacías, nos quedamos solo con las clave
    terminos_clave = [palabra for palabra in palabras if palabra not in PALABRAS_VACIAS and len(palabra) > 2]
    
    if not terminos_clave:
        # Si la consulta solo tenía palabras vacías, devolvemos nada
        return []

    # 3. Construir una consulta SQL dinámica que califica por relevancia
    conn = None
    try:
        conn = get_db_connection()
        
        # 'score_parts' tendrá: "(CASE WHEN (titulo LIKE ? OR contenido LIKE ?) THEN 1 ELSE 0 END)"
        # por cada palabra clave.
        score_parts = []
        params = []
        
        for term in terminos_clave:
            term_like = f"%{term}%"
            score_parts.append("(CASE WHEN (titulo LIKE ? OR contenido LIKE ?) THEN 1 ELSE 0 END)")
            params.append(term_like)
            params.append(term_like)

        # Construimos la consulta final
        # 1. Sumamos todos los 'CASE' para obtener un 'score' (puntuación)
        # 2. Seleccionamos solo los que tienen score > 0 (al menos 1 coincidencia)
        # 3. Ordenamos por score DESC (los más relevantes primero)
        # 4. Limitamos los resultados
        
        query_sql = f"""
            SELECT titulo, tipo, contenido, ({" + ".join(score_parts)}) AS score
            FROM bibliografia
            WHERE score > 0
            ORDER BY score DESC
            LIMIT ?
        """
        
        # Añadimos el 'LIMIT' a la lista de parámetros
        params.append(max_results)
        
        # Ejecutamos la consulta
        results = conn.execute(query_sql, tuple(params)).fetchall()
        
        # Devolvemos los resultados como diccionarios
        return [dict(row) for row in results]

    except Exception as e:
        print(f"ERROR en search_bibliografia (versión avanzada): {e}")
        return []
    finally:
        if conn:
            conn.close()

# --- Funciones de Sesión ---
@retry_on_connection_error()
def update_session_token(user_id, token):
    sql = "UPDATE users SET session_token = %s WHERE id = %s"
    try:
        with get_db_connection_context() as conn:
            with conn: # Gestor de transacción
                with conn.cursor() as cursor:
                    cursor.execute(sql, (token, user_id))
                    return True
    except Exception as e:
        log.error(f"Error updating session token: {e}")
        return False

@retry_on_connection_error()
def get_session_token_for_user(user_id):
    sql = "SELECT session_token FROM users WHERE id = %s"
    try:
        with get_db_connection_context() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute(sql, (user_id,))
                result = cursor.fetchone()
                token = result['session_token'] if result else None
                return token
    except Exception as e:
        log.error(f"Error getting session token: {e}")
        return None

@retry_on_connection_error()
def seed_initial_ingredients(user_id):
    """
    Copia todos los ingredientes de 'base_ingredients' a 'user_ingredients'
    para un nuevo usuario. Maneja fallbacks de nombres de columnas.
    """
    try:
        with get_db_connection_context() as conn:
            # ¡MODIFICADO! Usamos 'with conn' para la transacción principal
            with conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                    
                    cursor.execute("SELECT * FROM base_ingredients")
                    base_ingredients = cursor.fetchall()
                    if not base_ingredients:
                        log.warning(f"No se encontraron ingredientes base para copiar al usuario {user_id}")
                        return True 

                    user_ingredients_to_insert = []
                    for ingredient in base_ingredients:
                        ve_protein_val = ingredient.get('Ve_Protein_Percent', ingredient.get('ve_protein_percent'))
                        user_ingredients_to_insert.append((
                            ingredient['name'], ingredient['protein_percent'], ingredient['fat_percent'],
                            ingredient['water_percent'], ve_protein_val, ingredient['notes'],
                            ingredient['water_retention_factor'], ingredient['min_usage_percent'],
                            ingredient['max_usage_percent'], ingredient['precio_por_kg'],
                            ingredient['categoria'], user_id
                        ))

                    if user_ingredients_to_insert:
                        sql_insert = """
                            INSERT INTO user_ingredients (
                                name, protein_percent, fat_percent, water_percent, ve_protein_percent,
                                notes, water_retention_factor, min_usage_percent, max_usage_percent,
                                precio_por_kg, categoria, user_id
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        try:
                            cursor.executemany(sql_insert, user_ingredients_to_insert)
                            # El commit será automático al salir del 'with conn'
                        except psycopg2.errors.UndefinedColumn:
                            log.warning("ADVERTENCIA: Falló 've_protein_percent'. Intentando con 'Ve_Protein_Percent'...")
                            # El 'with conn' hará rollback automático de la transacción fallida
                            
                            # ¡MODIFICADO! Re-lanzamos la excepción para que el 'with conn'
                            # haga rollback, y luego la capturamos afuera para reintentar.
                            raise
        
    except psycopg2.errors.UndefinedColumn:
        # El primer intento (minúscula) falló y se hizo rollback.
        # Ahora reintentamos con la columna en mayúscula en una NUEVA transacción.
        log.info("Reintentando seed_initial_ingredients con 'Ve_Protein_Percent' (mayúscula)...")
        try:
            with get_db_connection_context() as conn:
                with conn: # Nueva transacción
                    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as fallback_cursor:
                        
                        # Volvemos a obtener los datos (necesario para la lista)
                        fallback_cursor.execute("SELECT * FROM base_ingredients")
                        base_ingredients_fb = fallback_cursor.fetchall()
                        if not base_ingredients_fb: return True
                        
                        user_ingredients_to_insert_fb = []
                        for ingredient in base_ingredients_fb:
                            ve_protein_val = ingredient.get('Ve_Protein_Percent', ingredient.get('ve_protein_percent'))
                            user_ingredients_to_insert_fb.append((
                                ingredient['name'], ingredient['protein_percent'], ingredient['fat_percent'],
                                ingredient['water_percent'], ve_protein_val, ingredient['notes'],
                                ingredient['water_retention_factor'], ingredient['min_usage_percent'],
                                ingredient['max_usage_percent'], ingredient['precio_por_kg'],
                                ingredient['categoria'], user_id
                            ))

                        sql_uppercase = """
                            INSERT INTO user_ingredients (
                                name, protein_percent, fat_percent, water_percent, "Ve_Protein_Percent",
                                notes, water_retention_factor, min_usage_percent, max_usage_percent,
                                precio_por_kg, categoria, user_id
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        fallback_cursor.executemany(sql_uppercase, user_ingredients_to_insert_fb)
                        # Commit automático del 'with conn'
                        log.info("Seed exitoso con 'Ve_Protein_Percent'.")
                        return True
        except Exception as e_fb:
            log.error(f"Error en el reintento de seed_initial_ingredients (fallback): {e_fb}")
            return False
            
    except Exception as e:
        log.error(f"Error general en seed_initial_ingredients: {e}")
        return False