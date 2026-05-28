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
        write_timeout=10,
        charset='utf8mb4', 
        use_unicode=True
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
        write_timeout=10,
        charset='utf8mb4', 
        use_unicode=True
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
    """Busca una factura en enx_rodelag.bills por id"""
    conn = get_rodelag_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('''
                SELECT b.id, b.Num_Fisico, b.Fiscal_id, b.Cliente, b.Date, b.SubTotal, b.Total, b.Status,
                       b.Sucursal_Venta, c.RUC, c.Nombre, c.Apellido
                FROM bills b
                LEFT JOIN customers c ON b.Cliente = c.id
                WHERE b.id = %s
                LIMIT 1
            ''', (numero_factura,))
            return cursor.fetchone()
    finally:
        conn.close()


def obtener_productos_factura(numero_factura):
    """Obtiene los productos detallados de una factura"""
    conn = get_rodelag_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('''
                SELECT bd.Descripcion, p.Marca, bd.Unidades, bd.Precio_Unitario, bd.Total
                FROM bills b
                JOIN bills_details bd ON b.id = bd.Bill
                JOIN products p ON bd.Codigo = p.id
                WHERE b.id = %s
                ORDER BY bd.Linea
            ''', (numero_factura,))
            return cursor.fetchall()
    finally:
        conn.close()


def calcular_monto_participante(productos, marcas_participantes):
    """Suma el total antes de ITBMS de productos de marcas participantes."""
    monto = 0.0
    for producto in productos:
        marca = (producto.get('Marca') or '').strip()
        aplica = bool(marca and marca.upper() in marcas_participantes)
        producto['aplica'] = aplica
        if not aplica:
            continue

        total_linea = float(producto.get('Total') or 0)
        if total_linea <= 0:
            unidades = float(producto.get('Unidades') or 0)
            precio_unitario = float(producto.get('Precio_Unitario') or 0)
            total_linea = unidades * precio_unitario

        monto += total_linea

    return round(monto, 2)


