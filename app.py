from flask import Flask, request
from database import conectar_bd

app = Flask(__name__)


@app.route("/")
def inicio():
    return "Api hoja de vida funcionando"

@app.route("/probar")
def probar_data():
    conexion = conectar_bd()
    if conexion.is_connected():
        conexion.close()
        return {
            "Mensaje": "Conexion ok"
        }


#CONSULTAR HOJA DE VIDA POR ID
@app.route("/api/consultarhv/<int:id>", methods=["GET"])
def obtenerhv(id):
    conexion = conectar_bd()
    cursor = conexion.cursor(dictionary=True)
    
    sql = ("SELECT * FROM Personal WHERE id_personal = %s")
    cursor.execute(sql,(id,))
    datos = cursor.fetchone()

    cursor.close()
    conexion.close()

    if datos is None:
        return{"No se encontro hoja de vida"}

    return datos


#ELIMINAR HOJA DE VIDA POR ID
@app.route("/api/eliminarhv/<int:id>", methods=["DELETE"])
def eliminarhv(id):
    conexion = conectar_bd()
    cursor = conexion.cursor(dictionary=True)
    
    sql = "DELETE FROM personal WHERE id_personal = %s"
    cursor.execute(sql, (id,))
    conexion.commit()
    
    eliminadas = cursor.rowcount
    
    cursor.close()
    conexion.close()
    
    if eliminadas == 0:
        return {"mensaje": "No se encontró esa hoja de vida"}, 404
        
    return {"mensaje": "Hoja de vida eliminada correctamente"}, 200

#ACTUALIZAR HOJA DE VIDA POR ID
@app.route("/api/actualizarhv/<int:id>", methods=["PUT"])


@app.route("/api/registrohv", methods=["POST"])
def registrohojavida():
    conexion = conectar_bd()
    cursor = conexion.cursor()
    datos = request.json

    # Consultar si el correo ya existe en la tabla 'personal'
    buscar = "SELECT id_personal, Nombres FROM personal WHERE Correo = %s"
    cursor.execute(buscar, (datos["Correo"],))
    usu = cursor.fetchone()

    if usu:
        cursor.close()
        conexion.close()
        return {
            "Mensaje": "El usuario ya existe"
        }

    # Insertar en la tabla 'personal' con los campos exactos de tu BD
    sql = """
        INSERT INTO personal (Fotografia, Nombres, Apellidos, Correo, Direccion, Perfil_Profesional)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    valor = (
        datos.get("Fotografia"),
        datos["Nombres"],
        datos["Apellidos"],
        datos["Correo"],
        datos.get("Direccion"),
        datos.get("Perfil_Profesional")
    )

    cursor.execute(sql, valor)
    conexion.commit()

    # Manejo del ID generado para la persona
    id_generado = cursor.lastrowid

    cursor.close()
    conexion.close()

    return {
        "Mensaje": "Hoja de vida creada correctamente",
        "id": id_generado
    }

# -------------------------------------------------------------
# OBTENER UNA HOJA DE VIDA DESDE LA BD POR ID
# -------------------------------------------------------------
@app.route("/api/hojas-vida/<int:id>")
def obtener_hojasvidaid(id):
    conexion = conectar_bd()
    cursor = conexion.cursor(dictionary=True)

    # Consulta a la tabla 'personal' según tu clave primaria id_personal
    sql = "SELECT * FROM personal WHERE id_personal = %s"
    cursor.execute(sql, (id,))
    persona = cursor.fetchone()

    cursor.close()
    conexion.close()

    if persona:
        return {
            "Mensaje": "Hoja de vida encontrada",
            "datos": persona
        }
    return {
        "Mensaje": "Hoja de vida no encontrada"
    }


@app.route("/api/hoja-vida")
def obtener_hojasvida():
    hojas_vida =[
                {
            "id_personal": 1,
            "Fotografia": "foto1.jpg",
            "Nombres": "Ana",
            "Apellidos": "Muñoz",
            "Correo": "nana@gmail.com",
            "Direccion": "Calle 100 # 15-20",
            "Perfil_Profesional": "Desarrollador Tecnólogo en ADSO con experiencia en Python y React"
        },
        {
            "id_personal": 2,
            "Fotografia": "foto2.jpg",
            "Nombres": "Erik",
            "Apellidos": "Espitia",
            "Correo": "erik626@gmail.com",
            "Direccion": "Carrera 7 # 45-10",
            "Perfil_Profesional": "Diseñador y productor multimedia"
        },
        {
            "id_personal": 3,
            "Fotografia": "foto3.jpg",
            "Nombres": "Sara",
            "Apellidos": "Cely",
            "Correo": "sara625@gmail.com",
            "Direccion": "Carrera 7 # 45-10",
            "Perfil_Profesional": "Animacion 3D"
        }
    ]
    return hojas_vida

# -------------------------------------------------------------
# LISTAR TODAS LAS HOJAS DE VIDA REGISTRADAS EN BD
# -------------------------------------------------------------
@app.route("/api/listarhv")
def listar_hojasvida():
    conexion = conectar_bd()
    cursor = conexion.cursor(dictionary=True)

    sql = "SELECT * FROM personal"
    cursor.execute(sql)

    hojas_vida = cursor.fetchall()

    cursor.close()
    conexion.close()

    return hojas_vida


if __name__ == "__main__":
    app.run(debug=True)