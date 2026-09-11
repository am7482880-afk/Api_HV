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
@app.route("/api/actualizar_hoja_vida/<int:id>", methods=["PUT"])
def actualizar_hoja_vida(id):
    conexion = conectar_bd()
    cursor = conexion.cursor()
    datos = request.json
    buscar_sql = "SELECT id_personal FROM Personal WHERE Correo = %s AND id_personal != %s"
    cursor.execute(buscar_sql, (datos.get("correo"), id))
    hoja_vida_existente = cursor.fetchone()

    if hoja_vida_existente:
        cursor.close()
        conexion.close()
        return {"mensaje": "El correo ya está registrado por otra hoja de vida"}, 400

    sql = """
        UPDATE Personal 
        SET Fotografia = %s, Nombres = %s, Apellidos = %s, Correo = %s, Direccion = %s, Perfil_Profesional = %s 
        WHERE id_personal = %s
    """
    valor = (
        datos.get("foto"),
        datos.get("nombres"),
        datos.get("apellidos"),
        datos.get("correo"),
        datos.get("direccion"),
        datos.get("perfil_profesional"),
        id
    )

    cursor.execute(sql, valor)

    if cursor.rowcount == 0:
        cursor.close()
        conexion.close()
        return {"mensaje": "No se encontró la hoja de vida con el ID proporcionado"}, 404

    conexion.commit()
    cursor.close()
    conexion.close()

    return {
        "mensaje": "Hoja de vida actualizada correctamente",
        "id_personal": id
    }
    

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

    id_generado = cursor.lastrowid

    cursor.close()
    conexion.close()

    return {
        "Mensaje": "Hoja de vida creada correctamente",
        "id": id_generado
    }

# OBTENER UNA HOJA DE VIDA DESDE LA BD POR ID
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

#CONSULTAR ESTUDIOS
# Consultar todos los estudios asociados a una hoja de vida
@app.route("/api/consultarestudios/<int:id_personal>", methods=["GET"])
def obtener_estudios_hoja_vida(id_personal):
    conexion = conectar_bd()
    cursor = conexion.cursor(dictionary=True)

    sql = "SELECT * FROM Estudios WHERE id_personal = %s"
    cursor.execute(sql, (id_personal,))
    estudios = cursor.fetchall()

    cursor.close()
    conexion.close()

    return estudios, 200