def es_credito_de_una(fiscal_id):
    """Verifica si una factura fue pagada con Crédito de Una"""
    if not fiscal_id:
        return False
    conn = get_rodelag_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('''
                SELECT COUNT(*) as total
                FROM enx_transacciones2
                WHERE NumFactura = %s
                LIMIT 1
            ''', (fiscal_id,))
            result = cursor.fetchone()
            return result['total'] > 0
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
                WHERE b.id = %s
                AND p.Marca IS NOT NULL AND p.Marca != ''
            ''', (numero_factura,))
            return [row['Marca'] for row in cursor.fetchall()]
    finally:
        conn.close()


def validar_factura_para_sorteo(numero_factura):
    """
    Valida una factura para el sorteo mostrando checks por cada campo.
    Retorna: (checks: list, datos_factura: dict or None)
    """
    from src.config import MARCAS, FECHA_INICIO, FECHA_FIN
    from datetime import datetime

    checks = []
    datos_factura = None

    # 1. Factura existe
    factura = buscar_factura_por_numero(numero_factura)
    if not factura:
        checks.append({'campo': 'Factura existe', 'pass': False, 'mensaje': 'El número de factura no existe en nuestro sistema.'})
        return checks, None
    checks.append({'campo': 'Factura existe', 'pass': True, 'mensaje': 'Factura encontrada en sistema Rodelag.'})

    # 2. Factura no anulada
    if factura['Status'] in ('ABORTED', 'MIGRATED'):
        checks.append({'campo': 'Factura válida', 'pass': False, 'mensaje': 'La factura está anulada o no es válida para la promoción.'})
        return checks, None
    checks.append({'campo': 'Factura válida', 'pass': True, 'mensaje': 'Factura activa y válida.'})

    # 3. Cliente activo
    cedula = factura['RUC']
    cliente = buscar_cliente_por_ruc(cedula)
    if not cliente:
        checks.append({'campo': 'Cliente activo', 'pass': False, 'mensaje': 'El cliente no está activo en nuestro sistema.'})
        return checks, None

    # 3b. Verificar datos completos del cliente (no bloquea, solo marca)
    telefono = (cliente.get('Telefono_1') or cliente.get('Contacto') or '').strip()
    email = (cliente.get('Email') or '').strip()
    direccion = (cliente.get('Direccion') or '').strip()
    datos_faltantes = []
    if not telefono:
        datos_faltantes.append('teléfono')
    if not email:
        datos_faltantes.append('email')
    if not direccion:
        datos_faltantes.append('dirección')

    if datos_faltantes:
        checks.append({
            'campo': 'Datos del cliente',
            'pass': True,
            'mensaje': f'Datos incompletos: {", ".join(datos_faltantes)}. Debe completarlos para registrar.'
        })
    else:
        checks.append({'campo': 'Datos del cliente', 'pass': True, 'mensaje': 'Datos del cliente completos.'})

    checks.append({'campo': 'Cliente activo', 'pass': True, 'mensaje': f'Cliente: {cliente["Nombre"]} {cliente["Apellido"]}.'})

    # 4. Fecha dentro del rango
    fecha_compra = factura['Date']
    if isinstance(fecha_compra, str):
        fecha_compra = datetime.strptime(fecha_compra, '%Y-%m-%d').date()

    fecha_inicio = datetime.strptime(FECHA_INICIO, '%Y-%m-%d').date()
    fecha_fin = datetime.strptime(FECHA_FIN, '%Y-%m-%d').date()

    if fecha_compra < fecha_inicio or fecha_compra > fecha_fin:
        checks.append({'campo': 'Fecha de compra', 'pass': False, 'mensaje': f'Fecha ({fecha_compra}) fuera del período ({FECHA_INICIO} al {FECHA_FIN}).'})
        return checks, None
    checks.append({'campo': 'Fecha de compra', 'pass': True, 'mensaje': f'Fecha válida: {fecha_compra}.'})

    # 5. Subtotal de la factura (informativo)
    subtotal = float(factura['SubTotal'] or 0)
    checks.append({'campo': 'Subtotal factura', 'pass': True, 'mensaje': f'Subtotal factura: B/.{subtotal:.2f}.'})

    # 6. Marcas participantes
    marcas_factura = obtener_marcas_factura(numero_factura)
    marcas_participantes = [m.upper() for m in MARCAS]
    marcas_encontradas = [m for m in marcas_factura if m.strip().upper() in marcas_participantes]

    if not marcas_encontradas:
        marcas_str = ', '.join(MARCAS)
        checks.append({'campo': 'Marca participante', 'pass': False, 'mensaje': f'No contiene marcas participantes ({marcas_str}).'})
        return checks, None
    checks.append({'campo': 'Marca participante', 'pass': True, 'mensaje': f'Marcas encontradas: {", ".join(marcas_encontradas)}.'})

    # 7. Productos de la factura y monto participante
    productos = obtener_productos_factura(numero_factura)
    monto_participante = calcular_monto_participante(productos, marcas_participantes)
    if monto_participante < 100:
        checks.append({
            'campo': 'Monto participante',
            'pass': False,
            'mensaje': f'Los productos participantes suman B/.{monto_participante:.2f} y no alcanzan el mínimo de B/.100.00.'
        })
        return checks, None
    checks.append({
        'campo': 'Monto participante',
        'pass': True,
        'mensaje': f'Monto participante válido: B/.{monto_participante:.2f}.'
    })

    # 8. Detectar Crédito de Una
    credito_una = es_credito_de_una(factura.get('Fiscal_id'))

    # Datos completos para el frontend
    datos_factura = {
        'id': factura['id'],
        'num_fisico': factura['Num_Fisico'],
        'fecha': str(fecha_compra),
        'subtotal': subtotal,
        'monto_elegible': monto_participante,
        'total': float(factura['Total'] or 0),
        'sucursal': factura['Sucursal_Venta'],
        'marcas': marcas_encontradas,
        'marca_principal': marcas_encontradas[0] if marcas_encontradas else '',
        'productos': productos,
        'credito_una': credito_una,
        'cliente': {
            'nombre': f"{cliente['Nombre']} {cliente['Apellido']}",
            'cedula': cliente['RUC'],
            'telefono': telefono,
            'email': email,
            'direccion': direccion,
            'datos_completos': len(datos_faltantes) == 0,
            'datos_faltantes': datos_faltantes
        }
    }

    return checks, datos_factura


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

    # 5. Verificar monto participante mínimo
    subtotal = float(factura['SubTotal'] or 0)
    marcas_factura = obtener_marcas_factura(numero_factura)
    marcas_participantes = [m.upper() for m in MARCAS]
    marcas_encontradas = [m for m in marcas_factura if m.strip().upper() in marcas_participantes]

    if not marcas_encontradas:
        marcas_str = ', '.join(MARCAS)
        return False, f'La factura no contiene productos de las marcas participantes ({marcas_str}).', None

    productos = obtener_productos_factura(numero_factura)
    monto_participante = calcular_monto_participante(productos, marcas_participantes)
    if monto_participante < 100:
        return False, f'Los productos participantes suman B/.{monto_participante:.2f} y no alcanzan el mínimo de B/.100.00.', None

    return True, None, {
        'id': factura['id'],
        'num_fisico': factura['Num_Fisico'],
        'fecha': str(factura['Date']),
        'subtotal': subtotal,
        'monto_elegible': monto_participante,
        'total': float(factura['Total'] or 0),
        'sucursal': factura['Sucursal_Venta'],
        'marcas': marcas_encontradas,
        'cliente_nombre': f"{factura['Nombre']} {factura['Apellido']}",
        'cliente_ruc': factura['RUC']
    }
