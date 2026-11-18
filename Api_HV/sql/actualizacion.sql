-- ============================================================
-- sql/actualizacion.sql
-- Ejecutar en phpMyAdmin sobre la base de datos que YA TIENES
-- (hojavida_nana). NO borra ningún dato.
--
-- phpMyAdmin -> selecciona hojavida_nana -> pestaña SQL ->
-- pega todo este archivo -> Continuar
-- ============================================================

USE hojavida_nana;

-- 1. Tabla de usuarios (si ya existe, no hace nada)
CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    correo VARCHAR(150) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    rol ENUM('aprendiz', 'reclutador') NOT NULL DEFAULT 'aprendiz',
    estado TINYINT(1) NOT NULL DEFAULT 1,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Campos de la guía que faltaban en 'personal' (datos básicos de la HV)
ALTER TABLE personal
    ADD COLUMN IF NOT EXISTS Edad     INT          NULL,
    ADD COLUMN IF NOT EXISTS Ciudad   VARCHAR(100) NULL,
    ADD COLUMN IF NOT EXISTS Programa VARCHAR(150) NULL,
    ADD COLUMN IF NOT EXISTS Ficha    VARCHAR(20)  NULL,
    ADD COLUMN IF NOT EXISTS Jornada  VARCHAR(30)  NULL;

-- 3. Tabla de habilidades relacionada con experiencias (experiencia_id)
CREATE TABLE IF NOT EXISTS habilidades (
    id INT AUTO_INCREMENT PRIMARY KEY,
    experiencia_id INT NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    CONSTRAINT fk_habilidades_experiencias
        FOREIGN KEY (experiencia_id) REFERENCES experiencias(id_experiencia)
        ON DELETE CASCADE ON UPDATE CASCADE
);

-- ------------------------------------------------------------
-- IMPORTANTE: la tabla 'personal' debe tener la columna usuario_id.
-- Si al ejecutar la API sale "Unknown column 'usuario_id'",
-- ejecuta también esto (solo una vez):
--
-- ALTER TABLE personal
--   ADD COLUMN usuario_id INT NULL UNIQUE,
--   ADD CONSTRAINT fk_personal_usuarios
--     FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
--     ON DELETE CASCADE ON UPDATE CASCADE;
-- ------------------------------------------------------------
