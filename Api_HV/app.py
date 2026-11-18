# app.py
# API del Sistema de Registro de Hojas de Vida (Flask + MySQL + JWT)
# Contiene TODAS las rutas: las nuevas de la guía + las anteriores del proyecto.
# Solo necesita config.py y database.py en la misma carpeta.
#
# Ejecutar:  python app.py   ->  http://127.0.0.1:5000

import re
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from functools import wraps

import mysql.connector
from flask import Flask, jsonify, request
from flask.json.provider import DefaultJSONProvider
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)
from werkzeug.security import check_password_hash, generate_password_hash

from config import Config
from database import conectar_bd


# ============================================================================
# CONFIGURACIÓN DE LA APP
# ============================================================================

class ProveedorJSON(DefaultJSONProvider):
    """Devuelve las fechas como 'AAAA-MM-DD' y respeta las tildes y la ñ."""

    ensure_ascii = False
    sort_keys = False

    @staticmethod
    def default(o):
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        if isinstance(o, Decimal):
            return float(o)
        return DefaultJSONProvider.default(o)


app = Flask(__name__)
app.config.from_object(Config)
app.json = ProveedorJSON(app)

CORS(
    app,
    resources={r"/api/*": {"origins": Config.FRONTEND_URLS}},
    allow_headers=["Content-Type", "Authorization"],
)

jwt = JWTManager(app)


@jwt.unauthorized_loader
def sin_token(_motivo):
    return jsonify({"mensaje": "Debes iniciar sesión para acceder (falta el token)"}), 401


@jwt.invalid_token_loader
def token_invalido(_motivo):
    return jsonify({"mensaje": "El token no es válido. Inicia sesión de nuevo"}), 401


@jwt.expired_token_loader
def token_expirado(_header, _payload):
    return jsonify({"mensaje": "Tu sesión expiró. Inicia sesión de nuevo"}), 401


# ============================================================================
# FUNCIONES DE AYUDA
# ============================================================================

@contextmanager
def cursor_bd(commit=False):
    """Abre conexión + cursor (diccionarios) y los cierra solos."""
    conexion = conectar_bd()
    cursor = conexion.cursor(dictionary=True)
    try:
        yield cursor
        if commit:
            conexion.commit()
    except Exception:
        conexion.rollback()
        raise
    finally:
        cursor.close()
        conexion.close()


def rol_requerido(*roles):
    """Exige token válido y que el rol del token esté en 'roles' (si no, 403)."""

    def decorador(funcion):
        @wraps(funcion)
        @jwt_required()
        def wrapper(*args, **kwargs):
            if get_jwt().get("rol") not in roles:
                return jsonify({"mensaje": "No tienes permisos para acceder"}), 403
            return funcion(*args, **kwargs)

        return wrapper

    return decorador


def usuario_actual_id():
    return int(get_jwt_identity())


def rol_actual():
    return get_jwt().get("rol")


def leer_json():
    return request.get_json(silent=True) or {}


def enviado(datos, *claves):
    """¿Vino alguna de estas claves en el JSON? Devuelve (True/False, valor)."""
    for clave in claves:
        if clave in datos:
            return True, datos[clave]
    return False, None


def limpiar(valor):
    """Quita espacios. Devuelve None si queda vacío."""
    if valor is None:
        return None
    valor = str(valor).strip()
    return valor or None


PATRON_CORREO = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
JORNADAS_VALIDAS = ["Mañana", "Tarde", "Noche", "Mixta", "Fin de semana"]


def es_correo_valido(correo):
    return bool(correo) and bool(PATRON_CORREO.match(correo))


def a_fecha(valor, nombre):
    """Convierte 'AAAA-MM-DD' a fecha. Devuelve (fecha_o_None, error_o_None)."""
    if valor in (None, ""):
        return None, None
    if isinstance(valor, date):
        return valor, None
    try:
        return datetime.strptime(str(valor).strip()[:10], "%Y-%m-%d").date(), None
    except ValueError:
        return None, f"La fecha '{nombre}' debe tener el formato AAAA-MM-DD"


def validar_rango(inicio, fin, nombre_inicio, nombre_fin):
    if inicio and fin and fin < inicio:
        return f"La '{nombre_fin}' no puede ser anterior a la '{nombre_inicio}'"
    return None


def lista_habilidades(valor):
    """Acepta "a, b, c" o ["a", "b"] y devuelve una lista limpia sin repetidos."""
    if not valor:
        return []
    partes = valor if isinstance(valor, list) else str(valor).split(",")
    resultado = []
    for parte in partes:
        nombre = limpiar(parte)
        if nombre and nombre.lower() not in [r.lower() for r in resultado]:
            resultado.append(nombre[:100])
    return resultado


# ---------------- Permisos sobre la hoja de vida ----------------

def verificar_acceso_hv(id_personal, modificar=False):
    """
    - Reclutador: puede CONSULTAR cualquier hoja de vida, no modificar.
    - Aprendiz: solo SU hoja de vida (consultar y modificar).
    Devuelve None si tiene permiso, o la respuesta de error (404/403).
    """
    with cursor_bd() as cursor:
        cursor.execute("SELECT usuario_id FROM personal WHERE id_personal = %s", (id_personal,))
        hv = cursor.fetchone()

    if not hv:
        return jsonify({"mensaje": "No se encontró esa hoja de vida"}), 404

    rol = rol_actual()
    if rol == "reclutador":
        if modificar:
            return jsonify({"mensaje": "El reclutador solo puede consultar"}), 403
        return None

    if rol == "aprendiz" and hv["usuario_id"] == usuario_actual_id():
        return None

    # Hoja de vida de otra persona: se responde 404 para no revelar que existe
    return jsonify({"mensaje": "No se encontró esa hoja de vida"}), 404


def id_hv_de(tabla, campo_id, valor_id):
    """Devuelve el id_personal al que pertenece un estudio/curso/experiencia, o None."""
    with cursor_bd() as cursor:
        cursor.execute(f"SELECT id_personal FROM {tabla} WHERE {campo_id} = %s", (valor_id,))
        fila = cursor.fetchone()
    return fila["id_personal"] if fila else None


# ---------------- Consultas reutilizables ----------------

