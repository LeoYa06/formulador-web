# import_data.py
import database

# --- CONFIGURACIÓN ---
MASTER_INGREDIENTS_FILE = 'ingredientes_maestros.xlsx'

def run_import():
    print("--- INICIANDO IMPORTACIÓN DESDE ARCHIVO MAESTRO ---")

    # 1. Asegurarse de que las tablas existan
    print("Inicializando base de datos...")
    database.initialize_database()
    print("Base de datos lista.")

    # 2. Importar todo desde el único archivo maestro
    database.import_ingredients_from_excel(MASTER_INGREDIENTS_FILE)

    print("\n¡IMPORTACIÓN FINALIZADA!")

if __name__ == "__main__":
    run_import()