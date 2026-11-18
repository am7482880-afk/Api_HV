-- ============================================================
-- sql/hojavida_nana_completa.sql
-- Base de datos COMPLETA desde cero (solo si NO la tienes creada,
-- por ejemplo en otro computador). Si ya la tienes, usa
-- actualizacion.sql para no perder datos.
-- ============================================================

CREATE DATABASE IF NOT EXISTS hojavida_nana
    CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;

USE hojavida_nana;

CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    correo VARCHAR(150) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    rol ENUM('aprendiz', 'reclutador') NOT NULL DEFAULT 'aprendiz',
    estado TINYINT(1) NOT NULL DEFAULT 1,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Hoja de vida (datos básicos). En la guía se llama 'hojas_vida'.
CREATE TABLE IF NOT EXISTS personal (
    id_personal         INT AUTO_INCREMENT PRIMARY KEY,
    Fotografia          VARCHAR(255),
    Nombres             VARCHAR(100) NOT NULL,
    Apellidos           VARCHAR(100) NOT NULL,
    Correo              VARCHAR(150) NOT NULL UNIQUE,
    Direccion           VARCHAR(200),
    Perfil_Profesional  TEXT,
    Edad                INT NULL,
    Ciudad              VARCHAR(100) NULL,
    Programa            VARCHAR(150) NULL,
    Ficha               VARCHAR(20) NULL,
    Jornada             VARCHAR(30) NULL,
    usuario_id          INT NULL UNIQUE,
    CONSTRAINT fk_personal_usuarios
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS estudios (
    id_estudio          INT AUTO_INCREMENT PRIMARY KEY,
    id_personal         INT NOT NULL,
    Nivel               VARCHAR(50),
    Institucion         VARCHAR(150),
    Titulo              VARCHAR(150),
    Fecha_inicio        DATE,
    Fecha_finalizacion  DATE NULL,
    Certificado         VARCHAR(255),
    CONSTRAINT fk_estudios_personal
        FOREIGN KEY (id_personal) REFERENCES personal(id_personal)
        ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS experiencias (
    id_experiencia      INT AUTO_INCREMENT PRIMARY KEY,
    id_personal         INT NOT NULL,
    Empresa             VARCHAR(150),
    Cargo               VARCHAR(100),
    Area                VARCHAR(100),
    Fecha_ingreso       DATE,
    Fecha_retiro        DATE NULL,
    Funciones           TEXT,
    Referencia_laboral  VARCHAR(200),
    Certificado         VARCHAR(255),
    Habilidades         TEXT NULL,  -- columna antigua, ya no se usa (ver tabla habilidades)
    CONSTRAINT fk_experiencias_personal
        FOREIGN KEY (id_personal) REFERENCES personal(id_personal)
        ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS cursos (
    id_curso            INT AUTO_INCREMENT PRIMARY KEY,
    id_personal         INT NOT NULL,
    Nombre              VARCHAR(150) NOT NULL,
    CONSTRAINT fk_cursos_personal
        FOREIGN KEY (id_personal) REFERENCES personal(id_personal)
        ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS habilidades (
    id INT AUTO_INCREMENT PRIMARY KEY,
    experiencia_id INT NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    CONSTRAINT fk_habilidades_experiencias
        FOREIGN KEY (experiencia_id) REFERENCES experiencias(id_experiencia)
        ON DELETE CASCADE ON UPDATE CASCADE
);