SELECT_PERSONAL = """
    SELECT p.id_personal AS id, p.usuario_id, p.Nombres AS nombres, p.Apellidos AS apellidos,
           p.Correo AS correo, p.Direccion AS direccion, p.Perfil_Profesional AS perfil_profesional,
           p.Fotografia AS fotografia, p.Edad AS edad, p.Ciudad AS ciudad, p.Programa AS programa,
           p.Ficha AS ficha, p.Jornada AS jornada
    FROM personal p
"""


def hoja_vida_completa(id_personal):
    """datos_personales, estudios, cursos, experiencias (con habilidades) y habilidades."""
    with cursor_bd() as cursor:
        cursor.execute(SELECT_PERSONAL + " WHERE p.id_personal = %s", (id_personal,))
        datos_personales = cursor.fetchone()
        if not datos_personales:
            return None

        cursor.execute("""
            SELECT id_estudio AS id, id_personal AS hoja_vida_id, Nivel AS nivel,
                   Institucion AS institucion, Titulo AS titulo, Fecha_inicio AS fecha_inicio,
                   Fecha_finalizacion AS fecha_finalizacion, Certificado AS certificado
            FROM estudios WHERE id_personal = %s
            ORDER BY Fecha_inicio DESC, id_estudio DESC
        """, (id_personal,))
        estudios = cursor.fetchall()

        cursor.execute("""
            SELECT id_curso AS id, id_personal AS hoja_vida_id, Nombre AS nombre
            FROM cursos WHERE id_personal = %s ORDER BY id_curso
        """, (id_personal,))
        cursos = cursor.fetchall()

        cursor.execute("""
            SELECT id_experiencia AS id, id_personal AS hoja_vida_id, Empresa AS empresa,
                   Cargo AS cargo, Area AS area, Fecha_ingreso AS fecha_ingreso,
                   Fecha_retiro AS fecha_retiro, Funciones AS funciones,
                   Referencia_laboral AS referencia_laboral, Certificado AS certificado
            FROM experiencias WHERE id_personal = %s
            ORDER BY Fecha_ingreso DESC, id_experiencia DESC
        """, (id_personal,))
        experiencias = cursor.fetchall()

        cursor.execute("""
            SELECT h.id, h.nombre, h.experiencia_id
            FROM habilidades h
            INNER JOIN experiencias e ON h.experiencia_id = e.id_experiencia
            WHERE e.id_personal = %s ORDER BY h.id
        """, (id_personal,))
        habilidades = cursor.fetchall()

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


def experiencias_con_texto_habilidades(cursor, filas):
    """
    Para las rutas ANTERIORES: llena el campo 'Habilidades' (texto) con las
    habilidades de la tabla nueva, así la respuesta queda igual que antes.
    """
    for fila in filas:
        cursor.execute(
            "SELECT nombre FROM habilidades WHERE experiencia_id = %s ORDER BY id",
            (fila["id_experiencia"],),
        )
        fila["Habilidades"] = ", ".join(h["nombre"] for h in cursor.fetchall()) or None
    return filas


def reemplazar_habilidades(cursor, id_experiencia, nombres):
    """Borra las habilidades de la experiencia y guarda las nuevas."""
    cursor.execute("DELETE FROM habilidades WHERE experiencia_id = %s", (id_experiencia,))
    for nombre in nombres:
        cursor.execute(
            "INSERT INTO habilidades (experiencia_id, nombre) VALUES (%s, %s)",
            (id_experiencia, nombre),
        )


# ---------------- Validación de cada tipo de registro ----------------
# Reciben los datos ACTUALES (para PUT) y los enviados; aceptan claves en
# minúscula (nueva) o con mayúscula (como estaban antes).

def armar_personal(datos, actual=None):
    actual = actual or {}
    campos = {
        "nombres": ("nombres", "Nombres", "nombre"),
        "apellidos": ("apellidos", "Apellidos"),
        "correo": ("correo", "Correo"),
        "direccion": ("direccion", "Direccion"),
        "perfil_profesional": ("perfil_profesional", "Perfil_Profesional"),
        "fotografia": ("fotografia", "Fotografia", "foto"),
        "edad": ("edad", "Edad"),
        "ciudad": ("ciudad", "Ciudad"),
        "programa": ("programa", "Programa"),
        "ficha": ("ficha", "Ficha"),
        "jornada": ("jornada", "Jornada"),
    }
    d = {}
    for campo, claves in campos.items():
        vino, valor = enviado(datos, *claves)
        d[campo] = limpiar(valor) if vino else limpiar(actual.get(campo))

    obligatorios = ["nombres", "apellidos", "correo", "edad", "ciudad", "programa", "ficha", "jornada"]
    faltan = [c for c in obligatorios if not d[c]]
    if faltan:
        return None, "Faltan campos obligatorios: " + ", ".join(faltan)

    d["correo"] = d["correo"].lower()
    if not es_correo_valido(d["correo"]):
        return None, "El correo no tiene un formato válido"
    if len(d["nombres"]) > 100 or len(d["apellidos"]) > 100:
        return None, "Nombres y apellidos admiten máximo 100 caracteres"
    try:
        d["edad"] = int(d["edad"])
    except ValueError:
        return None, "La edad debe ser un número entre 14 y 100"
    if d["edad"] < 14 or d["edad"] > 100:
        return None, "La edad debe ser un número entre 14 y 100"
    if not d["ficha"].isdigit() or len(d["ficha"]) > 20:
        return None, "La ficha debe contener solo números (máximo 20)"
    jornada = next((j for j in JORNADAS_VALIDAS if j.lower() == d["jornada"].lower()), None)
    if not jornada:
        return None, "Jornada no válida. Opciones: " + ", ".join(JORNADAS_VALIDAS)
    d["jornada"] = jornada
    if len(d["ciudad"]) > 100 or len(d["programa"]) > 150:
        return None, "Ciudad (máx. 100) o programa (máx. 150) demasiado largos"
    if d["direccion"] and len(d["direccion"]) > 200:
        return None, "La dirección admite máximo 200 caracteres"
    return d, None


