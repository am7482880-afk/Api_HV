# models/usuario_model.py
# Consultas SQL de la tabla 'usuarios'.

from database import obtener_cursor


def buscar_por_correo(correo):
    """Devuelve el usuario (incluye el hash de la contraseña) o None."""
    with obtener_cursor() as cursor:
        cursor.execute(
            """
            SELECT id, nombre, correo, password, rol, estado
            FROM usuarios
            WHERE correo = %s
            """,
            (correo,),
        )
        return cursor.fetchone()


def buscar_por_id(usuario_id):
    """Devuelve el usuario SIN la contraseña o None."""
    with obtener_cursor() as cursor:
        cursor.execute(
            """
            SELECT id, nombre, correo, rol, estado, fecha_creacion
            FROM usuarios
            WHERE id = %s
            """,
            (usuario_id,),
        )
        return cursor.fetchone()


def correo_existe(correo):
    with obtener_cursor() as cursor:
        cursor.execute("SELECT id FROM usuarios WHERE correo = %s", (correo,))
        return cursor.fetchone() is not None


def crear_aprendiz(nombre, correo, password_hash):
    """El registro público SIEMPRE crea un aprendiz. Devuelve el id nuevo."""
    with obtener_cursor(commit=True) as cursor:
        cursor.execute(
            """
            INSERT INTO usuarios (nombre, correo, password, rol)
            VALUES (%s, %s, %s, 'aprendiz')
            """,
            (nombre, correo, password_hash),
        )
        return cursor.lastrowid
