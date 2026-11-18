# routes/hojas_vida.py
# Registro de la hoja de vida (aprendiz), consulta de la hoja propia
# y consultas del reclutador.

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from models import hoja_vida_model
from utils.decoradores import rol_actual, rol_requerido, usuario_actual_id
from utils.validaciones import (
    JORNADAS_VALIDAS,
    entero_opcional,
    es_correo_valido,
    faltantes,
    texto,
    texto_opcional,
)

hojas_vida_bp = Blueprint("hojas_vida", __name__)


def _leer_datos_hoja_vida(datos):
    """
    Lee y valida los datos personales.
    Acepta las claves en minúscula (nombres, correo...) o como estaban
    antes en el proyecto (Nombres, Correo...).
    Devuelve (diccionario_limpio, mensaje_de_error).
    """
    d = {
        "nombres": texto(datos, "nombres", "Nombres", "nombre"),
        "apellidos": texto(datos, "apellidos", "Apellidos"),
        "correo": texto(datos, "correo", "Correo").lower(),
        "direccion": texto_opcional(datos, "direccion", "Direccion"),
        "perfil_profesional": texto_opcional(datos, "perfil_profesional", "Perfil_Profesional"),
        "fotografia": texto_opcional(datos, "fotografia", "Fotografia"),
        "ciudad": texto(datos, "ciudad", "Ciudad"),
        "programa": texto(datos, "programa", "Programa"),
        "ficha": texto(datos, "ficha", "Ficha"),
        "jornada": texto(datos, "jornada", "Jornada"),
    }
    edad_texto = texto(datos, "edad", "Edad")

    vacios = faltantes({
        "nombres": d["nombres"],
        "apellidos": d["apellidos"],
        "correo": d["correo"],
        "edad": edad_texto,
        "ciudad": d["ciudad"],
        "programa": d["programa"],
        "ficha": d["ficha"],
        "jornada": d["jornada"],
    })
    if vacios:
        return None, "Faltan campos obligatorios: " + ", ".join(vacios)

    if len(d["nombres"]) > 100 or len(d["apellidos"]) > 100:
        return None, "Nombres y apellidos admiten máximo 100 caracteres"

    if not es_correo_valido(d["correo"]):
        return None, "El correo no tiene un formato válido"

    edad, valida = entero_opcional(edad_texto)
    if not valida or edad < 14 or edad > 100:
        return None, "La edad debe ser un número entre 14 y 100"
    d["edad"] = edad

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


# ---------------------------------------------------------------------------
# 6. REGISTRAR DATOS BÁSICOS: el usuario_id se toma del token
# ---------------------------------------------------------------------------
@hojas_vida_bp.route("/api/registrohv", methods=["POST"])
@jwt_required()
def registrohv():
    usuario_id = usuario_actual_id()

    if rol_actual() != "aprendiz":
        return jsonify({"mensaje": "Solo los aprendices pueden registrar HV"}), 403

    datos = request.get_json(silent=True)
    if not datos:
        return jsonify({"mensaje": "No se recibieron datos"}), 400

    d, error = _leer_datos_hoja_vida(datos)
    if error:
        return jsonify({"mensaje": error}), 400

    existente = hoja_vida_model.obtener_por_usuario(usuario_id)
    if existente:
        return jsonify({
            "mensaje": "Ya tienes una hoja de vida registrada",
            "hoja_vida_id": existente["id"],
        }), 409

    if hoja_vida_model.correo_en_uso(d["correo"]):
        return jsonify({"mensaje": "Ese correo ya está registrado en otra hoja de vida"}), 409

    hoja_vida_id = hoja_vida_model.crear(usuario_id, d)

    return jsonify({
        "mensaje": "Hoja de vida registrada correctamente",
        "hoja_vida_id": hoja_vida_id,
    }), 201


# ---------------------------------------------------------------------------
# 7. CONSULTAR LA HOJA DE VIDA PROPIA (completa)
# ---------------------------------------------------------------------------
@hojas_vida_bp.route("/api/mi-hoja-vida", methods=["GET"])
@jwt_required()
def mi_hoja_vida():
    usuario_id = usuario_actual_id()

    if rol_actual() != "aprendiz":
        return jsonify({"mensaje": "Consulta exclusiva para aprendices"}), 403

    hv = hoja_vida_model.obtener_por_usuario(usuario_id)
    if not hv:
        return jsonify({"mensaje": "Aún no has registrado tu hoja de vida"}), 404

    return jsonify(hoja_vida_model.obtener_completa(hv["id"])), 200


# ---------------------------------------------------------------------------
# 5. LISTADO GENERAL: solo reclutador (el aprendiz recibe 403)
# ---------------------------------------------------------------------------
@hojas_vida_bp.route("/api/hojas-vida", methods=["GET"])
@rol_requerido("reclutador")
def obtener_hojas():
    # Solo un reclutador con token válido llega aquí
    hojas = hoja_vida_model.listar()
    return jsonify({"total": len(hojas), "hojas_vida": hojas}), 200


# ---------------------------------------------------------------------------
# EXTRA: el reclutador consulta una hoja de vida completa
# ---------------------------------------------------------------------------
@hojas_vida_bp.route("/api/hojas-vida/<int:hoja_vida_id>", methods=["GET"])
@rol_requerido("reclutador")
def obtener_hoja_completa(hoja_vida_id):
    hoja = hoja_vida_model.obtener_completa(hoja_vida_id)
    if not hoja:
        return jsonify({"mensaje": "Hoja de vida no encontrada"}), 404
    return jsonify(hoja), 200