def armar_estudio(datos, actual=None):
    actual = actual or {}
    campos = {
        "nivel": ("nivel", "Nivel"),
        "institucion": ("institucion", "Institucion"),
        "titulo": ("titulo", "Titulo"),
        "fecha_inicio": ("fecha_inicio", "Fecha_inicio"),
        "fecha_finalizacion": ("fecha_finalizacion", "Fecha_finalizacion"),
        "certificado": ("certificado", "Certificado"),
    }
    d = {}
    for campo, claves in campos.items():
        vino, valor = enviado(datos, *claves)
        d[campo] = (limpiar(valor) if vino else actual.get(campo))

    faltan = [c for c in ("nivel", "institucion", "titulo") if not d[c]]
    if faltan:
        return None, "Faltan campos obligatorios: " + ", ".join(faltan)
    if len(d["nivel"]) > 50 or len(d["institucion"]) > 150 or len(d["titulo"]) > 150:
        return None, "Algún campo supera la longitud permitida"

    d["fecha_inicio"], e1 = a_fecha(d["fecha_inicio"], "fecha de inicio")
    d["fecha_finalizacion"], e2 = a_fecha(d["fecha_finalizacion"], "fecha de finalización")
    e3 = validar_rango(d["fecha_inicio"], d["fecha_finalizacion"], "fecha de inicio", "fecha de finalización")
    if e1 or e2 or e3:
        return None, e1 or e2 or e3
    return d, None


def armar_experiencia(datos, actual=None):
    actual = actual or {}
    campos = {
        "empresa": ("empresa", "Empresa"),
        "cargo": ("cargo", "Cargo"),
        "area": ("area", "Area"),
        "fecha_ingreso": ("fecha_ingreso", "Fecha_ingreso"),
        "fecha_retiro": ("fecha_retiro", "Fecha_retiro"),
        "funciones": ("funciones", "Funciones"),
        "referencia_laboral": ("referencia_laboral", "Referencia_laboral"),
        "certificado": ("certificado", "Certificado"),
    }
    d = {}
    for campo, claves in campos.items():
        vino, valor = enviado(datos, *claves)
        d[campo] = (limpiar(valor) if vino else actual.get(campo))

    # "Actualmente" (como lo mandaba el React anterior) = sigue trabajando
    if isinstance(d["fecha_retiro"], str) and d["fecha_retiro"].lower() == "actualmente":
        d["fecha_retiro"] = None

    faltan = [c for c in ("empresa", "cargo") if not d[c]]
    if faltan:
        return None, "Faltan campos obligatorios: " + ", ".join(faltan)
    if len(d["empresa"]) > 150 or len(d["cargo"]) > 100 or len(d["area"] or "") > 100:
        return None, "Algún campo supera la longitud permitida"

    d["fecha_ingreso"], e1 = a_fecha(d["fecha_ingreso"], "fecha de ingreso")
    d["fecha_retiro"], e2 = a_fecha(d["fecha_retiro"], "fecha de retiro")
    e3 = validar_rango(d["fecha_ingreso"], d["fecha_retiro"], "fecha de ingreso", "fecha de retiro")
    if e1 or e2 or e3:
        return None, e1 or e2 or e3
    return d, None


# ============================================================================
# RUTAS GENERALES
# ============================================================================

@app.route("/")
def inicio():
    return "Api hoja de vida funcionando"


@app.route("/probar")
def probar_data():
    conexion = conectar_bd()
    conectado = conexion.is_connected()
    conexion.close()
    return jsonify({"Mensaje": "Conexion ok" if conectado else "Sin conexion"})


# Ruta de ejemplo con datos fijos (no usa la base de datos)
@app.route("/api/hoja-vida")
def obtener_hojasvida_ejemplo():
    hojas_vida = [
        {
            "id_personal": 1, "Fotografia": "foto1.jpg", "Nombres": "Ana", "Apellidos": "Muñoz",
            "Correo": "nana@gmail.com", "Direccion": "Calle 100 # 15-20",
            "Perfil_Profesional": "Desarrollador Tecnólogo en ADSO con experiencia en Python y React",
        },
        {
            "id_personal": 2, "Fotografia": "foto2.jpg", "Nombres": "Erik", "Apellidos": "Espitia",
            "Correo": "erik626@gmail.com", "Direccion": "Carrera 7 # 45-10",
            "Perfil_Profesional": "Diseñador y productor multimedia",
        },
        {
            "id_personal": 3, "Fotografia": "foto3.jpg", "Nombres": "Sara", "Apellidos": "Cely",
            "Correo": "sara625@gmail.com", "Direccion": "Carrera 7 # 45-10",
            "Perfil_Profesional": "Animacion 3D",
        },
    ]
    return jsonify(hojas_vida)


# ============================================================================
# AUTENTICACIÓN (guía puntos 2 y 4)
# ============================================================================

def usuario_publico(usuario):
    return {"id": usuario["id"], "nombre": usuario["nombre"],
            "correo": usuario["correo"], "rol": usuario["rol"]}


def generar_token(usuario):
    return create_access_token(identity=str(usuario["id"]),
                               additional_claims={"rol": usuario["rol"]})


# Registro público: SIEMPRE crea un aprendiz
@app.route("/api/registro-usuario", methods=["POST"])
def registro_usuario():
    datos = request.get_json(silent=True)
    if not datos:
        return jsonify({"mensaje": "No se recibieron datos"}), 400

    nombre = str(datos.get("nombre", "")).strip()
    correo = str(datos.get("correo", "")).strip().lower()
    password = str(datos.get("password", ""))

    if not nombre or not correo or not password:
        return jsonify({"mensaje": "Todos los campos son obligatorios"}), 400
    if len(nombre) < 3 or len(nombre) > 100:
        return jsonify({"mensaje": "El nombre debe tener entre 3 y 100 caracteres"}), 400
    if not es_correo_valido(correo) or len(correo) > 150:
        return jsonify({"mensaje": "El correo no tiene un formato válido"}), 400
    if len(password) < 8:
        return jsonify({"mensaje": "Mínimo 8 caracteres"}), 400
    if len(password) > 128:
        return jsonify({"mensaje": "La contraseña no puede superar 128 caracteres"}), 400

    with cursor_bd(commit=True) as cursor:
        cursor.execute("SELECT id FROM usuarios WHERE correo = %s", (correo,))
        if cursor.fetchone():
            return jsonify({"mensaje": "Este correo ya está registrado"}), 409

        password_hash = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO usuarios (nombre, correo, password, rol) VALUES (%s, %s, %s, 'aprendiz')",
            (nombre, correo, password_hash),
        )
        nuevo_id = cursor.lastrowid

    usuario = {"id": nuevo_id, "nombre": nombre, "correo": correo, "rol": "aprendiz"}
    return jsonify({
        "mensaje": "Cuenta creada correctamente",
        "token": generar_token(usuario),
        "usuario": usuario,
    }), 201