# Registrar un nuevo estudio para una hoja de vida
@app.route("/api/registrarestudio/<int:id_personal>", methods=["POST"])
def registrar_estudio_hoja_vida(id_personal):
    conexion = conectar_bd()
    cursor = conexion.cursor()
    datos = request.json

    cursor.execute("SELECT id_personal FROM Personal WHERE id_personal = %s", (id_personal,))
    if not cursor.fetchone():
        cursor.close()
        conexion.close()
        return {"mensaje": "La hoja de vida especificada no existe"}, 404

    sql = """
        INSERT INTO Estudios (id_personal, Nivel, Institucion, Titulo, Fecha_inicio, Fecha_finalizacion, Certificado)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    valores = (
        id_personal,
        datos.get("Nivel"),
        datos.get("Institucion"),
        datos.get("Titulo"),
        datos.get("Fecha_inicio"),
        datos.get("Fecha_finalizacion"),
        datos.get("Certificado")
    )

    cursor.execute(sql, valores)
    conexion.commit()

    id_estudio = cursor.lastrowid

    cursor.close()
    conexion.close()

    return {
        "mensaje": "Estudio registrado correctamente",
        "id_estudio": id_estudio
    }, 201


# Consultar un estudio específico
@app.route("/api/consultarestudio/<int:id_estudio>", methods=["GET"])
def consultar_estudio_por_id(id_estudio):
    conexion = conectar_bd()
    cursor = conexion.cursor(dictionary=True)

    sql = "SELECT * FROM Estudios WHERE id_estudio = %s"
    cursor.execute(sql, (id_estudio,))
    estudio = cursor.fetchone()

    cursor.close()
    conexion.close()

    if not estudio:
        return {"mensaje": "Estudio no encontrado"}, 404

    return estudio, 200


# Actualizar un estudio
@app.route("/api/actualizarestudio/<int:id_estudio>", methods=["PUT"])
def actualizar_estudio_por_id(id_estudio):
    conexion = conectar_bd()
    cursor = conexion.cursor()
    datos = request.json

    sql = """
        UPDATE Estudios
        SET Nivel = %s, Institucion = %s, Titulo = %s, Fecha_inicio = %s, Fecha_finalizacion = %s, Certificado = %s
        WHERE id_estudio = %s
    """
    valores = (
        datos.get("Nivel"),
        datos.get("Institucion"),
        datos.get("Titulo"),
        datos.get("Fecha_inicio"),
        datos.get("Fecha_finalizacion"),
        datos.get("Certificado"),
        id_estudio
    )

    cursor.execute(sql, valores)

    if cursor.rowcount == 0:
        cursor.close()
        conexion.close()
        return {"mensaje": "No se encontró el estudio para actualizar"}, 404

    conexion.commit()
    cursor.close()
    conexion.close()

    return {
        "mensaje": "Estudio actualizado correctamente",
        "id_estudio": id_estudio
    }, 200


# Eliminar un estudio
@app.route("/api/eliminarestudio/<int:id_estudio>", methods=["DELETE"])
def eliminar_estudio_por_id(id_estudio):
    conexion = conectar_bd()
    cursor = conexion.cursor()

    sql = "DELETE FROM Estudios WHERE id_estudio = %s"
    cursor.execute(sql, (id_estudio,))

    if cursor.rowcount == 0:
        cursor.close()
        conexion.close()
        return {"mensaje": "No se encontró el estudio para eliminar"}, 404

    conexion.commit()
    cursor.close()
    conexion.close()

    return {"mensaje": "Estudio eliminado correctamente"}, 200

# GESTIÓN DE EXPERIENCIA LABORAL

# Consultar las experiencias laborales de una hoja de vida
@app.route("/api/consultarexperiencias/<int:id_personal>", methods=["GET"])
def obtener_experiencias_hoja_vida(id_personal):
    conexion = conectar_bd()
    cursor = conexion.cursor(dictionary=True)

    sql = "SELECT * FROM Experiencias WHERE id_personal = %s"
    cursor.execute(sql, (id_personal,))
    experiencias = cursor.fetchall()

    cursor.close()
    conexion.close()

    return experiencias, 200


# Registrar una experiencia laboral 
@app.route("/api/registrarexperiencia/<int:id_personal>", methods=["POST"])
def registrar_experiencia_hoja_vida(id_personal):
    conexion = conectar_bd()
    cursor = conexion.cursor()
    datos = request.json

    cursor.execute("SELECT id_personal FROM Personal WHERE id_personal = %s", (id_personal,))
    if not cursor.fetchone():
        cursor.close()
        conexion.close()
        return {"mensaje": "La hoja de vida especificada no existe"}, 404

    sql = """
        INSERT INTO Experiencias (id_personal, Empresa, Cargo, Area, Fecha_ingreso, Fecha_retiro, Funciones, Referencia_laboral, Certificado, Habilidades)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    valores = (
        id_personal,
        datos.get("Empresa"),
        datos.get("Cargo"),
        datos.get("Area"),
        datos.get("Fecha_ingreso"),
        datos.get("Fecha_retiro"),
        datos.get("Funciones"),
        datos.get("Referencia_laboral"),
        datos.get("Certificado"),
        datos.get("Habilidades")
    )

    cursor.execute(sql, valores)
    conexion.commit()

    id_experiencia = cursor.lastrowid

    cursor.close()
    conexion.close()

    return {
        "mensaje": "Experiencia laboral registrada correctamente",
        "id_experiencia": id_experiencia
    }, 201


# Consultar una experiencia específica
@app.route("/api/consultarexperiencia/<int:id_experiencia>", methods=["GET"])
def consultar_experiencia_por_id(id_experiencia):
    conexion = conectar_bd()
    cursor = conexion.cursor(dictionary=True)

    sql = "SELECT * FROM Experiencias WHERE id_experiencia = %s"
    cursor.execute(sql, (id_experiencia,))
    experiencia = cursor.fetchone()

    cursor.close()
    conexion.close()

    if not experiencia:
        return {"mensaje": "Experiencia laboral no encontrada"}, 404

    return experiencia, 200


# Actualizar una experiencia 
@app.route("/api/actualizarexperiencia/<int:id_experiencia>", methods=["PUT"])
def actualizar_experiencia_por_id(id_experiencia):
    conexion = conectar_bd()
    cursor = conexion.cursor()
    datos = request.json

    sql = """
        UPDATE Experiencias
        SET Empresa = %s, Cargo = %s, Area = %s, Fecha_ingreso = %s, Fecha_retiro = %s, Funciones = %s, Referencia_laboral = %s, Certificado = %s, Habilidades = %s
        WHERE id_experiencia = %s
    """
    valores = (
        datos.get("Empresa"),
        datos.get("Cargo"),
        datos.get("Area"),
        datos.get("Fecha_ingreso"),
        datos.get("Fecha_retiro"),
        datos.get("Funciones"),
        datos.get("Referencia_laboral"),
        datos.get("Certificado"),
        datos.get("Habilidades"),
        id_experiencia
    )

    cursor.execute(sql, valores)

    if cursor.rowcount == 0:
        cursor.close()
        conexion.close()
        return {"mensaje": "No se encontró la experiencia laboral para actualizar"}, 404

    conexion.commit()
    cursor.close()
    conexion.close()

    return {
        "mensaje": "Experiencia laboral actualizada correctamente",
        "id_experiencia": id_experiencia
    }, 200


