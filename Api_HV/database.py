# database.py
# Conexión a la base de datos MySQL (hojavida_nana).

from contextlib import contextmanager

import mysql.connector

from config import Config


def conectar_bd():
    """Abre y devuelve una conexión nueva a MySQL."""
    conexion = mysql.connector.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
    )
    return conexion


@contextmanager
def obtener_cursor(commit=False):
    """
    Abre conexión + cursor (que devuelve diccionarios) y los cierra solos.
    Si commit=True guarda los cambios al terminar.
    Si ocurre un error, deshace los cambios (rollback).

    Uso:
        with obtener_cursor(commit=True) as cursor:
            cursor.execute("INSERT ...", (...))
    """
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