# Inicio de sesión: devuelve el token JWT con la identidad y el rol
@app.route("/api/login", methods=["POST"])
def login():
    datos = leer_json()
    correo = str(datos.get("correo", "")).strip().lower()
    password = str(datos.get("password", ""))

    if not correo or not password:
        return jsonify({"mensaje": "Ingresa el correo y la contraseña"}), 400

    with cursor_bd() as cursor:
        cursor.execute(
            "SELECT id, nombre, correo, password, rol, estado FROM usuarios WHERE correo = %s",
            (correo,),
        )
        usuario = cursor.fetchone()

    if not usuario or not check_password_hash(usuario["password"], password):
        return jsonify({"mensaje": "Correo o contraseña incorrectos"}), 401
    if not usuario["estado"]:
        return jsonify({"mensaje": "Cuenta desactivada"}), 403

    return jsonify({
        "mensaje": "Inicio de sesión correcto",
        "token": generar_token(usuario),
        "usuario": usuario_publico(usuario),
    }), 200


# Datos de la sesión actual (React lo usa al recargar la página)
@app.route("/api/me", methods=["GET"])
@jwt_required()
def mi_sesion():
    with cursor_bd() as cursor:
        cursor.execute(
            "SELECT id, nombre, correo, rol, estado FROM usuarios WHERE id = %s",
            (usuario_actual_id(),),
        )
        usuario = cursor.fetchone()
        if not usuario:
            return jsonify({"mensaje": "El usuario ya no existe"}), 401
        if not usuario["estado"]:
            return jsonify({"mensaje": "Cuenta desactivada"}), 403

        hoja_vida_id = None
        if usuario["rol"] == "aprendiz":
            cursor.execute("SELECT id_personal FROM personal WHERE usuario_id = %s", (usuario["id"],))
            hv = cursor.fetchone()
            hoja_vida_id = hv["id_personal"] if hv else None

    return jsonify({"usuario": usuario_publico(usuario), "hoja_vida_id": hoja_vida_id}), 200


# ============================================================================
# HOJA DE VIDA (datos personales)
# ============================================================================