# Eliminar una experiencia
@app.route("/api/eliminarexperiencia/<int:id_experiencia>", methods=["DELETE"])
def eliminar_experiencia_por_id(id_experiencia):
    conexion = conectar_bd()
    cursor = conexion.cursor()

    sql = "DELETE FROM Experiencias WHERE id_experiencia = %s"
    cursor.execute(sql, (id_experiencia,))

    if cursor.rowcount == 0:
        cursor.close()
        conexion.close()
        return {"mensaje": "No se encontró la experiencia laboral para eliminar"}, 404

    conexion.commit()
    cursor.close()
    conexion.close()

    return {"mensaje": "Experiencia laboral eliminada correctamente"}, 200

# GESTIÓN DE HABILIDADES 

# Consultar las habilidades de una experiencia
@app.route("/api/consultarhabilidades/<int:id_experiencia>", methods=["GET"])
def obtener_habilidades_experiencia(id_experiencia):
    conexion = conectar_bd()
    cursor = conexion.cursor(dictionary=True)

    sql = "SELECT id_experiencia, Habilidades FROM Experiencias WHERE id_experiencia = %s"
    cursor.execute(sql, (id_experiencia,))
    experiencia = cursor.fetchone()

    cursor.close()
    conexion.close()

    if not experiencia:
        return {"mensaje": "Experiencia laboral no encontrada"}, 404

    return experiencia, 200


# Registrar / Asignar habilidades a una experiencia
@app.route("/api/registrarhabilidad/<int:id_experiencia>", methods=["POST"])
def registrar_habilidad_experiencia(id_experiencia):
    conexion = conectar_bd()
    cursor = conexion.cursor()
    datos = request.json

    sql = "UPDATE Experiencias SET Habilidades = %s WHERE id_experiencia = %s"
    cursor.execute(sql, (datos.get("Habilidades"), id_experiencia))

    if cursor.rowcount == 0:
        cursor.close()
        conexion.close()
        return {"mensaje": "No se encontró la experiencia laboral"}, 404

    conexion.commit()
    cursor.close()
    conexion.close()

    return {
        "mensaje": "Habilidad registrada correctamente",
        "id_experiencia": id_experiencia
    }, 200


# Actualizar la habilidad de una experiencia
@app.route("/api/actualizarhabilidad/<int:id_experiencia>", methods=["PUT"])
def actualizar_habilidad_experiencia(id_experiencia):
    conexion = conectar_bd()
    cursor = conexion.cursor()
    datos = request.json

    sql = "UPDATE Experiencias SET Habilidades = %s WHERE id_experiencia = %s"
    cursor.execute(sql, (datos.get("Habilidades"), id_experiencia))

    if cursor.rowcount == 0:
        cursor.close()
        conexion.close()
        return {"mensaje": "No se encontró la experiencia para actualizar habilidades"}, 404

    conexion.commit()
    cursor.close()
    conexion.close()

    return {
        "mensaje": "Habilidades actualizadas correctamente",
        "id_experiencia": id_experiencia
    }, 200


# Eliminar la habilidad de una experiencia (dejar el campo en NULL/vacío)
@app.route("/api/eliminarhabilidad/<int:id_experiencia>", methods=["DELETE"])
def eliminar_habilidad_experiencia(id_experiencia):
    conexion = conectar_bd()
    cursor = conexion.cursor()

    sql = "UPDATE Experiencias SET Habilidades = NULL WHERE id_experiencia = %s"
    cursor.execute(sql, (id_experiencia,))

    if cursor.rowcount == 0:
        cursor.close()
        conexion.close()
        return {"mensaje": "No se encontró la experiencia para eliminar habilidades"}, 404

    conexion.commit()
    cursor.close()
    conexion.close()

    return {"mensaje": "Habilidades eliminadas de la experiencia correctamente"}, 200


# GESTIÓN DE CURSOS

