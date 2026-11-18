# models/hoja_vida_model.py
# Consultas SQL de la hoja de vida (tabla 'personal') y de la hoja completa.
#
# NOTA: en la guía la tabla se llama 'hojas_vida'. En este proyecto usamos
# la tabla 'personal' que ya existía. El "hoja_vida_id" de las rutas es el
# campo 'id_personal'. Los nombres se devuelven en minúscula para que el JSON
# sea igual al de la guía.

from database import obtener_cursor

SELECT_PERSONAL = """
    SELECT
        p.id_personal        AS id,
        p.usuario_id         AS usuario_id,
        p.Nombres            AS nombres,
        p.Apellidos          AS apellidos,
        p.Correo             AS correo,
        p.Direccion          AS direccion,
        p.Perfil_Profesional AS perfil_profesional,
        p.Fotografia         AS fotografia,
        p.Edad               AS edad,
        p.Ciudad             AS ciudad,
        p.Programa           AS programa,
        p.Ficha              AS ficha,
        p.Jornada            AS jornada
    FROM personal p
"""


def obtener_por_usuario(usuario_id):
    with obtener_cursor() as cursor:
        cursor.execute(SELECT_PERSONAL + " WHERE p.usuario_id = %s", (usuario_id,))
        return cursor.fetchone()


def obtener_por_id(hoja_vida_id):
    with obtener_cursor() as cursor:
        cursor.execute(SELECT_PERSONAL + " WHERE p.id_personal = %s", (hoja_vida_id,))
        return cursor.fetchone()


def correo_en_uso(correo):
    """True si otra hoja de vida ya usa ese correo (la columna es UNIQUE)."""
    with obtener_cursor() as cursor:
        cursor.execute("SELECT id_personal FROM personal WHERE Correo = %s", (correo,))
        return cursor.fetchone() is not None


def pertenece_a_usuario(hoja_vida_id, usuario_id):
    """True si la hoja de vida es del usuario que inició sesión."""
    with obtener_cursor() as cursor:
        cursor.execute(
            "SELECT id_personal FROM personal WHERE id_personal = %s AND usuario_id = %s",
            (hoja_vida_id, usuario_id),
        )
        return cursor.fetchone() is not None


def crear(usuario_id, datos):
    """Inserta los datos básicos. Devuelve el id de la hoja de vida (id_personal)."""
    with obtener_cursor(commit=True) as cursor:
        cursor.execute(
            """
            INSERT INTO personal
            (usuario_id, Nombres, Apellidos, Correo, Direccion, Perfil_Profesional,
             Fotografia, Edad, Ciudad, Programa, Ficha, Jornada)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                usuario_id,
                datos["nombres"],
                datos["apellidos"],
                datos["correo"],
                datos["direccion"],
                datos["perfil_profesional"],
                datos["fotografia"],
                datos["edad"],
                datos["ciudad"],
                datos["programa"],
                datos["ficha"],
                datos["jornada"],
            ),
        )
        return cursor.lastrowid


def listar():
    """Listado general para el reclutador, con el total de registros de cada sección."""
    with obtener_cursor() as cursor:
        cursor.execute(
            """
            SELECT
                p.id_personal AS id,
                p.usuario_id  AS usuario_id,
                p.Nombres     AS nombres,
                p.Apellidos   AS apellidos,
                p.Correo      AS correo,
                p.Ciudad      AS ciudad,
                p.Programa    AS programa,
                p.Ficha       AS ficha,
                p.Jornada     AS jornada,
                p.Perfil_Profesional AS perfil_profesional,
                (SELECT COUNT(*) FROM estudios e     WHERE e.id_personal = p.id_personal) AS total_estudios,
                (SELECT COUNT(*) FROM cursos c       WHERE c.id_personal = p.id_personal) AS total_cursos,
                (SELECT COUNT(*) FROM experiencias x WHERE x.id_personal = p.id_personal) AS total_experiencias
            FROM personal p
            ORDER BY p.id_personal DESC
            """
        )
        return cursor.fetchall()


def obtener_completa(hoja_vida_id):
    """
    Devuelve la hoja de vida completa organizada en secciones:
    datos_personales, estudios, cursos, experiencias (cada una con sus
    habilidades) y habilidades (todas juntas).
    Devuelve None si la hoja de vida no existe.
    """
    with obtener_cursor() as cursor:
        cursor.execute(SELECT_PERSONAL + " WHERE p.id_personal = %s", (hoja_vida_id,))
        datos_personales = cursor.fetchone()
        if not datos_personales:
            return None

        cursor.execute(
            """
            SELECT id_estudio AS id, id_personal AS hoja_vida_id,
                   Nivel AS nivel, Institucion AS institucion, Titulo AS titulo,
                   Fecha_inicio AS fecha_inicio, Fecha_finalizacion AS fecha_finalizacion,
                   Certificado AS certificado
            FROM estudios
            WHERE id_personal = %s
            ORDER BY Fecha_inicio DESC, id_estudio DESC
            """,
            (hoja_vida_id,),
        )
        estudios = cursor.fetchall()

        cursor.execute(
            """
            SELECT id_curso AS id, id_personal AS hoja_vida_id, Nombre AS nombre
            FROM cursos
            WHERE id_personal = %s
            ORDER BY id_curso
            """,
            (hoja_vida_id,),
        )
        cursos = cursor.fetchall()

        cursor.execute(
            """
            SELECT id_experiencia AS id, id_personal AS hoja_vida_id,
                   Empresa AS empresa, Cargo AS cargo, Area AS area,
                   Fecha_ingreso AS fecha_ingreso, Fecha_retiro AS fecha_retiro,
                   Funciones AS funciones, Referencia_laboral AS referencia_laboral,
                   Certificado AS certificado
            FROM experiencias
            WHERE id_personal = %s
            ORDER BY Fecha_ingreso DESC, id_experiencia DESC
            """,
            (hoja_vida_id,),
        )
        experiencias = cursor.fetchall()

        # Habilidades de todas las experiencias de esta hoja de vida
        cursor.execute(
            """
            SELECT h.id, h.nombre, h.experiencia_id
            FROM habilidades h
            INNER JOIN experiencias e ON h.experiencia_id = e.id_experiencia
            WHERE e.id_personal = %s
            ORDER BY h.id
            """,
            (hoja_vida_id,),
        )
        habilidades = cursor.fetchall()

    # Asociar las habilidades con cada experiencia
    for experiencia in experiencias:
        experiencia["habilidades"] = [
            h for h in habilidades if h["experiencia_id"] == experiencia["id"]
        ]

    return {
        "datos_personales": datos_personales,
        "estudios": estudios,
        "cursos": cursos,
        "experiencias": experiencias,
        "habilidades": habilidades,
    }