# Registrar datos básicos: el usuario_id sale del token (guía punto 6)
@app.route("/api/registrohv", methods=["POST"])
@jwt_required()
def registrohv():
    usuario_id = usuario_actual_id()
    if rol_actual() != "aprendiz":
        return jsonify({"mensaje": "Solo los aprendices pueden registrar HV"}), 403

    datos = request.get_json(silent=True)
    if not datos:
        return jsonify({"mensaje": "No se recibieron datos"}), 400

    d, error = armar_personal(datos)
    if error:
        return jsonify({"mensaje": error}), 400

    with cursor_bd(commit=True) as cursor:
        cursor.execute("SELECT id_personal FROM personal WHERE usuario_id = %s", (usuario_id,))
        existente = cursor.fetchone()
        if existente:
            return jsonify({"mensaje": "Ya tienes una hoja de vida registrada",
                            "hoja_vida_id": existente["id_personal"]}), 409

        cursor.execute("SELECT id_personal FROM personal WHERE Correo = %s", (d["correo"],))
        if cursor.fetchone():
            return jsonify({"mensaje": "Ese correo ya está registrado en otra hoja de vida"}), 409

        cursor.execute("""
            INSERT INTO personal (usuario_id, Nombres, Apellidos, Correo, Direccion, Perfil_Profesional,
                                  Fotografia, Edad, Ciudad, Programa, Ficha, Jornada)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (usuario_id, d["nombres"], d["apellidos"], d["correo"], d["direccion"],
              d["perfil_profesional"], d["fotografia"], d["edad"], d["ciudad"],
              d["programa"], d["ficha"], d["jornada"]))
        hoja_vida_id = cursor.lastrowid

    return jsonify({"mensaje": "Hoja de vida registrada correctamente",
                    "hoja_vida_id": hoja_vida_id}), 201


# Consultar la hoja de vida propia, completa (guía punto 7)
@app.route("/api/mi-hoja-vida", methods=["GET"])
@jwt_required()
def mi_hoja_vida():
    if rol_actual() != "aprendiz":
        return jsonify({"mensaje": "Consulta exclusiva para aprendices"}), 403

    with cursor_bd() as cursor:
        cursor.execute("SELECT id_personal FROM personal WHERE usuario_id = %s", (usuario_actual_id(),))
        hv = cursor.fetchone()

    if not hv:
        return jsonify({"mensaje": "Aún no has registrado tu hoja de vida"}), 404
    return jsonify(hoja_vida_completa(hv["id_personal"])), 200


# Listado general: solo reclutador (guía punto 5)
@app.route("/api/hojas-vida", methods=["GET"])
@rol_requerido("reclutador")
def obtener_hojas():
    with cursor_bd() as cursor:
        cursor.execute("""
            SELECT p.id_personal AS id, p.usuario_id, p.Nombres AS nombres, p.Apellidos AS apellidos,
                   p.Correo AS correo, p.Ciudad AS ciudad, p.Programa AS programa, p.Ficha AS ficha,
                   p.Jornada AS jornada, p.Perfil_Profesional AS perfil_profesional,
                   (SELECT COUNT(*) FROM estudios e WHERE e.id_personal = p.id_personal) AS total_estudios,
                   (SELECT COUNT(*) FROM cursos c WHERE c.id_personal = p.id_personal) AS total_cursos,
                   (SELECT COUNT(*) FROM experiencias x WHERE x.id_personal = p.id_personal) AS total_experiencias
            FROM personal p
            ORDER BY p.id_personal DESC
        """)
        hojas = cursor.fetchall()
    return jsonify({"total": len(hojas), "hojas_vida": hojas}), 200


# (ANTERIOR) Listar todas las hojas de vida: ahora solo reclutador
@app.route("/api/listarhv", methods=["GET"])
@rol_requerido("reclutador")
def listar_hojasvida():
    with cursor_bd() as cursor:
        cursor.execute("SELECT * FROM personal ORDER BY id_personal")
        return jsonify(cursor.fetchall())


# Hoja de vida completa por id: reclutador, o el aprendiz dueño
@app.route("/api/hojas-vida/<int:hoja_vida_id>", methods=["GET"])
@rol_requerido("reclutador", "aprendiz")
def obtener_hoja_completa(hoja_vida_id):
    error = verificar_acceso_hv(hoja_vida_id)
    if error:
        return error
    return jsonify(hoja_vida_completa(hoja_vida_id)), 200


# (ANTERIOR) Consulta completa de la hoja de vida
@app.route("/api/consultarhojadevida/<int:id_personal>", methods=["GET"])
@rol_requerido("reclutador", "aprendiz")
def consultar_hoja_vida_completa(id_personal):
    error = verificar_acceso_hv(id_personal)
    if error:
        return error

    with cursor_bd() as cursor:
        cursor.execute("SELECT * FROM personal WHERE id_personal = %s", (id_personal,))
        persona = cursor.fetchone()
        cursor.execute("SELECT * FROM estudios WHERE id_personal = %s", (id_personal,))
        estudios = cursor.fetchall()
        cursor.execute("SELECT * FROM cursos WHERE id_personal = %s", (id_personal,))
        cursos = cursor.fetchall()
        cursor.execute("SELECT * FROM experiencias WHERE id_personal = %s", (id_personal,))
        experiencias = experiencias_con_texto_habilidades(cursor, cursor.fetchall())

    return jsonify({
        "datos_personales": persona,
        "estudios": estudios,
        "cursos": cursos,
        "experiencias_laborales": experiencias,
    }), 200


# (ANTERIOR) Consultar datos personales por id
@app.route("/api/consultarhv/<int:id>", methods=["GET"])
@rol_requerido("reclutador", "aprendiz")
def obtenerhv(id):
    error = verificar_acceso_hv(id)
    if error:
        return error
    with cursor_bd() as cursor:
        cursor.execute("SELECT * FROM personal WHERE id_personal = %s", (id,))
        return jsonify(cursor.fetchone()), 200


# (ANTERIOR) Actualizar datos personales: solo el aprendiz dueño.
# Los campos que no se envíen conservan su valor actual.
@app.route("/api/actualizar_hoja_vida/<int:id>", methods=["PUT"])
@rol_requerido("aprendiz")
def actualizar_hoja_vida(id):
    error = verificar_acceso_hv(id, modificar=True)
    if error:
        return error

    datos = leer_json()
    with cursor_bd(commit=True) as cursor:
        cursor.execute(SELECT_PERSONAL + " WHERE p.id_personal = %s", (id,))
        actual = cursor.fetchone()

        d, error = armar_personal(datos, actual)
        if error:
            return jsonify({"mensaje": error}), 400

        cursor.execute(
            "SELECT id_personal FROM personal WHERE Correo = %s AND id_personal != %s",
            (d["correo"], id),
        )
        if cursor.fetchone():
            return jsonify({"mensaje": "El correo ya está registrado por otra hoja de vida"}), 400

        cursor.execute("""
            UPDATE personal
            SET Fotografia = %s, Nombres = %s, Apellidos = %s, Correo = %s, Direccion = %s,
                Perfil_Profesional = %s, Edad = %s, Ciudad = %s, Programa = %s, Ficha = %s, Jornada = %s
            WHERE id_personal = %s
        """, (d["fotografia"], d["nombres"], d["apellidos"], d["correo"], d["direccion"],
              d["perfil_profesional"], d["edad"], d["ciudad"], d["programa"], d["ficha"],
              d["jornada"], id))

    return jsonify({"mensaje": "Hoja de vida actualizada correctamente", "id_personal": id}), 200


# (ANTERIOR) Eliminar hoja de vida: solo el aprendiz dueño.
# Por ON DELETE CASCADE se borran también sus estudios, cursos, experiencias y habilidades.
@app.route("/api/eliminarhv/<int:id>", methods=["DELETE"])
@rol_requerido("aprendiz")
def eliminarhv(id):
    error = verificar_acceso_hv(id, modificar=True)
    if error:
        return error
    with cursor_bd(commit=True) as cursor:
        cursor.execute("DELETE FROM personal WHERE id_personal = %s", (id,))
    return jsonify({"mensaje": "Hoja de vida eliminada correctamente"}), 200


# ============================================================================
# ESTUDIOS
# ============================================================================

def crear_estudio(id_personal):
    error = verificar_acceso_hv(id_personal, modificar=True)
    if error:
        return error

    d, error = armar_estudio(leer_json())
    if error:
        return jsonify({"mensaje": error}), 400

    with cursor_bd(commit=True) as cursor:
        cursor.execute("""
            INSERT INTO estudios (id_personal, Nivel, Institucion, Titulo, Fecha_inicio,
                                  Fecha_finalizacion, Certificado)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (id_personal, d["nivel"], d["institucion"], d["titulo"], d["fecha_inicio"],
              d["fecha_finalizacion"], d["certificado"]))
        id_estudio = cursor.lastrowid

    return jsonify({"mensaje": "Estudio registrado correctamente", "id_estudio": id_estudio,
                    "hoja_vida_id": id_personal}), 201


# NUEVA (guía punto 8)
@app.route("/api/hojas-vida/<int:hoja_vida_id>/estudios", methods=["POST"])
@rol_requerido("aprendiz")
def registrar_estudio(hoja_vida_id):
    return crear_estudio(hoja_vida_id)


# ANTERIOR
@app.route("/api/registrarestudio/<int:id_personal>", methods=["POST"])
@rol_requerido("aprendiz")
def registrar_estudio_hoja_vida(id_personal):
    return crear_estudio(id_personal)


@app.route("/api/consultarestudios/<int:id_personal>", methods=["GET"])
@rol_requerido("reclutador", "aprendiz")
def obtener_estudios_hoja_vida(id_personal):
    error = verificar_acceso_hv(id_personal)
    if error:
        return error
    with cursor_bd() as cursor:
        cursor.execute("SELECT * FROM estudios WHERE id_personal = %s", (id_personal,))
        return jsonify(cursor.fetchall()), 200


@app.route("/api/consultarestudio/<int:id_estudio>", methods=["GET"])
@rol_requerido("reclutador", "aprendiz")
def consultar_estudio_por_id(id_estudio):
    id_personal = id_hv_de("estudios", "id_estudio", id_estudio)
    if not id_personal or verificar_acceso_hv(id_personal):
        return jsonify({"mensaje": "Estudio no encontrado"}), 404
    with cursor_bd() as cursor:
        cursor.execute("SELECT * FROM estudios WHERE id_estudio = %s", (id_estudio,))
        return jsonify(cursor.fetchone()), 200


