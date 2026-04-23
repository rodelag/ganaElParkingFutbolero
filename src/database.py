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
        cursor.execute(f'''
            INSERT INTO {TABLE_PARTICIPANTES} (nombre, cedula, telefono, email, direccion, fecha_registro)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (nombre, cedula, telefono, email, direccion, fecha))
        conn.commit()
        return cursor.lastrowid
    except pymysql.err.IntegrityError:
        cursor.execute(f'SELECT id FROM {TABLE_PARTICIPANTES} WHERE cedula = %s', (cedula,))
        row = cursor.fetchone()
        return row['id'] if row else None
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
    
    cursor.execute(f'SELECT COUNT(*) as total FROM {TABLE_GANADORES}')
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


def asignar_ganador(participante_id, premio_id, sorteo_id, boleto_id):
    conn = get_connection()
    cursor = conn.cursor()
    from datetime import datetime
    fecha = datetime.now()
    
    cursor.execute(f'''
        INSERT INTO {TABLE_GANADORES} (participante_id, premio_id, sorteo_id, boleto_id, fecha_sorteo)
        VALUES (%s, %s, %s, %s, %s)
    ''', (participante_id, premio_id, sorteo_id, boleto_id, fecha))
    
    cursor.execute(f'UPDATE {TABLE_PARTICIPANTES} SET es_ganador = 1, fecha_ganancia = %s WHERE id = %s', (fecha, participante_id))
    cursor.execute(f'UPDATE {TABLE_BOLETOS} SET asignado_en_sorteo = 1, sorteo_id = %s WHERE id = %s', (sorteo_id, boleto_id))
    cursor.execute(f'UPDATE {TABLE_PREMIOS} SET ganador_id = %s, fecha_asignacion = %s WHERE id = %s', (participante_id, fecha, premio_id))
    
    conn.commit()
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
            ORDER BY g.id DESC
        ''', (sorteo_id,))
    else:
        cursor.execute(f'''
            SELECT g.*, p.nombre, p.cedula, p.telefono, p.email, pr.marca, pr.tv, pr.partido, pr.fecha_fiesta
            FROM {TABLE_GANADORES} g
            JOIN {TABLE_PARTICIPANTES} p ON g.participante_id = p.id
            JOIN {TABLE_PREMIOS} pr ON g.premio_id = pr.id
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
