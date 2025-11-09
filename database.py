import os
import psycopg2
import psycopg2.extras
import psycopg2.pool
import datetime
import decimal
import logging # ¡NUEVA IMPORTACIÓN!
from contextlib import contextmanager # ¡NUEVA IMPORTACIÓN!
from werkzeug.security import generate_password_hash, check_password_hash

# --- Configuración de Logging ---
# Reemplaza todos los 'print()' por un logger profesional.
# El nivel de log se puede controlar con una variable de entorno.
logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO').upper(), 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

def convert_row_to_dict(row):
    """
    Convierte una fila (p. ej. psycopg2.extras.DictRow) a un dict normalizando tipos:
    - decimal.Decimal -> int (si es entero) o float
    - datetime.datetime -> ISO string
    - deja otros tipos tal cual
    """
    # ... (código sin cambios) ...
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
log.info(f"Conectando a la URL de la base de datos: {DATABASE_URL[:30]}...") # Ocultamos la info sensible

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
    """
    global db_pool
    if db_pool is None:
        log.error("El pool de conexiones no está inicializado. Intentando recrear...")
        try:
            db_pool = psycopg2.pool.SimpleConnectionPool(1, 10, dsn=DATABASE_URL)
            log.info("Pool de conexiones recreado exitosamente.")
        except Exception as e:
            log.error(f"ERROR CRÍTICO: No se pudo recrear el pool de conexiones. {e}")
            return None
            
    try:
        conn = db_pool.getconn()
        log.debug("Conexión obtenida del pool.")
        return conn
    except Exception as e:
        log.error(f"ERROR: No se pudo obtener conexión del pool. {e}")
        return None

def release_db_connection(conn):
    """
    Devuelve una conexión al POOL.
    """
    global db_pool
    if db_pool and conn:
        log.debug("Devolviendo conexión al pool.")
        db_pool.putconn(conn)

# --- ¡NUEVO! GESTOR DE CONTEXTO ---
@contextmanager
def get_db_connection_context():
    """
    Gestor de contexto para obtener y liberar una conexión del pool.
    Esto reemplaza la necesidad de try/finally y release_db_connection() en cada función.
    """
    conn = None
    try:
        conn = get_db_connection()
        if conn is None:
            raise psycopg2.OperationalError("No se pudo obtener una conexión del pool de la base de datos.")
        
        yield conn # Proporciona la conexión al bloque 'with'
        
    except Exception as e:
        log.error(f"Error en el gestor de contexto de la DB: {e}")
        # La excepción se propaga, el 'with conn.cursor()' de abajo hará rollback.
        raise # Re-lanza la excepción
    finally:
        if conn:
            # Esto se ejecuta siempre, haya error o no.
            release_db_connection(conn)

# --- FIN DE CAMBIOS EN EL POOL/CONTEXTO ---


# --- Inicialización de la Base de Datos ---
def initialize_database():
    """Crea o actualiza las tablas necesarias en PostgreSQL."""
    try:
        with get_db_connection_context() as conn:
            # Usamos un cursor normal aquí porque DDL (CREATE TABLE)
            # a veces requiere manejo explícito de la transacción.
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

            cursor.close()
            log.info("Base de datos PostgreSQL inicializada y actualizada para multi-usuario.")
            
    except Exception as e:
        log.error(f"ERROR: No se pudo inicializar la DB. {e}")


# --- Funciones para Usuarios ---

def add_user(username: str, password: str, full_name: str, verification_code: str = None, code_expiry: datetime = None) -> bool:
    """Añade un nuevo usuario y devuelve su ID, o None si falla."""
    password_hash = generate_password_hash(password)
    initial_credits = 100
    expiry_date = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=3)

    sql = """
        INSERT INTO users (username, password_hash, full_name, verification_code, code_expiry, credits, credits_expiry_date) 
        VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
    """
    
    try:
        # ¡NUEVO PATRÓN! 'with' anidados.
        # El 'with conn.cursor()' exterior maneja commit/rollback.
        # El 'with get_db_connection_context()' interior maneja obtener/liberar la conexión.
        with get_db_connection_context() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    sql,
                    (username, password_hash, full_name, verification_code, code_expiry, initial_credits, expiry_date)
                )
                new_user_id = cursor.fetchone()[0]
                # El commit es automático al salir del 'with cursor' sin errores
                return new_user_id
    except psycopg2.IntegrityError:
        log.warning(f"Error de integridad al añadir usuario {username}. Ya existe.")
        # El rollback es automático al salir del 'with cursor' con una excepción
        return None
    except Exception as e:
        log.error(f"Error inesperado en add_user: {e}")
        return None

def get_user_by_username(username: str) -> dict | None:
    """
    Busca un usuario por su nombre de usuario (email).
    Devuelve los datos del usuario o None si no se encuentra.
    """
    sql = "SELECT * FROM users WHERE username = %s"
    try:
        with get_db_connection_context() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute(sql, (username,))
                user = cursor.fetchone()
                # No se necesita commit/rollback para un SELECT
                return dict(user) if user else None
    except Exception as e:
        log.error(f"Error en get_user_by_username: {e}")
        return None

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

def verify_user(username: str) -> bool:
    """Marca a un usuario como verificado y limpia los datos de verificación."""
    sql = "UPDATE users SET is_verified = TRUE, verification_code = NULL, code_expiry = NULL WHERE username = %s"
    try:
        with get_db_connection_context() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (username,))
                # Commit automático
                return cursor.rowcount > 0
    except Exception as e:
        log.error(f"ERROR al verificar usuario: {e}")
        # Rollback automático
        return False

# --- Funciones para Créditos ---

def get_user_credits(user_id: int) -> int:
    """Obtiene los créditos de un usuario."""
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

def add_user_credits(user_id: int, amount: int) -> bool:
    """Añade créditos a un usuario y extiende su expiración por 30 días."""
    new_expiry_date = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)
    
    try:
        with get_db_connection_context() as conn:
            with conn.cursor() as cursor:
                # Primero, obtenemos los créditos actuales
                cursor.execute("SELECT credits FROM users WHERE id = %s", (user_id,))
                result = cursor.fetchone()
                current_credits = result[0] if result and result[0] is not None else 0
                
                new_total_credits = current_credits + amount
                
                # Actualizamos
                cursor.execute(
                    "UPDATE users SET credits = %s, credits_expiry_date = %s WHERE id = %s",
                    (new_total_credits, new_expiry_date, user_id)
                )
                # Commit automático
                return cursor.rowcount > 0
    except Exception as e:
        log.error(f"ERROR añadiendo créditos: {e}")
        # Rollback automático
        return False

def decrement_user_credits(user_id: int, amount: int) -> bool:
    """Descuenta créditos de un usuario si tiene suficientes."""
    sql = "UPDATE users SET credits = credits - %s WHERE id = %s AND credits >= %s"
    try:
        with get_db_connection_context() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (amount, user_id, amount))
                # Commit automático
                return cursor.rowcount > 0
    except Exception as e:
        log.error(f"ERROR descontando créditos: {e}")
        # Rollback automático
        return False

def check_and_handle_credit_expiration(user_id: int) -> int:
    """Verifica la expiración de créditos y los resetea si es necesario."""
    try:
        with get_db_connection_context() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute("SELECT credits, credits_expiry_date FROM users WHERE id = %s", (user_id,))
                user = cursor.fetchone()
                if not user:
                    return 0

                current_credits = user['credits']
                expiry_date = user['credits_expiry_date'] 

                if not expiry_date:
                    return current_credits if current_credits is not None else 0

                ahora_utc = datetime.datetime.now(datetime.timezone.utc) 

                if ahora_utc > expiry_date:
                    log.info(f"Créditos expirados para el usuario {user_id}. Reseteando.")
                    cursor.execute("UPDATE users SET credits = 0, credits_expiry_date = NULL WHERE id = %s", (user_id,))
                    # Commit automático
                    return 0 

                return current_credits if current_credits is not None else 0
    except Exception as e:
        log.error(f"Error manejando la expiración de créditos: {e}")
        # Rollback automático (si hubo un UPDATE)
        return 0

# --- Funciones para Fórmulas ---
def get_all_formulas(user_id: int) -> list[dict]:
    """Obtiene lista simple de todas las fórmulas para un usuario específico."""
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
                if not formula_row:
                    return None

                formula_data = dict(formula_row)
                formula_data['ingredients'] = []

                cursor.execute(sql_ingredients, (formula_id, user_id))
                ingredient_rows = cursor.fetchall()
                formula_data['ingredients'] = [dict(row) for row in ingredient_rows]
                return formula_data
    except Exception as e:
        log.error(f"Error en get_formula_by_id: {e}")
        return None

def add_formula(product_name: str, user_id: int, description: str = "") -> int | None:
    creation_date = datetime.datetime.now().isoformat()
    sql = "INSERT INTO formulas (product_name, description, creation_date, user_id) VALUES (%s, %s, %s, %s) RETURNING id"
    try:
        with get_db_connection_context() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (product_name, description, creation_date, user_id))
                formula_id = cursor.fetchone()[0]
                # Commit automático
                return formula_id
    except psycopg2.IntegrityError:
        log.warning(f"Error de integridad al añadir fórmula. ¿Duplicada? user_id={user_id}, name={product_name}")
        # Rollback automático
        return None
    except Exception as e:
        log.error(f"Error inesperado en add_formula: {e}")
        return None

def delete_formula(formula_id: int, user_id: int) -> bool:
    sql = "DELETE FROM formulas WHERE id = %s AND user_id = %s"
    try:
        with get_db_connection_context() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (formula_id, user_id))
                # Commit automático
                return cursor.rowcount > 0
    except Exception as e:
        log.error(f"ERROR eliminando fórmula: {e}")
        # Rollback automático
        return False

def update_formula_name(formula_id: int, new_name: str, user_id: int) -> bool:
    """Actualiza el nombre de una fórmula específica."""
    sql = "UPDATE formulas SET product_name = %s WHERE id = %s AND user_id = %s"
    try:
        with get_db_connection_context() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (new_name, formula_id, user_id))
                # Commit automático
                return cursor.rowcount > 0
    except Exception as e:
        log.error(f"Error actualizando nombre de fórmula: {e}")
        # Rollback automático
        return False

# --- Funciones para Ingredientes en Fórmulas ---

# Esta es una función "helper" interna.
# NO abre/cierra conexiones, sino que reutiliza el cursor que se le pasa.
def _get_base_ingredient_data_by_name(cursor, ingredient_name: str) -> dict | None:
    """Obtiene los datos completos de un ingrediente de la tabla base (case-insensitive)."""
    sql = 'SELECT * FROM base_ingredients WHERE name ILIKE %s'
    try:
        cursor.execute(sql, (ingredient_name,))
        result = cursor.fetchone()
        return dict(result) if result else None
    except Exception as e:
        log.error(f"ERROR en _get_base_ingredient_data_by_name: {e}")
        return None

# --- ¡MODIFICADO! LÓGICA ATÓMICA PARA PREVENIR RACE CONDITIONS ---
def _get_or_create_user_ingredient_id_by_name(cursor, ingredient_name: str, user_id: int) -> int | None:
    """
    Busca el ID de un ingrediente en la lista del usuario ('user_ingredients') usando ILIKE.
    Si no existe, lo busca en 'base_ingredients' (ILIKE).
    Si existe en la base, lo copia a 'user_ingredients' de forma atómica usando
    INSERT ... ON CONFLICT y devuelve el ID.
    
    IMPORTANTE: Esta función es un helper, asume que ya está dentro de una
    transacción y reutiliza el cursor proporcionado.
    """
    
    # 1. Buscar en la lista de ingredientes del usuario (case-insensitive)
    sql_user_select = "SELECT id FROM user_ingredients WHERE name ILIKE %s AND user_id = %s"
    cursor.execute(sql_user_select, (ingredient_name, user_id))
    result_user = cursor.fetchone()
    
    if result_user:
        return result_user['id']
    
    # 2. No encontrado. Buscar en la lista de ingredientes base (case-insensitive).
    log.info(f"Ingrediente '{ingredient_name}' no encontrado para user {user_id}. Buscando en la tabla base...")
    base_ingredient_data = _get_base_ingredient_data_by_name(cursor, ingredient_name)
    
    if not base_ingredient_data:
        # Ingrediente no existe en ningún lado
        log.error(f"Error FATAL: Ingrediente '{ingredient_name}' no fue encontrado NI en user_ingredients NI en base_ingredients.")
        return None

    # 3. Encontrado en la base. Copiarlo a 'user_ingredients' usando INSERT... ON CONFLICT.
    # Usamos el nombre *exacto* de la tabla base para la inserción.
    exact_name = base_ingredient_data['name']
    
    # Preparamos los valores
    values = (
        exact_name, # Usamos el nombre exacto
        base_ingredient_data.get('protein_percent'),
        base_ingredient_data.get('fat_percent'),
        base_ingredient_data.get('water_percent'),
        base_ingredient_data.get('ve_protein_percent'), # Intentamos con minúscula
        base_ingredient_data.get('notes'),
        base_ingredient_data.get('water_retention_factor'),
        base_ingredient_data.get('min_usage_percent'),
        base_ingredient_data.get('max_usage_percent'),
        base_ingredient_data.get('precio_por_kg'),
        base_ingredient_data.get('categoria'),
        user_id
    )

    try:
        # Intentamos insertar con la columna 've_protein_percent' (minúscula)
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
        # El cursor ya está en estado de error, la transacción se abortará.
        # El 'with cursor' de la función que nos llamó hará rollback.
        # Debemos hacer rollback aquí para poder re-intentar.
        cursor.connection.rollback() # Hacemos rollback de la transacción fallida
        
        # Re-preparamos los valores para el fallback
        values_uc = (
            exact_name,
            base_ingredient_data.get('protein_percent'),
            base_ingredient_data.get('fat_percent'),
            base_ingredient_data.get('water_percent'),
            base_ingredient_data.get('Ve_Protein_Percent'), # Usamos mayúscula
            base_ingredient_data.get('notes'),
            base_ingredient_data.get('water_retention_factor'),
            base_ingredient_data.get('min_usage_percent'),
            base_ingredient_data.get('max_usage_percent'),
            base_ingredient_data.get('precio_por_kg'),
            base_ingredient_data.get('categoria'),
            user_id
        )
        
        # Intentamos insertar con la columna "Ve_Protein_Percent" (mayúscula)
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
        # El rollback será automático
        return None

    # 4. En este punto, el ingrediente DEBE existir.
    # (ya sea porque estaba, lo insertamos nosotros, o lo insertó otra petición)
    # Lo volvemos a buscar para obtener el ID de forma segura.
    log.debug(f"Buscando ID final para '{ingredient_name}' después del insert atómico.")
    cursor.execute(sql_user_select, (ingredient_name, user_id))
    result_final = cursor.fetchone()
    
    if result_final:
        return result_final['id']
    else:
        # Esto no debería ocurrir
        log.error(f"ERROR CRÍTICO: No se encontró el ingrediente '{ingredient_name}' después del INSERT ON CONFLICT.")
        return None
# --- FIN DE LA MODIFICACIÓN ATÓMICA ---

def add_ingredient_to_formula(formula_id: int, ingredient_name: str, quantity: float, unit: str, user_id: int):
    """Añade un ingrediente a una fórmula."""
    sql = "INSERT INTO formula_ingredients (formula_id, ingredient_id, quantity, unit) VALUES (%s, %s, %s, %s)"
    try:
        with get_db_connection_context() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                
                ingredient_id = _get_or_create_user_ingredient_id_by_name(cursor, ingredient_name, user_id)
                
                if ingredient_id:
                    cursor.execute(sql, (formula_id, ingredient_id, quantity, unit))
                    # ¡LIMPIADO! Commit/Rollback es automático por el 'with cursor'.
                    log.info(f"Ingrediente '{ingredient_name}' (ID: {ingredient_id}) añadido exitosamente a la fórmula {formula_id}.")
                else:
                    log.error(f"Error FATAL: Ingrediente '{ingredient_name}' no fue encontrado NI en user_ingredients NI en base_ingredients.")
                    # El 'with cursor' hará rollback automático
    except Exception as e:
        log.error(f"ERROR en add_ingredient_to_formula: {e}")
        # Rollback automático

def delete_ingredient(formula_ingredient_id: int):
    sql = "DELETE FROM formula_ingredients WHERE id = %s"
    try:
        with get_db_connection_context() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (formula_ingredient_id,))
                # Commit automático
    except Exception as e:
        log.error(f"Error en delete_ingredient: {e}")
        # Rollback automático

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

def update_ingredient(formula_ingredient_id: int, new_name: str, new_quantity: float, new_unit: str, user_id: int) -> bool:
    """Actualiza un ingrediente dentro de una fórmula."""
    sql_update = "UPDATE formula_ingredients SET ingredient_id = %s, quantity = %s, unit = %s WHERE id = %s"
    try:
        with get_db_connection_context() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                
                new_ingredient_id = _get_or_create_user_ingredient_id_by_name(cursor, new_name, user_id)

                if not new_ingredient_id:
                    log.error(f"ERROR: No se pudo encontrar o crear el ID para el ingrediente '{new_name}'")
                    # Rollback automático
                    return False

                cursor.execute(sql_update, (new_ingredient_id, new_quantity, new_unit, formula_ingredient_id))
                # ¡LIMPIADO! Commit/Rollback es automático por el 'with cursor'.
                return cursor.rowcount > 0 
    except Exception as e:
        log.error(f"ERROR en update_ingredient: {e}")
        # Rollback automático
        return False

# --- Funciones de Ingredientes de Usuario ---
def get_user_ingredients(user_id: int) -> list[dict]:
    """Obtiene todos los ingredientes para un usuario específico."""
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

def get_master_ingredients() -> list[dict]:
    """Obtiene SÓLO los ingredientes MAESTROS (de la tabla base)."""
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


def add_user_ingredient(details: dict, user_id: int) -> int | None:
    """Añade un nuevo ingrediente a la colección de un usuario."""
    sql = """
        INSERT INTO user_ingredients (
            name, protein_percent, fat_percent, water_percent, 
            water_retention_factor, precio_por_kg, categoria, user_id
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
    """
    try:
        with get_db_connection_context() as conn:
            with conn.cursor() as cursor:
                values = (
                    details.get('name'),
                    details.get('protein_percent'),
                    details.get('fat_percent'),
                    details.get('water_percent'),
                    details.get('water_retention_factor'),
                    details.get('precio_por_kg'),
                    details.get('categoria'),
                    user_id
                )
                cursor.execute(sql, values)
                new_id = cursor.fetchone()[0]
                # Commit automático
                return new_id
    except psycopg2.IntegrityError: 
        log.warning(f"Error de integridad al añadir ingrediente de usuario. ¿Duplicado? name={details.get('name')}")
        # Rollback automático
        return None
    except Exception as e:
        log.error(f"Error inesperado en add_user_ingredient: {e}")
        return None

def update_user_ingredient(ingredient_id: int, details: dict, user_id: int) -> bool:
    """Actualiza un ingrediente específico de un usuario."""
    sql = """
        UPDATE user_ingredients SET 
            name = %s, protein_percent = %s, fat_percent = %s, water_percent = %s, 
            water_retention_factor = %s, precio_por_kg = %s, categoria = %s 
        WHERE id = %s AND user_id = %s
    """
    try:
        with get_db_connection_context() as conn:
            with conn.cursor() as cursor:
                values = (
                    details.get('name'),
                    details.get('protein_percent'),
                    details.get('fat_percent'),
                    details.get('water_percent'),
                    details.get('water_retention_factor'),
                    details.get('precio_por_kg'),
                    details.get('categoria'),
                    ingredient_id,
                    user_id
                )
                cursor.execute(sql, values)
                # Commit automático
                return cursor.rowcount > 0
    except psycopg2.IntegrityError:
        log.warning(f"Error de integridad al actualizar ingrediente de usuario. ¿Nombre duplicado? id={ingredient_id}")
        # Rollback automático
        return False
    except Exception as e:
        log.error(f"Error inesperado en update_user_ingredient: {e}")
        return False

def delete_user_ingredient(ingredient_id: int, user_id: int) -> str:
    """Elimina un ingrediente de un usuario, si no está en uso."""
    sql = "DELETE FROM user_ingredients WHERE id = %s AND user_id = %s"
    try:
        with get_db_connection_context() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (ingredient_id, user_id))
                # Commit automático
                return 'success' if cursor.rowcount > 0 else 'not_found'
    except psycopg2.IntegrityError: 
        log.warning(f"No se pudo eliminar ingrediente {ingredient_id}, está en uso.")
        # Rollback automático
        return 'in_use'
    except Exception as e:
        log.error(f"Error inesperado en delete_user_ingredient: {e}")
        return 'error'

def search_user_ingredient_names(query: str, user_id: int) -> list[str]:
    """Busca nombres de ingredientes para un usuario específico."""
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

def search_base_ingredient_names(query: str) -> list[str]:
    """Busca nombres de ingredientes en la tabla base (base_ingredients)."""
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

def add_bibliografia_entry(titulo: str, tipo: str, contenido: str) -> int | None:
    sql = "INSERT INTO bibliografia (titulo, tipo, contenido) VALUES (%s, %s, %s) RETURNING id"
    try:
        with get_db_connection_context() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (titulo, tipo, contenido))
                new_id = cursor.fetchone()[0]
                # Commit automático
                return new_id
    except Exception as e:
        log.error(f"Error en add_bibliografia_entry: {e}")
        # Rollback automático
        return None

def update_bibliografia_entry(entry_id: int, titulo: str, tipo: str, contenido: str) -> bool:
    sql = "UPDATE bibliografia SET titulo = %s, tipo = %s, contenido = %s WHERE id = %s"
    try:
        with get_db_connection_context() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (titulo, tipo, contenido, entry_id))
                # Commit automático
                return cursor.rowcount > 0
    except Exception as e:
        log.error(f"Error en update_bibliografia_entry: {e}")
        # Rollback automático
        return False

def delete_bibliografia_entry(entry_id: int) -> bool:
    sql = "DELETE FROM bibliografia WHERE id = %s"
    try:
        with get_db_connection_context() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (entry_id,))
                # Commit automático
                return cursor.rowcount > 0
    except Exception as e:
        log.error(f"Error en delete_bibliografia_entry: {e}")
        # Rollback automático
        return False

# --- Funciones de Sesión ---
def update_session_token(user_id, token):
    """Actualiza el token de sesión de un usuario en la base de datos."""
    sql = "UPDATE users SET session_token = %s WHERE id = %s"
    try:
        with get_db_connection_context() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (token, user_id))
                # Commit automático
                return True
    except Exception as e:
        log.error(f"Error updating session token: {e}")
        # Rollback automático
        return False

def get_session_token_for_user(user_id):
    """Obtiene el token de sesión actual de un usuario desde la base de datos."""
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

def seed_initial_ingredients(user_id):
    """
    Copia todos los ingredientes de 'base_ingredients' a 'user_ingredients'
    para un nuevo usuario.
    """
    try:
        with get_db_connection_context() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                
                cursor.execute("SELECT * FROM base_ingredients")
                base_ingredients = cursor.fetchall()
                if not base_ingredients:
                    log.warning(f"No se encontraron ingredientes base para copiar al usuario {user_id}")
                    return True # No es un error, solo no hay nada que copiar

                user_ingredients_to_insert = []
                for ingredient in base_ingredients:
                    ve_protein_val = ingredient.get('Ve_Protein_Percent', ingredient.get('ve_protein_percent'))

                    user_ingredients_to_insert.append((
                        ingredient['name'],
                        ingredient['protein_percent'],
                        ingredient['fat_percent'],
                        ingredient['water_percent'],
                        ve_protein_val,
                        ingredient['notes'],
                        ingredient['water_retention_factor'],
                        ingredient['min_usage_percent'],
                        ingredient['max_usage_percent'],
                        ingredient['precio_por_kg'],
                        ingredient['categoria'],
                        user_id
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
                    except psycopg2.errors.UndefinedColumn:
                        log.warning("ADVERTENCIA: Falló 've_protein_percent'. Intentando con 'Ve_Protein_Percent'...")
                        # El rollback es automático por la excepción
                        
                        # ¡IMPORTANTE! El 'with cursor' ya hizo rollback,
                        # pero la conexión (conn) sigue abierta. Necesitamos
                        # un commit explícito si la siguiente operación tiene éxito.
                        
                        sql_uppercase = """
                            INSERT INTO user_ingredients (
                                name, protein_percent, fat_percent, water_percent, "Ve_Protein_Percent",
                                notes, water_retention_factor, min_usage_percent, max_usage_percent,
                                precio_por_kg, categoria, user_id
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        # Necesitamos un *nuevo* cursor para el fallback
                        with conn.cursor() as fallback_cursor:
                            fallback_cursor.executemany(sql_uppercase, user_ingredients_to_insert)
                            conn.commit() # Commit explícito para el fallback
                            
                    # Si el primer 'try' tuvo éxito, el commit es automático
            # Commit automático principal
            return True
    except Exception as e:
        log.error(f"Error seeding ingredients for user {user_id}: {e}")
        # Rollback automático
        return False