@app.route("/api/actualizarestudio/<int:id_estudio>", methods=["PUT"])
@rol_requerido("aprendiz")
def actualizar_estudio_por_id(id_estudio):
    id_personal = id_hv_de("estudios", "id_estudio", id_estudio)
    if not id_personal or verificar_acceso_hv(id_personal, modificar=True):
        return jsonify({"mensaje": "No se encontró el estudio para actualizar"}), 404

    with cursor_bd(commit=True) as cursor:
        cursor.execute("""
            SELECT Nivel AS nivel, Institucion AS institucion, Titulo AS titulo,
                   Fecha_inicio AS fecha_inicio, Fecha_finalizacion AS fecha_finalizacion,
                   Certificado AS certificado
            FROM estudios WHERE id_estudio = %s
        """, (id_estudio,))
        actual = cursor.fetchone()

        d, error = armar_estudio(leer_json(), actual)
        if error:
            return jsonify({"mensaje": error}), 400

        cursor.execute("""
            UPDATE estudios
            SET Nivel = %s, Institucion = %s, Titulo = %s, Fecha_inicio = %s,
                Fecha_finalizacion = %s, Certificado = %s
            WHERE id_estudio = %s
        """, (d["nivel"], d["institucion"], d["titulo"], d["fecha_inicio"],
              d["fecha_finalizacion"], d["certificado"], id_estudio))

    return jsonify({"mensaje": "Estudio actualizado correctamente", "id_estudio": id_estudio}), 200


@app.route("/api/eliminarestudio/<int:id_estudio>", methods=["DELETE"])
@rol_requerido("aprendiz")
def eliminar_estudio_por_id(id_estudio):
    id_personal = id_hv_de("estudios", "id_estudio", id_estudio)
    if not id_personal or verificar_acceso_hv(id_personal, modificar=True):
        return jsonify({"mensaje": "No se encontró el estudio para eliminar"}), 404
    with cursor_bd(commit=True) as cursor:
        cursor.execute("DELETE FROM estudios WHERE id_estudio = %s", (id_estudio,))
    return jsonify({"mensaje": "Estudio eliminado correctamente"}), 200


# ============================================================================
# CURSOS
# ============================================================================

def crear_curso(id_personal):
    error = verificar_acceso_hv(id_personal, modificar=True)
    if error:
        return error

    vino, nombre = enviado(leer_json(), "nombre", "Nombre")
    nombre = limpiar(nombre)
    if not nombre:
        return jsonify({"mensaje": "El nombre del curso es obligatorio"}), 400
    if len(nombre) > 150:
        return jsonify({"mensaje": "El nombre del curso admite máximo 150 caracteres"}), 400

    with cursor_bd(commit=True) as cursor:
        cursor.execute("INSERT INTO cursos (id_personal, Nombre) VALUES (%s, %s)", (id_personal, nombre))
        id_curso = cursor.lastrowid

    return jsonify({"mensaje": "Curso registrado correctamente", "id_curso": id_curso,
                    "hoja_vida_id": id_personal}), 201


# NUEVA (guía punto 8)
@app.route("/api/hojas-vida/<int:hoja_vida_id>/cursos", methods=["POST"])
@rol_requerido("aprendiz")
def registrar_curso(hoja_vida_id):
    return crear_curso(hoja_vida_id)


# ANTERIOR
@app.route("/api/registrarcurso/<int:id_personal>", methods=["POST"])
@rol_requerido("aprendiz")
def registrar_curso_hoja_vida(id_personal):
    return crear_curso(id_personal)


@app.route("/api/consultarcursos/<int:id_personal>", methods=["GET"])
@rol_requerido("reclutador", "aprendiz")
def obtener_cursos_hoja_vida(id_personal):
    error = verificar_acceso_hv(id_personal)
    if error:
        return error
    with cursor_bd() as cursor:
        cursor.execute("SELECT * FROM cursos WHERE id_personal = %s", (id_personal,))
        return jsonify(cursor.fetchall()), 200


@app.route("/api/consultarcurso/<int:id_curso>", methods=["GET"])
@rol_requerido("reclutador", "aprendiz")
def consultar_curso_por_id(id_curso):
    id_personal = id_hv_de("cursos", "id_curso", id_curso)
    if not id_personal or verificar_acceso_hv(id_personal):
        return jsonify({"mensaje": "Curso no encontrado"}), 404
    with cursor_bd() as cursor:
        cursor.execute("SELECT * FROM cursos WHERE id_curso = %s", (id_curso,))
        return jsonify(cursor.fetchone()), 200


@app.route("/api/actualizarcurso/<int:id_curso>", methods=["PUT"])
@rol_requerido("aprendiz")
def actualizar_curso_por_id(id_curso):
    id_personal = id_hv_de("cursos", "id_curso", id_curso)
    if not id_personal or verificar_acceso_hv(id_personal, modificar=True):
        return jsonify({"mensaje": "No se encontró el curso para actualizar"}), 404

    vino, nombre = enviado(leer_json(), "nombre", "Nombre")
    nombre = limpiar(nombre)
    if not nombre:
        return jsonify({"mensaje": "El nombre del curso es obligatorio"}), 400
    if len(nombre) > 150:
        return jsonify({"mensaje": "El nombre del curso admite máximo 150 caracteres"}), 400

    with cursor_bd(commit=True) as cursor:
        cursor.execute("UPDATE cursos SET Nombre = %s WHERE id_curso = %s", (nombre, id_curso))

    return jsonify({"mensaje": "Curso actualizado correctamente", "id_curso": id_curso}), 200


@app.route("/api/eliminarcurso/<int:id_curso>", methods=["DELETE"])
@rol_requerido("aprendiz")
def eliminar_curso_por_id(id_curso):
    id_personal = id_hv_de("cursos", "id_curso", id_curso)
    if not id_personal or verificar_acceso_hv(id_personal, modificar=True):
        return jsonify({"mensaje": "No se encontró el curso para eliminar"}), 404
    with cursor_bd(commit=True) as cursor:
        cursor.execute("DELETE FROM cursos WHERE id_curso = %s", (id_curso,))
    return jsonify({"mensaje": "Curso eliminado correctamente"}), 200


