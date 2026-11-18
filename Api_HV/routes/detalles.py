# routes/detalles.py
# 8. Estudios, cursos y experiencias asociados a una hoja de vida (hoja_vida_id)
# 9. Habilidades asociadas a una experiencia (experiencia_id)
#
# Solo el aprendiz dueño de la hoja de vida puede agregar registros.

from flask import Blueprint, jsonify, request

from models import detalle_model, hoja_vida_model
from utils.decoradores import rol_requerido, usuario_actual_id
from utils.validaciones import (
    faltantes,
    fecha_opcional,
    texto,
    texto_opcional,
    validar_rango_fechas,
)

detalles_bp = Blueprint("detalles", __name__)


def _hoja_no_propia(hoja_vida_id):
    """Devuelve una respuesta 404 si la hoja de vida no es del aprendiz; si es suya, None."""
    if not hoja_vida_model.pertenece_a_usuario(hoja_vida_id, usuario_actual_id()):
        return jsonify({"mensaje": "Hoja de vida no encontrada"}), 404
    return None


# ---------------------------------------------------------------------------
# ESTUDIOS
# ---------------------------------------------------------------------------
@detalles_bp.route("/api/hojas-vida/<int:hoja_vida_id>/estudios", methods=["POST"])
@rol_requerido("aprendiz")
def registrar_estudio(hoja_vida_id):
    error = _hoja_no_propia(hoja_vida_id)
    if error:
        return error

    datos = request.get_json(silent=True) or {}
    d = {
        "nivel": texto(datos, "nivel", "Nivel"),
        "institucion": texto(datos, "institucion", "Institucion"),
        "titulo": texto(datos, "titulo", "Titulo"),
        "certificado": texto_opcional(datos, "certificado", "Certificado"),
    }

    vacios = faltantes({"nivel": d["nivel"], "institucion": d["institucion"], "titulo": d["titulo"]})
    if vacios:
        return jsonify({"mensaje": "Faltan campos obligatorios: " + ", ".join(vacios)}), 400

    if len(d["nivel"]) > 50 or len(d["institucion"]) > 150 or len(d["titulo"]) > 150:
        return jsonify({"mensaje": "Algún campo supera la longitud permitida"}), 400

    d["fecha_inicio"], err1 = fecha_opcional(
        texto(datos, "fecha_inicio", "Fecha_inicio"), "fecha de inicio")
    d["fecha_finalizacion"], err2 = fecha_opcional(
        texto(datos, "fecha_finalizacion", "Fecha_finalizacion"), "fecha de finalización")
    err3 = validar_rango_fechas(
        d["fecha_inicio"], d["fecha_finalizacion"], "fecha de inicio", "fecha de finalización")
    if err1 or err2 or err3:
        return jsonify({"mensaje": err1 or err2 or err3}), 400

    id_estudio = detalle_model.crear_estudio(hoja_vida_id, d)
    return jsonify({
        "mensaje": "Estudio registrado correctamente",
        "id_estudio": id_estudio,
        "hoja_vida_id": hoja_vida_id,
    }), 201


# ---------------------------------------------------------------------------
# CURSOS
# ---------------------------------------------------------------------------
@detalles_bp.route("/api/hojas-vida/<int:hoja_vida_id>/cursos", methods=["POST"])
@rol_requerido("aprendiz")
def registrar_curso(hoja_vida_id):
    error = _hoja_no_propia(hoja_vida_id)
    if error:
        return error

    datos = request.get_json(silent=True) or {}
    nombre = texto(datos, "nombre", "Nombre")

    if not nombre:
        return jsonify({"mensaje": "El nombre del curso es obligatorio"}), 400
    if len(nombre) > 150:
        return jsonify({"mensaje": "El nombre del curso admite máximo 150 caracteres"}), 400

    id_curso = detalle_model.crear_curso(hoja_vida_id, nombre)
    return jsonify({
        "mensaje": "Curso registrado correctamente",
        "id_curso": id_curso,
        "hoja_vida_id": hoja_vida_id,
    }), 201


# ---------------------------------------------------------------------------
# EXPERIENCIAS
# ---------------------------------------------------------------------------
@detalles_bp.route("/api/hojas-vida/<int:hoja_vida_id>/experiencias", methods=["POST"])
@rol_requerido("aprendiz")
def registrar_experiencia(hoja_vida_id):
    error = _hoja_no_propia(hoja_vida_id)
    if error:
        return error

    datos = request.get_json(silent=True) or {}
    d = {
        "empresa": texto(datos, "empresa", "Empresa"),
        "cargo": texto(datos, "cargo", "Cargo"),
        "area": texto_opcional(datos, "area", "Area"),
        "funciones": texto_opcional(datos, "funciones", "Funciones"),
        "referencia_laboral": texto_opcional(datos, "referencia_laboral", "Referencia_laboral"),
        "certificado": texto_opcional(datos, "certificado", "Certificado"),
    }

    vacios = faltantes({"empresa": d["empresa"], "cargo": d["cargo"]})
    if vacios:
        return jsonify({"mensaje": "Faltan campos obligatorios: " + ", ".join(vacios)}), 400

    if len(d["empresa"]) > 150 or len(d["cargo"]) > 100 or len(d["area"] or "") > 100:
        return jsonify({"mensaje": "Algún campo supera la longitud permitida"}), 400

    # fecha_retiro vacía o null = trabaja actualmente allí
    d["fecha_ingreso"], err1 = fecha_opcional(
        texto(datos, "fecha_ingreso", "Fecha_ingreso"), "fecha de ingreso")
    d["fecha_retiro"], err2 = fecha_opcional(
        texto(datos, "fecha_retiro", "Fecha_retiro"), "fecha de retiro")
    err3 = validar_rango_fechas(
        d["fecha_ingreso"], d["fecha_retiro"], "fecha de ingreso", "fecha de retiro")
    if err1 or err2 or err3:
        return jsonify({"mensaje": err1 or err2 or err3}), 400

    id_experiencia = detalle_model.crear_experiencia(hoja_vida_id, d)
    return jsonify({
        "mensaje": "Experiencia laboral registrada correctamente",
        "id_experiencia": id_experiencia,
        "hoja_vida_id": hoja_vida_id,
    }), 201


# ---------------------------------------------------------------------------
# 9. HABILIDADES: se asocian a una experiencia mediante experiencia_id
# ---------------------------------------------------------------------------
@detalles_bp.route("/api/experiencias/<int:experiencia_id>/habilidades", methods=["POST"])
@rol_requerido("aprendiz")
def registrar_habilidad(experiencia_id):
    usuario_id = usuario_actual_id()
    datos = request.get_json(silent=True) or {}
    nombre = texto(datos, "nombre", "Nombre")

    if not nombre:
        return jsonify({"mensaje": "El nombre de la habilidad es obligatorio"}), 400
    if len(nombre) > 100:
        return jsonify({"mensaje": "La habilidad admite máximo 100 caracteres"}), 400

    # Verificar que la experiencia pertenece al aprendiz
    if not detalle_model.experiencia_pertenece_a_usuario(experiencia_id, usuario_id):
        return jsonify({"mensaje": "Experiencia no encontrada"}), 404

    if detalle_model.habilidad_existe(experiencia_id, nombre):
        return jsonify({"mensaje": "Esa habilidad ya está registrada en esta experiencia"}), 409

    id_habilidad = detalle_model.crear_habilidad(experiencia_id, nombre)
    return jsonify({
        "mensaje": "Habilidad registrada correctamente",
        "id_habilidad": id_habilidad,
        "experiencia_id": experiencia_id,
    }), 201
