-- BASE DE DATOS NUEVA Y VACIA de Creaciones GMD.
-- phpMyAdmin > Importar > elegir este archivo > Continuar. Borra la base anterior si existía.
DROP DATABASE IF EXISTS creaciones_gmd;
CREATE DATABASE IF NOT EXISTS creaciones_gmd CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE creaciones_gmd;

CREATE TABLE IF NOT EXISTS clientes (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(150) NOT NULL UNIQUE,
  telefono VARCHAR(40) DEFAULT ''
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS materiales (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(100) NOT NULL UNIQUE
) ENGINE=InnoDB;

-- Cada compra se guarda con el ID del cliente. La fecha es la de la compra (automática).
CREATE TABLE IF NOT EXISTS pedidos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  cliente_id INT NOT NULL,
  material VARCHAR(100) DEFAULT '',
  ancho DECIMAL(8,2) NOT NULL DEFAULT 0,
  alto DECIMAL(8,2) NOT NULL DEFAULT 0,
  precio DECIMAL(10,2) NOT NULL DEFAULT 0,
  fecha DATE NOT NULL,
  estado CHAR(1) NOT NULL DEFAULT 'P',
  INDEX (fecha), INDEX (cliente_id),
  CONSTRAINT fk_ped_cli FOREIGN KEY (cliente_id) REFERENCES clientes(id)
) ENGINE=InnoDB;

-- Publicación = imagen + breve descripción (la imagen se guarda en static/uploads y aquí su nombre)
CREATE TABLE IF NOT EXISTS publicaciones (
  id INT AUTO_INCREMENT PRIMARY KEY,
  imagen VARCHAR(255) NOT NULL,
  descripcion VARCHAR(300) DEFAULT '',
  fecha DATE NOT NULL,
  estado VARCHAR(20) DEFAULT 'Publicada'
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS actividades (
  id INT AUTO_INCREMENT PRIMARY KEY,
  icono VARCHAR(10), color VARCHAR(10),
  texto VARCHAR(200), detalle VARCHAR(200),
  ts BIGINT NOT NULL
) ENGINE=InnoDB;
