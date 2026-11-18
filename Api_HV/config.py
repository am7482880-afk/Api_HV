# config.py
# Lee la configuración del archivo .env (variables de entorno).
# Si una variable no existe en el .env, se usa el valor por defecto.

import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()


class Config:
    # --- JWT ---
    # Clave con la que se firman los tokens. Debe ser larga (mínimo 32 caracteres).
    JWT_SECRET_KEY = os.getenv(
        "JWT_SECRET_KEY",
        "clave-de-desarrollo-cambiala-en-el-env-0123456789",
    )
    # Tiempo de vida del token (en horas)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.getenv("JWT_HORAS", "8")))

    # --- Base de datos MySQL (XAMPP) ---
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "hojavida_nana")

    # --- CORS: direcciones desde donde React puede llamar a la API ---
    FRONTEND_URLS = [
        url.strip()
        for url in os.getenv(
            "FRONTEND_URLS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if url.strip()
    ]