# Consultar los cursos de una hoja de vida
@app.route("/api/consultarcursos/<int:id_personal>", methods=["GET"])
def obtener_cursos_hoja_vida(id_personal):
    conexion = conectar_bd()
    cursor = conexion.cursor(dictionary=True)

    sql = "SELECT * FROM Cursos WHERE id_personal = %s"
    cursor.execute(sql, (id_personal,))
    cursos = cursor.fetchall()

    cursor.close()
    conexion.close()

    return cursos, 200


# Registrar un curso
@app.route("/api/registrarcurso/<int:id_personal>", methods=["POST"])
def registrar_curso_hoja_vida(id_personal):
    conexion = conectar_bd()
    cursor = conexion.cursor()
    datos = request.json

    cursor.execute("SELECT id_personal FROM Personal WHERE id_personal = %s", (id_personal,))
    if not cursor.fetchone():
        cursor.close()
        conexion.close()
        return {"mensaje": "La hoja de vida especificada no existe"}, 404

    sql = "INSERT INTO Cursos (id_personal, Nombre) VALUES (%s, %s)"
    valores = (id_personal, datos.get("Nombre"))

    cursor.execute(sql, valores)
    conexion.commit()

    id_curso = cursor.lastrowid

    cursor.close()
    conexion.close()

    return {
        "mensaje": "Curso registrado correctamente",
        "id_curso": id_curso
    }, 201


# Consultar un curso específico
@app.route("/api/consultarcurso/<int:id_curso>", methods=["GET"])
def consultar_curso_por_id(id_curso):
    conexion = conectar_bd()
    cursor = conexion.cursor(dictionary=True)

    sql = "SELECT * FROM Cursos WHERE id_curso = %s"
    cursor.execute(sql, (id_curso,))
    curso = cursor.fetchone()

    cursor.close()
    conexion.close()

    if not curso:
        return {"mensaje": "Curso no encontrado"}, 404

    return curso, 200


# Actualizar un curso
@app.route("/api/actualizarcurso/<int:id_curso>", methods=["PUT"])
def actualizar_curso_por_id(id_curso):
    conexion = conectar_bd()
    cursor = conexion.cursor()
    datos = request.json

    sql = "UPDATE Cursos SET Nombre = %s WHERE id_curso = %s"
    cursor.execute(sql, (datos.get("Nombre"), id_curso))

    if cursor.rowcount == 0:
        cursor.close()
        conexion.close()
        return {"mensaje": "No se encontró el curso para actualizar"}, 404

    conexion.commit()
    cursor.close()
    conexion.close()

    return {
        "mensaje": "Curso actualizado correctamente",
        "id_curso": id_curso
    }, 200


# Eliminar un curso
@app.route("/api/eliminarcurso/<int:id_curso>", methods=["DELETE"])
def eliminar_curso_por_id(id_curso):
    conexion = conectar_bd()
    cursor = conexion.cursor()

    sql = "DELETE FROM Cursos WHERE id_curso = %s"
    cursor.execute(sql, (id_curso,))

    if cursor.rowcount == 0:
        cursor.close()
        conexion.close()
        return {"mensaje": "No se encontró el curso para eliminar"}, 404

    conexion.commit()
    cursor.close()
    conexion.close()

    return {"mensaje": "Curso eliminado correctamente"}, 200


# CONSULTA COMPLETA DE LA HOJA DE VIDA

@app.route("/api/consultarhojadevida/<int:id_personal>", methods=["GET"])
def consultar_hoja_vida_completa(id_personal):
    conexion = conectar_bd()
    cursor = conexion.cursor(dictionary=True)

    # Datos Personales
    cursor.execute("SELECT * FROM Personal WHERE id_personal = %s", (id_personal,))
    persona = cursor.fetchone()

    if not persona:
        cursor.close()
        conexion.close()
        return {"mensaje": "La hoja de vida especificada no existe"}, 404

    # Información Académica 
    cursor.execute("SELECT * FROM Estudios WHERE id_personal = %s", (id_personal,))
    estudios = cursor.fetchall()

    # Consultar Cursos
    cursor.execute("SELECT * FROM Cursos WHERE id_personal = %s", (id_personal,))
    cursos = cursor.fetchall()

    # Consultar Experiencia Laboral 
    cursor.execute("SELECT * FROM Experiencias WHERE id_personal = %s", (id_personal,))
    experiencias = cursor.fetchall()

    cursor.close()
    conexion.close()

    return {
        "datos_personales": persona,
        "estudios": estudios,
        "cursos": cursos,
        "experiencias_laborales": experiencias
    }, 200

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