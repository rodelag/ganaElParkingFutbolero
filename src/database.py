import pymysql
from src.config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME_DEV, TABLE_PREFIX
from src.mysql_db import get_dev_connection

TABLE_PARTICIPANTES = f'{TABLE_PREFIX}participantes'
TABLE_FACTURAS = f'{TABLE_PREFIX}facturas'
TABLE_BOLETOS = f'{TABLE_PREFIX}boletos'
TABLE_PREMIOS = f'{TABLE_PREFIX}premios'
TABLE_GANADORES = f'{TABLE_PREFIX}ganadores'
TABLE_USUARIOS_ADMIN = f'{TABLE_PREFIX}usuarios_admin'


def get_connection():
    return get_dev_connection()


def init_database():
    # Las tablas ya se crean con init_mysql_tables.py
    pass


def insertar_participante(nombre, cedula, telefono, email, direccion=None):
    conn = get_connection()
    cursor = conn.cursor()
    from datetime import datetime
    fecha = datetime.now()
    try:
        # Intentar insertar; si ya existe (cedula UNIQUE), actualizar datos
        cursor.execute(f'''
            INSERT INTO {TABLE_PARTICIPANTES} (nombre, cedula, telefono, email, direccion, fecha_registro)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                nombre = VALUES(nombre),
                telefono = VALUES(telefono),
                email = VALUES(email),
                direccion = VALUES(direccion)
        ''', (nombre, cedula, telefono, email, direccion, fecha))
        conn.commit()
        # Obtener el ID del participante (nuevo o existente)
        cursor.execute(f'SELECT id FROM {TABLE_PARTICIPANTES} WHERE cedula = %s', (cedula,))
        row = cursor.fetchone()
        return row['id'] if row else None
    except Exception:
        return None
    finally:
        conn.close()


