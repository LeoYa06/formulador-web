# db/database.py
import os
import psycopg2
import psycopg2.extras # Para obtener resultados como diccionarios
import datetime

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

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS formulas (
            id SERIAL PRIMARY KEY,
            product_name TEXT NOT NULL UNIQUE,
            description TEXT,
            creation_date TEXT NOT NULL
        );
    ''')
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

    conn.commit()
    cursor.close()
    conn.close()
    print("Base de datos PostgreSQL inicializada.")

# --- Funciones para Fórmulas ---
def get_all_formulas() -> list[dict]:
    """Obtiene lista simple de todas las fórmulas."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("SELECT id, product_name, creation_date FROM formulas ORDER BY product_name")
    formulas = [dict(row) for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return formulas

def get_formula_by_id(formula_id: int) -> dict | None:
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("SELECT * FROM formulas WHERE id = %s", (formula_id,))
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

def add_formula(product_name: str, description: str = "") -> int | None:
    conn = get_db_connection()
    cursor = conn.cursor()
    creation_date = datetime.datetime.now().isoformat()
    try:
        cursor.execute("INSERT INTO formulas (product_name, description, creation_date) VALUES (%s, %s, %s) RETURNING id", 
                       (product_name, description, creation_date))
        formula_id = cursor.fetchone()[0]
        conn.commit()
        return formula_id
    except psycopg2.IntegrityError:
        return None
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