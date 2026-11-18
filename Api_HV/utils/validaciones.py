# utils/validaciones.py
# Funciones de validación reutilizables por todas las rutas.

import re
from datetime import date, datetime

PATRON_CORREO = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

JORNADAS_VALIDAS = ["Mañana", "Tarde", "Noche", "Mixta", "Fin de semana"]


def es_correo_valido(correo):
    return bool(correo) and bool(PATRON_CORREO.match(correo))


def texto(datos, *claves):
    """
    Devuelve el texto de la primera clave que exista en 'datos', sin espacios
    al inicio ni al final. Permite aceptar 'nombres' o 'Nombres', por ejemplo.
    Si no existe ninguna, devuelve "".
    """
    for clave in claves:
        valor = datos.get(clave)
        if valor is not None:
            return str(valor).strip()
    return ""


def texto_opcional(datos, *claves):
    """Igual que texto(), pero devuelve None si está vacío (para guardar NULL)."""
    valor = texto(datos, *claves)
    return valor or None


def faltantes(campos):
    """
    Recibe un diccionario {"Nombre visible": valor} y devuelve la lista
    de los nombres cuyo valor está vacío.
    """
    return [nombre for nombre, valor in campos.items() if valor in (None, "")]


def fecha_opcional(valor, nombre_campo):
    """
    Valida una fecha con formato AAAA-MM-DD.
    Devuelve (fecha_o_None, mensaje_error_o_None).
    """
    if valor in (None, ""):
        return None, None
    try:
        return datetime.strptime(str(valor).strip()[:10], "%Y-%m-%d").date(), None
    except ValueError:
        return None, f"La fecha '{nombre_campo}' debe tener el formato AAAA-MM-DD"


def validar_rango_fechas(inicio, fin, nombre_inicio, nombre_fin):
    """Devuelve un mensaje de error si la fecha final es anterior a la inicial."""
    if inicio and fin and fin < inicio:
        return f"La '{nombre_fin}' no puede ser anterior a la '{nombre_inicio}'"
    if inicio and inicio > date.today():
        return f"La '{nombre_inicio}' no puede ser una fecha futura"
    return None


def entero_opcional(valor):
    """Convierte a entero. Devuelve (numero_o_None, es_valido)."""
    if valor in (None, ""):
        return None, True
    try:
        return int(str(valor).strip()), True
    except ValueError:
        return None, False
