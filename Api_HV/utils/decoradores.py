# utils/decoradores.py
# Decorador rol_requerido: exige un token JWT válido y comprueba el rol.

from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required


def rol_requerido(*roles):
    """
    Uso:
        @rol_requerido("reclutador")
        @rol_requerido("aprendiz")
        @rol_requerido("aprendiz", "reclutador")   # cualquiera de los dos

    - Sin token o token inválido -> 401 (lo responde flask_jwt_extended)
    - Token válido pero rol distinto -> 403 Forbidden
    """

    def decorador(funcion):
        @wraps(funcion)
        @jwt_required()
        def wrapper(*args, **kwargs):
            claims = get_jwt()
            if claims.get("rol") not in roles:
                return jsonify({
                    "mensaje": "No tienes permisos para acceder"
                }), 403
            return funcion(*args, **kwargs)

        return wrapper

    return decorador


def usuario_actual_id():
    """Devuelve el id del usuario que viene dentro del token."""
    return int(get_jwt_identity())


def rol_actual():
    """Devuelve el rol que viene dentro del token."""
    return get_jwt().get("rol")
