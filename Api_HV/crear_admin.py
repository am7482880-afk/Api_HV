# crear_admin.py
# Crea el usuario con rol RECLUTADOR desde la terminal.
# El reclutador NO se registra desde el formulario público.
#
# Uso (en la carpeta Api_HV):
#     python crear_admin.py

from getpass import getpass

from werkzeug.security import generate_password_hash

from database import conectar_bd
from utils.validaciones import es_correo_valido


def crear_administrador():
    print("=== Crear usuario RECLUTADOR ===")
    nombre = input("Nombre del reclutador: ").strip()
    correo = input("Correo electrónico: ").strip().lower()
    password = getpass("Contraseña (no se ve mientras escribes): ")

    if not nombre or not correo or len(password) < 8:
        print("Verifica los datos. La clave requiere mínimo 8 caracteres")
        return

    if not es_correo_valido(correo):
        print("El correo no tiene un formato válido")
        return

    confirmar = getpass("Confirma la contraseña: ")
    if confirmar != password:
        print("Las contraseñas no coinciden")
        return

    conexion = conectar_bd()
    cursor = conexion.cursor()

    try:
        cursor.execute("SELECT id FROM usuarios WHERE correo = %s", (correo,))
        if cursor.fetchone():
            print("Este correo ya está registrado")
            return

        password_hash = generate_password_hash(password)
        sql = """
            INSERT INTO usuarios
            (nombre, correo, password, rol, estado)
            VALUES (%s, %s, %s, 'reclutador', 1)
        """
        cursor.execute(sql, (nombre, correo, password_hash))
        conexion.commit()
        print(f"Reclutador creado correctamente (id {cursor.lastrowid})")

    except Exception as error:
        conexion.rollback()
        print("Error:", error)
    finally:
        cursor.close()
        conexion.close()


if __name__ == "__main__":
    crear_administrador()
