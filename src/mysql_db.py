import pymysql
from pymysql.cursors import DictCursor
from src.config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME, DB_NAME_DEV


def get_rodelag_connection():
    """Conexión a la base de datos de producción de Rodelag (solo lectura para validaciones)"""
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        cursorclass=DictCursor,
        connect_timeout=10,
        read_timeout=10,
        write_timeout=10
    )


def get_dev_connection():
    """Conexión a la base de datos de desarrollo (lectura/escritura para la promoción)"""
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME_DEV,
        cursorclass=DictCursor,
        connect_timeout=10,
        read_timeout=10,
        write_timeout=10
    )


def buscar_cliente_por_ruc(ruc):
    """Busca un cliente en enx_rodelag.customers por RUC/Cédula"""
    conn = get_rodelag_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('''
                SELECT id, RUC, Nombre, Apellido, Contacto, Email, Telefono_1, Direccion, Ciudad, Estado
                FROM customers
                WHERE RUC = %s AND Status = 'ACTIVE'
                LIMIT 1
            ''', (ruc,))
            return cursor.fetchone()
    finally:
        conn.close()


def buscar_factura_por_numero(numero_factura):
    """Busca una factura en enx_rodelag.bills por Num_Fisico"""
    conn = get_rodelag_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('''
                SELECT b.id, b.Num_Fisico, b.Cliente, b.Date, b.SubTotal, b.Total, b.Status,
                       b.Sucursal_Venta, c.RUC, c.Nombre, c.Apellido
                FROM bills b
                LEFT JOIN customers c ON b.Cliente = c.id
                WHERE b.Num_Fisico = %s
                LIMIT 1
            ''', (numero_factura,))
            return cursor.fetchone()
    finally:
        conn.close()


def obtener_marcas_factura(numero_factura):
    """Obtiene las marcas de los productos en una factura"""
    conn = get_rodelag_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('''
                SELECT DISTINCT p.Marca
                FROM bills b
                JOIN bills_details bd ON b.id = bd.Bill
                JOIN products p ON bd.Codigo = p.id
                WHERE b.Num_Fisico = %s
                AND p.Marca IS NOT NULL AND p.Marca != ''
            ''', (numero_factura,))
            return [row['Marca'] for row in cursor.fetchall()]
    finally:
        conn.close()


def validar_factura_completa(numero_factura, cedula, monto_reportado):
    """
    Valida una factura completa:
    1. Existe en bills
    2. El cliente coincide (RUC = cedula)
    3. El monto SubTotal >= 100
    4. Tiene al menos un producto de marca participante
    
    Retorna: (exito: bool, mensaje_error: str, datos_factura: dict)
    """
    from src.config import MARCAS, FECHA_INICIO, FECHA_FIN

    # 1. Buscar factura
    factura = buscar_factura_por_numero(numero_factura)
    if not factura:
        return False, 'El número de factura no existe en nuestro sistema.', None

    # 2. Verificar que no esté anulada
    if factura['Status'] in ('ABORTED', 'MIGRATED'):
        return False, 'La factura está anulada o no es válida para la promoción.', None

    # 3. Verificar que el cliente coincida
    if factura['RUC'] != cedula:
        return False, f'La factura no pertenece a la cédula ingresada. Cliente registrado: {factura["Nombre"]} {factura["Apellido"]}.', None

    # 4. Verificar fechas de vigencia
    from datetime import datetime
    fecha_compra = factura['Date']
    if isinstance(fecha_compra, str):
        fecha_compra = datetime.strptime(fecha_compra, '%Y-%m-%d').date()

    fecha_inicio = datetime.strptime(FECHA_INICIO, '%Y-%m-%d').date()
    fecha_fin = datetime.strptime(FECHA_FIN, '%Y-%m-%d').date()

    if fecha_compra < fecha_inicio or fecha_compra > fecha_fin:
        return False, f'La fecha de la factura ({fecha_compra}) está fuera del período de la promoción ({FECHA_INICIO} al {FECHA_FIN}).', None

    # 5. Verificar monto mínimo
    subtotal = float(factura['SubTotal'] or 0)
    if subtotal < 100:
        return False, f'El monto de la factura (B/.{subtotal:.2f}) no alcanza el mínimo de B/.100.00.', None

    # 6. Verificar marcas participantes
    marcas_factura = obtener_marcas_factura(numero_factura)
    marcas_participantes = [m.upper() for m in MARCAS]
    marcas_encontradas = [m for m in marcas_factura if m.upper() in marcas_participantes]

    if not marcas_encontradas:
        marcas_str = ', '.join(MARCAS)
        return False, f'La factura no contiene productos de las marcas participantes ({marcas_str}).', None

    return True, None, {
        'id': factura['id'],
        'num_fisico': factura['Num_Fisico'],
        'fecha': str(factura['Date']),
        'subtotal': subtotal,
        'total': float(factura['Total'] or 0),
        'sucursal': factura['Sucursal_Venta'],
        'marcas': marcas_encontradas,
        'cliente_nombre': f"{factura['Nombre']} {factura['Apellido']}",
        'cliente_ruc': factura['RUC']
    }
