# routes/auth.py
# Registro público (aprendiz), inicio de sesión (JWT) y datos de la sesión.

from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, jwt_required
from werkzeug.security import check_password_hash, generate_password_hash

from models import hoja_vida_model, usuario_model
from utils.decoradores import usuario_actual_id
from utils.validaciones import es_correo_valido

auth_bp = Blueprint("auth", __name__)


def _usuario_publico(usuario):
    """Datos del usuario que se pueden enviar al frontend (sin contraseña)."""
    return {
        "id": usuario["id"],
        "nombre": usuario["nombre"],
        "correo": usuario["correo"],
        "rol": usuario["rol"],
    }


def _generar_token(usuario):
    """El token guarda la identidad (id) y el rol del usuario."""
    return create_access_token(
        identity=str(usuario["id"]),
        additional_claims={"rol": usuario["rol"]},
    )


# ---------------------------------------------------------------------------
# 2. REGISTRO PÚBLICO: crea la cuenta SIEMPRE con rol aprendiz
# ---------------------------------------------------------------------------
@auth_bp.route("/api/registro-usuario", methods=["POST"])
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

    # Validar longitud mínima
    if len(password) < 8:
        return jsonify({"mensaje": "Mínimo 8 caracteres"}), 400

    if len(password) > 128:
        return jsonify({"mensaje": "La contraseña no puede superar 128 caracteres"}), 400

    # Verificar correo duplicado
    if usuario_model.correo_existe(correo):
        return jsonify({"mensaje": "Este correo ya está registrado"}), 409

    # El registro público siempre crea un aprendiz y guarda la contraseña como hash
    password_hash = generate_password_hash(password)
    nuevo_id = usuario_model.crear_aprendiz(nombre, correo, password_hash)

    usuario = {"id": nuevo_id, "nombre": nombre, "correo": correo, "rol": "aprendiz"}

    # Se devuelve también el token para que React inicie sesión de una vez
    return jsonify({
        "mensaje": "Cuenta creada correctamente",
        "token": _generar_token(usuario),
        "usuario": usuario,
    }), 201


# ---------------------------------------------------------------------------
# 4. INICIO DE SESIÓN: verifica credenciales y genera el token JWT
# ---------------------------------------------------------------------------
@auth_bp.route("/api/login", methods=["POST"])
def login():
    datos = request.get_json(silent=True) or {}
    correo = str(datos.get("correo", "")).strip().lower()
    password = str(datos.get("password", ""))

    if not correo or not password:
        return jsonify({"mensaje": "Ingresa el correo y la contraseña"}), 400

    usuario = usuario_model.buscar_por_correo(correo)

    if not usuario or not check_password_hash(usuario["password"], password):
        return jsonify({"mensaje": "Correo o contraseña incorrectos"}), 401

    if not usuario["estado"]:
        return jsonify({"mensaje": "Cuenta desactivada"}), 403

    return jsonify({
        "mensaje": "Inicio de sesión correcto",
        "token": _generar_token(usuario),
        "usuario": _usuario_publico(usuario),
    }), 200


# ---------------------------------------------------------------------------
# EXTRA: datos de la sesión actual (React lo usa al recargar la página)
# ---------------------------------------------------------------------------
@auth_bp.route("/api/me", methods=["GET"])
@jwt_required()
def mi_sesion():
    usuario = usuario_model.buscar_por_id(usuario_actual_id())

    if not usuario:
        return jsonify({"mensaje": "El usuario ya no existe"}), 401

    if not usuario["estado"]:
        return jsonify({"mensaje": "Cuenta desactivada"}), 403

    hoja_vida_id = None
    if usuario["rol"] == "aprendiz":
        hoja = hoja_vida_model.obtener_por_usuario(usuario["id"])
        hoja_vida_id = hoja["id"] if hoja else None

    return jsonify({
        "usuario": _usuario_publico(usuario),
        "hoja_vida_id": hoja_vida_id,
    }), 200
