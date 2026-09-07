import mysql.connector

def conectar_bd():
    conexion = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="hojavida_nana"
    )
    return conexion