# ============================================================================
# EXPERIENCIAS
# ============================================================================

def crear_experiencia(id_personal):
    error = verificar_acceso_hv(id_personal, modificar=True)
    if error:
        return error

    datos = leer_json()
    d, error = armar_experiencia(datos)
    if error:
        return jsonify({"mensaje": error}), 400

    # Compatibilidad: si envían "Habilidades" (texto "a, b" o lista), se guardan en la tabla nueva
    _, habilidades = enviado(datos, "Habilidades", "habilidades")
    nombres = lista_habilidades(habilidades)

    with cursor_bd(commit=True) as cursor:
        cursor.execute("""
            INSERT INTO experiencias (id_personal, Empresa, Cargo, Area, Fecha_ingreso, Fecha_retiro,
                                      Funciones, Referencia_laboral, Certificado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (id_personal, d["empresa"], d["cargo"], d["area"], d["fecha_ingreso"],
              d["fecha_retiro"], d["funciones"], d["referencia_laboral"], d["certificado"]))
        id_experiencia = cursor.lastrowid
        if nombres:
            reemplazar_habilidades(cursor, id_experiencia, nombres)

    return jsonify({"mensaje": "Experiencia laboral registrada correctamente",
                    "id_experiencia": id_experiencia, "hoja_vida_id": id_personal}), 201


# NUEVA (guía punto 8)
@app.route("/api/hojas-vida/<int:hoja_vida_id>/experiencias", methods=["POST"])
@rol_requerido("aprendiz")
def registrar_experiencia(hoja_vida_id):
    return crear_experiencia(hoja_vida_id)


# ANTERIOR
@app.route("/api/registrarexperiencia/<int:id_personal>", methods=["POST"])
@rol_requerido("aprendiz")
def registrar_experiencia_hoja_vida(id_personal):
    return crear_experiencia(id_personal)


@app.route("/api/consultarexperiencias/<int:id_personal>", methods=["GET"])
@rol_requerido("reclutador", "aprendiz")
def obtener_experiencias_hoja_vida(id_personal):
    error = verificar_acceso_hv(id_personal)
    if error:
        return error
    with cursor_bd() as cursor:
        cursor.execute("SELECT * FROM experiencias WHERE id_personal = %s", (id_personal,))
        return jsonify(experiencias_con_texto_habilidades(cursor, cursor.fetchall())), 200


@app.route("/api/consultarexperiencia/<int:id_experiencia>", methods=["GET"])
@rol_requerido("reclutador", "aprendiz")
def consultar_experiencia_por_id(id_experiencia):
    id_personal = id_hv_de("experiencias", "id_experiencia", id_experiencia)
    if not id_personal or verificar_acceso_hv(id_personal):
        return jsonify({"mensaje": "Experiencia laboral no encontrada"}), 404
    with cursor_bd() as cursor:
        cursor.execute("SELECT * FROM experiencias WHERE id_experiencia = %s", (id_experiencia,))
        return jsonify(experiencias_con_texto_habilidades(cursor, [cursor.fetchone()])[0]), 200


@app.route("/api/actualizarexperiencia/<int:id_experiencia>", methods=["PUT"])
@rol_requerido("aprendiz")
def actualizar_experiencia_por_id(id_experiencia):
    id_personal = id_hv_de("experiencias", "id_experiencia", id_experiencia)
    if not id_personal or verificar_acceso_hv(id_personal, modificar=True):
        return jsonify({"mensaje": "No se encontró la experiencia laboral para actualizar"}), 404

    datos = leer_json()
    with cursor_bd(commit=True) as cursor:
        cursor.execute("""
            SELECT Empresa AS empresa, Cargo AS cargo, Area AS area, Fecha_ingreso AS fecha_ingreso,
                   Fecha_retiro AS fecha_retiro, Funciones AS funciones,
                   Referencia_laboral AS referencia_laboral, Certificado AS certificado
            FROM experiencias WHERE id_experiencia = %s
        """, (id_experiencia,))
        actual = cursor.fetchone()

        d, error = armar_experiencia(datos, actual)
        if error:
            return jsonify({"mensaje": error}), 400

        cursor.execute("""
            UPDATE experiencias
            SET Empresa = %s, Cargo = %s, Area = %s, Fecha_ingreso = %s, Fecha_retiro = %s,
                Funciones = %s, Referencia_laboral = %s, Certificado = %s
            WHERE id_experiencia = %s
        """, (d["empresa"], d["cargo"], d["area"], d["fecha_ingreso"], d["fecha_retiro"],
              d["funciones"], d["referencia_laboral"], d["certificado"], id_experiencia))

        # Si envían "Habilidades", se reemplazan las de esta experiencia
        vino, habilidades = enviado(datos, "Habilidades", "habilidades")
        if vino:
            reemplazar_habilidades(cursor, id_experiencia, lista_habilidades(habilidades))

    return jsonify({"mensaje": "Experiencia laboral actualizada correctamente",
                    "id_experiencia": id_experiencia}), 200


@app.route("/api/eliminarexperiencia/<int:id_experiencia>", methods=["DELETE"])
@rol_requerido("aprendiz")
def eliminar_experiencia_por_id(id_experiencia):
    id_personal = id_hv_de("experiencias", "id_experiencia", id_experiencia)
    if not id_personal or verificar_acceso_hv(id_personal, modificar=True):
        return jsonify({"mensaje": "No se encontró la experiencia laboral para eliminar"}), 404
    with cursor_bd(commit=True) as cursor:
        cursor.execute("DELETE FROM experiencias WHERE id_experiencia = %s", (id_experiencia,))
    return jsonify({"mensaje": "Experiencia laboral eliminada correctamente"}), 200


# ============================================================================
# HABILIDADES (tabla habilidades, relacionada con experiencias)
# ============================================================================

def experiencia_editable(id_experiencia):
    """None si el aprendiz puede modificar la experiencia; si no, respuesta 404."""
    id_personal = id_hv_de("experiencias", "id_experiencia", id_experiencia)
    if not id_personal or verificar_acceso_hv(id_personal, modificar=True):
        return jsonify({"mensaje": "Experiencia no encontrada"}), 404
    return None


# NUEVA (guía punto 9): registra UNA habilidad -> {"nombre": "Excel"}
@app.route("/api/experiencias/<int:experiencia_id>/habilidades", methods=["POST"])
@rol_requerido("aprendiz")
def registrar_habilidad(experiencia_id):
    nombre = limpiar(leer_json().get("nombre"))
    if not nombre:
        return jsonify({"mensaje": "El nombre de la habilidad es obligatorio"}), 400
    if len(nombre) > 100:
        return jsonify({"mensaje": "La habilidad admite máximo 100 caracteres"}), 400

    error = experiencia_editable(experiencia_id)
    if error:
        return error

    with cursor_bd(commit=True) as cursor:
        cursor.execute(
            "SELECT id FROM habilidades WHERE experiencia_id = %s AND LOWER(nombre) = LOWER(%s)",
            (experiencia_id, nombre),
        )
        if cursor.fetchone():
            return jsonify({"mensaje": "Esa habilidad ya está registrada en esta experiencia"}), 409
        cursor.execute(
            "INSERT INTO habilidades (experiencia_id, nombre) VALUES (%s, %s)",
            (experiencia_id, nombre),
        )
        id_habilidad = cursor.lastrowid

    return jsonify({"mensaje": "Habilidad registrada correctamente",
                    "id_habilidad": id_habilidad, "experiencia_id": experiencia_id}), 201


# ANTERIOR: consultar las habilidades de una experiencia
@app.route("/api/consultarhabilidades/<int:id_experiencia>", methods=["GET"])
@rol_requerido("reclutador", "aprendiz")
def obtener_habilidades_experiencia(id_experiencia):
    id_personal = id_hv_de("experiencias", "id_experiencia", id_experiencia)
    if not id_personal or verificar_acceso_hv(id_personal):
        return jsonify({"mensaje": "Experiencia laboral no encontrada"}), 404
    with cursor_bd() as cursor:
        cursor.execute(
            "SELECT id, nombre FROM habilidades WHERE experiencia_id = %s ORDER BY id",
            (id_experiencia,),
        )
        habilidades = cursor.fetchall()
    return jsonify({
        "id_experiencia": id_experiencia,
        "Habilidades": ", ".join(h["nombre"] for h in habilidades) or None,
        "habilidades": habilidades,
    }), 200


# ANTERIOR: agregar habilidades -> {"Habilidades": "Excel, Word"} o {"nombre": "Excel"}
@app.route("/api/registrarhabilidad/<int:id_experiencia>", methods=["POST"])
@rol_requerido("aprendiz")
def registrar_habilidad_experiencia(id_experiencia):
    datos = leer_json()
    _, valor = enviado(datos, "Habilidades", "habilidades", "nombre")
    nombres = lista_habilidades(valor)
    if not nombres:
        return jsonify({"mensaje": "Envía 'Habilidades' (ej: \"Excel, Word\") o 'nombre'"}), 400

    error = experiencia_editable(id_experiencia)
    if error:
        return error

    with cursor_bd(commit=True) as cursor:
        cursor.execute("SELECT nombre FROM habilidades WHERE experiencia_id = %s", (id_experiencia,))
        existentes = [h["nombre"].lower() for h in cursor.fetchall()]
        for nombre in nombres:
            if nombre.lower() not in existentes:
                cursor.execute(
                    "INSERT INTO habilidades (experiencia_id, nombre) VALUES (%s, %s)",
                    (id_experiencia, nombre),
                )

    return jsonify({"mensaje": "Habilidad registrada correctamente",
                    "id_experiencia": id_experiencia}), 200


# ANTERIOR: reemplazar todas las habilidades -> {"Habilidades": "Excel, Python"}
@app.route("/api/actualizarhabilidad/<int:id_experiencia>", methods=["PUT"])
@rol_requerido("aprendiz")
def actualizar_habilidad_experiencia(id_experiencia):
    _, valor = enviado(leer_json(), "Habilidades", "habilidades")
    nombres = lista_habilidades(valor)
    if not nombres:
        return jsonify({"mensaje": "Envía 'Habilidades' (ej: \"Excel, Python\")"}), 400

    error = experiencia_editable(id_experiencia)
    if error:
        return error

    with cursor_bd(commit=True) as cursor:
        reemplazar_habilidades(cursor, id_experiencia, nombres)

    return jsonify({"mensaje": "Habilidades actualizadas correctamente",
                    "id_experiencia": id_experiencia}), 200


# ANTERIOR: eliminar todas las habilidades de una experiencia
@app.route("/api/eliminarhabilidad/<int:id_experiencia>", methods=["DELETE"])
@rol_requerido("aprendiz")
def eliminar_habilidad_experiencia(id_experiencia):
    error = experiencia_editable(id_experiencia)
    if error:
        return error
    with cursor_bd(commit=True) as cursor:
        cursor.execute("DELETE FROM habilidades WHERE experiencia_id = %s", (id_experiencia,))
    return jsonify({"mensaje": "Habilidades eliminadas de la experiencia correctamente"}), 200


# ============================================================================
# MANEJO DE ERRORES
# ============================================================================

@app.errorhandler(mysql.connector.Error)
def error_mysql(error):
    app.logger.exception(error)
    numero = getattr(error, "errno", None)

    if numero in (2003, 2005, 2013):
        return jsonify({"mensaje": "No se pudo conectar a MySQL. ¿Está encendido MySQL en XAMPP?"}), 503
    if numero == 1049:
        return jsonify({"mensaje": f"No existe la base de datos '{Config.DB_NAME}'. Revisa DB_NAME en el .env"}), 503
    if numero in (1146, 1054):
        return jsonify({
            "mensaje": "Falta una tabla o columna en la base de datos. "
                       "Ejecuta el script sql/actualizacion.sql en phpMyAdmin",
            "detalle": str(error.msg),
        }), 500
    if numero == 1062:
        return jsonify({"mensaje": "Ya existe un registro con esos datos"}), 409
    return jsonify({"mensaje": "Error en la base de datos", "detalle": str(error.msg)}), 500


@app.errorhandler(404)
def no_encontrado(_error):
    return jsonify({"mensaje": "Ruta no encontrada"}), 404


@app.errorhandler(405)
def metodo_no_permitido(_error):
    return jsonify({"mensaje": "Método HTTP no permitido en esta ruta"}), 405


@app.errorhandler(500)
def error_interno(_error):
    return jsonify({"mensaje": "Error interno del servidor"}), 500


if __name__ == "__main__":
    app.run(debug=True)