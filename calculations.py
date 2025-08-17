# core/calculations.py
import math

def convert_to_kg(quantity, unit):
    """Convierte cantidad a Kg basado en la unidad."""
    kg_total = 0.0
    unit_lower = unit.lower() if isinstance(unit, str) else ''
    if not isinstance(quantity, (int, float)): return 0.0
    if unit_lower == 'g': kg_total = quantity / 1000.0
    else: kg_total = quantity
    return kg_total

def process_ingredients_for_display(ingredients_data: list[dict]) -> list[dict]:
    """
    Procesa y ORDENA los ingredientes usando la columna 'categoria' de la base de datos.
    """
    processed_data = []
    if not ingredients_data: return processed_data

    CATEGORY_ORDER = {
        "Cárnico": 1,
        "Agua/Hielo": 2,
        "Retenedor/No Cárnico": 3,
        "Condimento/Aditivo": 4,
        "Colorante": 5
    }
    
    for ing in ingredients_data:
        kg_total = convert_to_kg(ing.get('quantity', 0), ing.get('unit', ''))
        precio_por_kg = ing.get('precio_por_kg', 0) or 0
        categoria = ing.get('categoria', 'Retenedor/No Cárnico')
        
        processed_data.append({
            'formula_ingredient_id': ing.get('formula_ingredient_id', -1),
            'name': ing.get('ingredient_name', 'ErrorNombre'),
            'original_qty_display': f"{ing.get('quantity', 0):.2f}",
            'original_unit': ing.get('unit', ''),
            'kg_total': kg_total,
            'kg_protein': kg_total * ((ing.get('protein_percent', 0) or 0) / 100.0),
            'kg_fat': kg_total * ((ing.get('fat_percent', 0) or 0) / 100.0),
            'kg_water': kg_total * ((ing.get('water_percent', 0) or 0) / 100.0),
            'water_retention_factor': ing.get('water_retention_factor', 0) or 0,
            'costo_linea': kg_total * precio_por_kg,
            'sort_order': CATEGORY_ORDER.get(categoria, 3)
        })
        
    processed_data.sort(key=lambda x: (x['sort_order'], -x['kg_total']))

    return processed_data

def calculate_formula_totals(processed_ingredients: list[dict]) -> dict:
    """
    Calcula todos los totales de la fórmula con la lógica de humedad corregida.
    """
    if not processed_ingredients:
        return {
            'total_kg': 0, 'protein_perc': 0, 'fat_perc': 0, 'water_perc': 0,
            'costo_total': 0, 'costo_por_kg': 0,
            'aw_fp_ratio_str': 'N/A', 'af_fp_ratio_str': 'N/A'
        }

    # --- CÁLCULO DE TOTALES EN KG ---
    total_kg = sum(item.get('kg_total', 0) for item in processed_ingredients)
    total_protein_kg = sum(item.get('kg_protein', 0) for item in processed_ingredients)
    total_fat_kg = sum(item.get('kg_fat', 0) for item in processed_ingredients)
    total_water_kg = sum(item.get('kg_water', 0) for item in processed_ingredients) # Esta es el agua total REAL
    total_retained_water_kg = sum(item.get('kg_total', 0) * item.get('water_retention_factor', 0) for item in processed_ingredients)
    costo_total = sum(item.get('costo_linea', 0) for item in processed_ingredients)
    
    # --- CÁLCULO DE VALORES FINALES ---
    costo_por_kg = costo_total / total_kg if total_kg > 0 else 0
    
    # --- CÁLCULO DE PORCENTAJES (CORREGIDO) ---
    # El % de humedad se calcula usando el agua total real, sin sumar el agua retenida.
    protein_perc = (total_protein_kg / total_kg * 100.0) if total_kg > 0 else 0
    fat_perc = (total_fat_kg / total_kg * 100.0) if total_kg > 0 else 0
    water_perc = (total_water_kg / total_kg * 100.0) if total_kg > 0 else 0
    
    # --- CÁLCULOS DE RATIOS (usando los porcentajes correctos) ---
    aw_fp_ratio = (water_perc / protein_perc) if protein_perc > 0 else float('inf')
    af_fp_ratio = (fat_perc / protein_perc) if protein_perc > 0 else float('inf')
    aw_fp_ratio_str = f"{aw_fp_ratio:.2f}" if not math.isinf(aw_fp_ratio) else "N/A"
    af_fp_ratio_str = f"{af_fp_ratio:.2f}" if not math.isinf(af_fp_ratio) else "N/A"

    return {
        'total_kg': total_kg,
        'total_protein_kg': total_protein_kg,
        'total_fat_kg': total_fat_kg,
        'total_water_kg': total_water_kg,
        'total_retained_water_kg': total_retained_water_kg, # Lo mantenemos como dato informativo
        'protein_perc': protein_perc,
        'fat_perc': fat_perc,
        'water_perc': water_perc, # Porcentaje de humedad corregido
        'costo_total': costo_total,
        'costo_por_kg': costo_por_kg,
        'aw_fp_ratio_str': aw_fp_ratio_str,
        'af_fp_ratio_str': af_fp_ratio_str
    }
