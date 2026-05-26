import pymysql
from src.config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME_DEV, TABLE_PREFIX


def init_mysql_tables():
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME_DEV,
        cursorclass=pymysql.cursors.DictCursor
    )
    cursor = conn.cursor()

    # Tabla de participantes
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {TABLE_PREFIX}participantes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nombre VARCHAR(200) NOT NULL,
            cedula VARCHAR(55) NOT NULL UNIQUE,
            telefono VARCHAR(100) NOT NULL,
            email VARCHAR(200) NOT NULL,
            direccion TEXT,
            fecha_registro DATETIME NOT NULL,
            es_ganador TINYINT DEFAULT 0,
            fecha_ganancia DATETIME,
            INDEX idx_cedula (cedula)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    ''')

    # Tabla de facturas registradas
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {TABLE_PREFIX}facturas (
            id INT AUTO_INCREMENT PRIMARY KEY,
            participante_id INT NOT NULL,
            numero_factura VARCHAR(50) NOT NULL UNIQUE,
            marca VARCHAR(50) NOT NULL,
            monto DECIMAL(22,2) NOT NULL,
            sucursal VARCHAR(100),
            fecha_compra DATE NOT NULL,
            fecha_registro DATETIME NOT NULL,
            credito_una TINYINT DEFAULT 0,
            boletos_asignados INT DEFAULT 0,
            estado VARCHAR(20) DEFAULT 'activa',
            INDEX idx_participante (participante_id),
            INDEX idx_factura (numero_factura)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    ''')

    # Tabla de boletos
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {TABLE_PREFIX}boletos (
            id INT AUTO_INCREMENT PRIMARY KEY,
            participante_id INT NOT NULL,
            factura_id INT NOT NULL,
            numero_boleto VARCHAR(20) NOT NULL UNIQUE,
            sorteo_id INT,
            asignado_en_sorteo TINYINT DEFAULT 0,
            INDEX idx_participante (participante_id),
            INDEX idx_boleto (numero_boleto)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    ''')

    # Tabla de premios
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {TABLE_PREFIX}premios (
            id INT PRIMARY KEY,
            marca VARCHAR(50) NOT NULL,
            tv VARCHAR(100) NOT NULL,
            valor DECIMAL(22,2) NOT NULL,
            partido VARCHAR(100) NOT NULL,
            fecha_fiesta DATE NOT NULL,
            sorteo_id INT NOT NULL,
            ganador_id INT,
            fecha_asignacion DATETIME
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    ''')

    # Tabla de ganadores
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {TABLE_PREFIX}ganadores (
            id INT AUTO_INCREMENT PRIMARY KEY,
            participante_id INT NOT NULL,
            premio_id INT NOT NULL,
            sorteo_id INT NOT NULL,
            boleto_id INT NOT NULL,
            fecha_sorteo DATETIME NOT NULL,
            confirmado TINYINT DEFAULT 0,
            INDEX idx_sorteo (sorteo_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    ''')

    # Tabla de usuarios admin
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {TABLE_PREFIX}usuarios_admin (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    ''')

    # Insertar premios si no existen
    from src.config import PREMIOS
    for p in PREMIOS:
        cursor.execute(f'''
            INSERT INTO {TABLE_PREFIX}premios (id, marca, tv, valor, partido, fecha_fiesta, sorteo_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                marca = VALUES(marca),
                tv = VALUES(tv),
                valor = VALUES(valor),
                partido = VALUES(partido),
                fecha_fiesta = VALUES(fecha_fiesta),
                sorteo_id = VALUES(sorteo_id)
        ''', (p['id'], p['marca'], p['tv'], p['valor'], p['partido'], p['fecha_fiesta'], p['sorteo']))

    conn.commit()
    conn.close()
    print(f"Tablas creadas/verificadas en {DB_NAME_DEV} con prefijo {TABLE_PREFIX}")


if __name__ == '__main__':
    init_mysql_tables()
