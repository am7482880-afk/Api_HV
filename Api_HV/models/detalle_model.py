# models/detalle_model.py
# Consultas SQL de estudios, cursos, experiencias y habilidades.
# Todas se asocian a la hoja de vida mediante hoja_vida_id (= id_personal).

from database import obtener_cursor


def crear_estudio(hoja_vida_id, d):
    with obtener_cursor(commit=True) as cursor:
        cursor.execute(
            """
            INSERT INTO estudios
            (id_personal, Nivel, Institucion, Titulo, Fecha_inicio, Fecha_finalizacion, Certificado)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                hoja_vida_id,
                d["nivel"],
                d["institucion"],
                d["titulo"],
                d["fecha_inicio"],
                d["fecha_finalizacion"],
                d["certificado"],
            ),
        )
        return cursor.lastrowid


def crear_curso(hoja_vida_id, nombre):
    with obtener_cursor(commit=True) as cursor:
        cursor.execute(
            "INSERT INTO cursos (id_personal, Nombre) VALUES (%s, %s)",
            (hoja_vida_id, nombre),
        )
        return cursor.lastrowid


def crear_experiencia(hoja_vida_id, d):
    with obtener_cursor(commit=True) as cursor:
        cursor.execute(
            """
            INSERT INTO experiencias
            (id_personal, Empresa, Cargo, Area, Fecha_ingreso, Fecha_retiro,
             Funciones, Referencia_laboral, Certificado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                hoja_vida_id,
                d["empresa"],
                d["cargo"],
                d["area"],
                d["fecha_ingreso"],
                d["fecha_retiro"],
                d["funciones"],
                d["referencia_laboral"],
                d["certificado"],
            ),
        )
        return cursor.lastrowid


def experiencia_pertenece_a_usuario(experiencia_id, usuario_id):
    """Verifica que la experiencia sea de una hoja de vida del aprendiz."""
    with obtener_cursor() as cursor:
        cursor.execute(
            """
            SELECT e.id_experiencia
            FROM experiencias e
            INNER JOIN personal hv ON hv.id_personal = e.id_personal
            WHERE e.id_experiencia = %s AND hv.usuario_id = %s
            """,
            (experiencia_id, usuario_id),
        )
        return cursor.fetchone() is not None


def habilidad_existe(experiencia_id, nombre):
    with obtener_cursor() as cursor:
        cursor.execute(
            "SELECT id FROM habilidades WHERE experiencia_id = %s AND LOWER(nombre) = LOWER(%s)",
            (experiencia_id, nombre),
        )
        return cursor.fetchone() is not None


def crear_habilidad(experiencia_id, nombre):
    with obtener_cursor(commit=True) as cursor:
        cursor.execute(
            "INSERT INTO habilidades (experiencia_id, nombre) VALUES (%s, %s)",
            (experiencia_id, nombre),
        )
        return cursor.lastrowid