def insertar_factura(participante_id, numero_factura, marca, monto, sucursal, fecha_compra, credito_una, boletos):
    conn = get_connection()
    cursor = conn.cursor()
    from datetime import datetime
    fecha = datetime.now()
    try:
        cursor.execute(f'''
            INSERT INTO {TABLE_FACTURAS} (participante_id, numero_factura, marca, monto, sucursal, fecha_compra, fecha_registro, credito_una, boletos_asignados)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (participante_id, numero_factura, marca, monto, sucursal, fecha_compra, fecha, credito_una, boletos))
        conn.commit()
        return cursor.lastrowid
    except pymysql.err.IntegrityError:
        return None
    finally:
        conn.close()


def insertar_boleto(participante_id, factura_id, numero_boleto):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f'''
            INSERT INTO {TABLE_BOLETOS} (participante_id, factura_id, numero_boleto)
            VALUES (%s, %s, %s)
        ''', (participante_id, factura_id, numero_boleto))
        conn.commit()
        return cursor.lastrowid
    except pymysql.err.IntegrityError:
        return None
    finally:
        conn.close()


def obtener_participante_por_cedula(cedula):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f'SELECT * FROM {TABLE_PARTICIPANTES} WHERE cedula = %s', (cedula,))
    row = cursor.fetchone()
    conn.close()
    return row


def obtener_factura_por_numero(numero):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f'SELECT * FROM {TABLE_FACTURAS} WHERE numero_factura = %s', (numero,))
    row = cursor.fetchone()
    conn.close()
    return row


def obtener_boletos_por_participante(participante_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f'''
        SELECT b.*, f.numero_factura, f.marca, f.monto 
        FROM {TABLE_BOLETOS} b 
        JOIN {TABLE_FACTURAS} f ON b.factura_id = f.id 
        WHERE b.participante_id = %s
        ORDER BY b.id DESC
    ''', (participante_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def obtener_boletos_por_factura_numero(numero_factura):
    """Obtiene los boletos generados para una factura específica (por su numero_factura/id Rodelag)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f'''
        SELECT b.*
        FROM {TABLE_BOLETOS} b
        JOIN {TABLE_FACTURAS} f ON b.factura_id = f.id
        WHERE f.numero_factura = %s
        ORDER BY b.id ASC
    ''', (numero_factura,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def obtener_participante_por_factura(numero_factura):
    """Obtiene el participante asociado a una factura registrada"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f'''
        SELECT p.*
        FROM {TABLE_PARTICIPANTES} p
        JOIN {TABLE_FACTURAS} f ON f.participante_id = p.id
        WHERE f.numero_factura = %s
        LIMIT 1
    ''', (numero_factura,))
    row = cursor.fetchone()
    conn.close()
    return row


def obtener_participante_por_cedula_flexible(cedula):
    """Busca participante por cédula exacta o sin guiones/espacios"""
    conn = get_connection()
    cursor = conn.cursor()
    # Primero buscar exacta
    cursor.execute(f'SELECT * FROM {TABLE_PARTICIPANTES} WHERE cedula = %s', (cedula,))
    row = cursor.fetchone()
    if not row:
        # Buscar sin guiones ni espacios
        cedula_limpia = cedula.replace('-', '').replace(' ', '')
        cursor.execute(f"SELECT * FROM {TABLE_PARTICIPANTES} WHERE REPLACE(REPLACE(cedula, '-', ''), ' ', '') = %s", (cedula_limpia,))
        row = cursor.fetchone()
    conn.close()
    return row


def obtener_boleto_por_numero(numero_boleto):
    """Busca un boleto por su número y retorna boleto + participante + factura"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f'''
        SELECT b.*, f.numero_factura, f.marca, f.monto, f.credito_una,
               p.nombre, p.cedula, p.telefono, p.email, p.es_ganador
        FROM {TABLE_BOLETOS} b
        JOIN {TABLE_FACTURAS} f ON b.factura_id = f.id
        JOIN {TABLE_PARTICIPANTES} p ON b.participante_id = p.id
        WHERE b.numero_boleto = %s
    ''', (numero_boleto,))
    row = cursor.fetchone()
    conn.close()
    return row


def obtener_estadisticas():
    conn = get_connection()
    cursor = conn.cursor()
    stats = {}
    
    cursor.execute(f'SELECT COUNT(*) as total FROM {TABLE_PARTICIPANTES}')
    stats['total_participantes'] = cursor.fetchone()['total']
    
    cursor.execute(f'SELECT COUNT(*) as total FROM {TABLE_FACTURAS}')
    stats['total_facturas'] = cursor.fetchone()['total']
    
    cursor.execute(f'SELECT COUNT(*) as total FROM {TABLE_BOLETOS}')
    stats['total_boletos'] = cursor.fetchone()['total']
    
    cursor.execute(f'''
        SELECT COUNT(*) as total
        FROM {TABLE_GANADORES} g
        JOIN {TABLE_PREMIOS} pr ON g.premio_id = pr.id
        WHERE g.confirmado = 1 OR pr.ganador_id IS NOT NULL
    ''')
    stats['total_ganadores'] = cursor.fetchone()['total']
    
    cursor.execute(f'SELECT SUM(monto) as total FROM {TABLE_FACTURAS} WHERE estado = "activa"')
    row = cursor.fetchone()
    stats['monto_total'] = float(row['total'] or 0)
    
    conn.close()
    return stats


def obtener_premios_disponibles(sorteo_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f'''
        SELECT * FROM {TABLE_PREMIOS} 
        WHERE sorteo_id = %s AND ganador_id IS NULL
        ORDER BY id
    ''', (sorteo_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def obtener_boletos_para_sorteo():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f'''
        SELECT b.*, p.nombre, p.cedula, p.telefono, p.email, p.es_ganador
        FROM {TABLE_BOLETOS} b
        JOIN {TABLE_PARTICIPANTES} p ON b.participante_id = p.id
        WHERE b.asignado_en_sorteo = 0 AND p.es_ganador = 0
        ORDER BY RAND()
    ''')
    rows = cursor.fetchall()
    conn.close()
    return rows


def obtener_ganador_pendiente_por_premio(premio_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f'''
        SELECT g.*, b.numero_boleto, p.nombre, p.cedula, p.telefono, p.email
        FROM {TABLE_GANADORES} g
        JOIN {TABLE_PREMIOS} pr ON g.premio_id = pr.id
        JOIN {TABLE_BOLETOS} b ON g.boleto_id = b.id
        JOIN {TABLE_PARTICIPANTES} p ON g.participante_id = p.id
        WHERE g.premio_id = %s
          AND g.confirmado = 0
          AND pr.ganador_id IS NULL
        ORDER BY g.id DESC
        LIMIT 1
    ''', (premio_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def obtener_participantes_con_ganador_pendiente():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f'''
        SELECT DISTINCT g.participante_id
        FROM {TABLE_GANADORES} g
        JOIN {TABLE_PREMIOS} pr ON g.premio_id = pr.id
        WHERE g.confirmado = 0
          AND pr.ganador_id IS NULL
    ''')
    rows = cursor.fetchall()
    conn.close()
    return [row['participante_id'] for row in rows]


def registrar_ganador_pendiente(participante_id, premio_id, sorteo_id, boleto_id):
    conn = get_connection()
    cursor = conn.cursor()
    from datetime import datetime
    fecha = datetime.now()
    try:
        cursor.execute(f'''
            INSERT INTO {TABLE_GANADORES} (participante_id, premio_id, sorteo_id, boleto_id, fecha_sorteo, confirmado)
            VALUES (%s, %s, %s, %s, %s, 0)
        ''', (participante_id, premio_id, sorteo_id, boleto_id, fecha))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def asignar_ganador(participante_id, premio_id, sorteo_id, boleto_id):
    conn = get_connection()
    cursor = conn.cursor()
    from datetime import datetime
    fecha = datetime.now()
    
    cursor.execute(f'''
        INSERT INTO {TABLE_GANADORES} (participante_id, premio_id, sorteo_id, boleto_id, fecha_sorteo, confirmado)
        VALUES (%s, %s, %s, %s, %s, 1)
    ''', (participante_id, premio_id, sorteo_id, boleto_id, fecha))
    
    cursor.execute(f'UPDATE {TABLE_PARTICIPANTES} SET es_ganador = 1, fecha_ganancia = %s WHERE id = %s', (fecha, participante_id))
    cursor.execute(f'UPDATE {TABLE_BOLETOS} SET asignado_en_sorteo = 1, sorteo_id = %s WHERE id = %s', (sorteo_id, boleto_id))
    cursor.execute(f'UPDATE {TABLE_PREMIOS} SET ganador_id = %s, fecha_asignacion = %s WHERE id = %s', (participante_id, fecha, premio_id))
    
    conn.commit()
    conn.close()


def confirmar_ganador_pendiente(ganador_id):
    conn = get_connection()
    cursor = conn.cursor()
    from datetime import datetime
    fecha = datetime.now()

    try:
        cursor.execute(f'''
            SELECT g.*
            FROM {TABLE_GANADORES} g
            JOIN {TABLE_PREMIOS} pr ON g.premio_id = pr.id
            WHERE g.id = %s
              AND g.confirmado = 0
              AND pr.ganador_id IS NULL
            LIMIT 1
        ''', (ganador_id,))
        ganador = cursor.fetchone()
        if not ganador:
            return None

        cursor.execute(f'UPDATE {TABLE_GANADORES} SET confirmado = 1 WHERE id = %s', (ganador_id,))
        cursor.execute(f'UPDATE {TABLE_PARTICIPANTES} SET es_ganador = 1, fecha_ganancia = %s WHERE id = %s', (fecha, ganador["participante_id"]))
        cursor.execute(f'UPDATE {TABLE_BOLETOS} SET asignado_en_sorteo = 1, sorteo_id = %s WHERE id = %s', (ganador['sorteo_id'], ganador['boleto_id']))
        cursor.execute(f'UPDATE {TABLE_PREMIOS} SET ganador_id = %s, fecha_asignacion = %s WHERE id = %s', (ganador['participante_id'], fecha, ganador['premio_id']))
        conn.commit()
        return ganador
    finally:
        conn.close()


def descartar_ganador_pendiente(ganador_id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f'''
            SELECT g.*
            FROM {TABLE_GANADORES} g
            JOIN {TABLE_PREMIOS} pr ON g.premio_id = pr.id
            WHERE g.id = %s
              AND g.confirmado = 0
              AND pr.ganador_id IS NULL
            LIMIT 1
        ''', (ganador_id,))
        ganador = cursor.fetchone()
        if not ganador:
            return None

        cursor.execute(f'DELETE FROM {TABLE_GANADORES} WHERE id = %s', (ganador_id,))
        conn.commit()
        return ganador
    finally:
        conn.close()


def obtener_ganadores(sorteo_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    if sorteo_id:
        cursor.execute(f'''
            SELECT g.*, p.nombre, p.cedula, p.telefono, p.email, pr.marca, pr.tv, pr.partido, pr.fecha_fiesta
            FROM {TABLE_GANADORES} g
            JOIN {TABLE_PARTICIPANTES} p ON g.participante_id = p.id
            JOIN {TABLE_PREMIOS} pr ON g.premio_id = pr.id
            WHERE g.sorteo_id = %s
              AND (g.confirmado = 1 OR pr.ganador_id IS NOT NULL)
            ORDER BY g.id DESC
        ''', (sorteo_id,))
    else:
        cursor.execute(f'''
            SELECT g.*, p.nombre, p.cedula, p.telefono, p.email, pr.marca, pr.tv, pr.partido, pr.fecha_fiesta
            FROM {TABLE_GANADORES} g
            JOIN {TABLE_PARTICIPANTES} p ON g.participante_id = p.id
            JOIN {TABLE_PREMIOS} pr ON g.premio_id = pr.id
            WHERE g.confirmado = 1 OR pr.ganador_id IS NOT NULL
            ORDER BY g.id DESC
        ''')
    rows = cursor.fetchall()
    conn.close()
    return rows


def obtener_todas_las_facturas():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f'''
        SELECT f.*, p.nombre, p.cedula, p.email
        FROM {TABLE_FACTURAS} f
        JOIN {TABLE_PARTICIPANTES} p ON f.participante_id = p.id
        ORDER BY f.fecha_registro DESC
    ''')
    rows = cursor.fetchall()
    conn.close()
    return rows


def invalidar_boletos_por_factura(factura_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f'UPDATE {TABLE_BOLETOS} SET asignado_en_sorteo = -1 WHERE factura_id = %s', (factura_id,))
    cursor.execute(f'UPDATE {TABLE_FACTURAS} SET estado = "invalidada" WHERE id = %s', (factura_id,))
    conn.commit()
    conn.close()


# ========== CONFIGURACIÓN (modo pruebas, etc.) ==========

TABLE_CONFIG = f'{TABLE_PREFIX}config'


def init_config_table():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {TABLE_CONFIG} (
            clave VARCHAR(100) PRIMARY KEY,
            valor TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    ''')
    # Insertar default si no existe
    cursor.execute(f'''
        INSERT IGNORE INTO {TABLE_CONFIG} (clave, valor) VALUES ('modo_pruebas_email', '1')
    ''')
    conn.commit()
    conn.close()


def obtener_config(clave, default=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f'SELECT valor FROM {TABLE_CONFIG} WHERE clave = %s', (clave,))
    row = cursor.fetchone()
    conn.close()
    return row['valor'] if row else default


def guardar_config(clave, valor):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f'''
        INSERT INTO {TABLE_CONFIG} (clave, valor) VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE valor = VALUES(valor), updated_at = CURRENT_TIMESTAMP
    ''', (clave, valor))
    conn.commit()
    conn.close()
