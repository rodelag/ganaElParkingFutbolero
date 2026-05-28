import os
import random
import string
from decimal import Decimal, InvalidOperation
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, Response
from werkzeug.security import generate_password_hash, check_password_hash

from src.config import (
    SECRET_KEY, ADMIN_PASSWORD_HASH, FLASK_PORT, MARCAS, MONTO_BOLETO,
    MULTIPLICADOR_CREDITO_UNA, FECHA_INICIO, FECHA_FIN, SORTEOS
)
from src.database import (
    insertar_participante, insertar_factura, insertar_boleto,
    obtener_participante_por_cedula, obtener_participante_por_cedula_flexible,
    obtener_participante_por_factura,
    obtener_factura_por_numero, obtener_boleto_por_numero,
    obtener_boletos_por_participante, obtener_boletos_por_factura_numero, obtener_estadisticas,
    obtener_premios_disponibles, obtener_boletos_para_sorteo,
    asignar_ganador, obtener_ganadores, obtener_todas_las_facturas,
    obtener_ganador_pendiente_por_premio, obtener_participantes_con_ganador_pendiente,
    registrar_ganador_pendiente, confirmar_ganador_pendiente, descartar_ganador_pendiente,
    invalidar_boletos_por_factura,
    init_config_table, obtener_config, guardar_config
)
from src.mysql_db import (
    buscar_cliente_por_ruc, validar_factura_completa, validar_factura_para_sorteo,
    obtener_productos_factura
)
from src.email_service import enviar_correo_confirmacion

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['JSON_AS_ASCII'] = False
@app.template_filter('miles')
def miles_filter(value):
    try:
        return "{:,}".format(int(value))
    except:
        return value

@app.after_request
def add_charset(response):
    if response.content_type.startswith('text/html'):
        response.headers['Content-Type'] = 'text/html; charset=utf-8'
    return response

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin' not in session:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function


def generar_numero_boleto():
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=8))


def normalizar_monto(valor):
    try:
        return Decimal(str(valor or 0))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal('0')


def calcular_boletos(monto, credito_una):
    boletos = int(normalizar_monto(monto) // normalizar_monto(MONTO_BOLETO))
    if credito_una:
        boletos *= MULTIPLICADOR_CREDITO_UNA
    return boletos


def calcular_boletos_por_productos(productos, credito_una):
    """Calcula boletos por monto elegible acumulado en productos participantes."""
    detalle = []
    monto_elegible = Decimal('0')

    for prod in productos:
        if not prod.get('aplica'):
            continue

        total_linea = normalizar_monto(prod.get('Total'))
        if total_linea <= 0:
            total_linea = normalizar_monto(prod.get('Precio_Unitario')) * normalizar_monto(prod.get('Unidades'))

        monto_elegible += total_linea
        detalle.append({
            'producto': prod.get('Descripcion') or 'Producto',
            'marca': prod.get('Marca') or '',
            'monto': float(total_linea)
        })

    boletos_base = calcular_boletos(monto_elegible, False)
    total_boletos = calcular_boletos(monto_elegible, credito_una)

    return {
        'total_boletos': total_boletos,
        'boletos_base': boletos_base,
        'monto_elegible': float(monto_elegible),
        'detalle': detalle
    }


def _obtener_estado_sorteos():
    estado = session.get('sorteos_admin')
    if not isinstance(estado, dict):
        estado = {}
        session['sorteos_admin'] = estado
    return estado


def _obtener_rechazados_premio(premio_id):
    estado = _obtener_estado_sorteos()
    premio_estado = estado.setdefault(str(premio_id), {'participantes_rechazados': []})
    return premio_estado['participantes_rechazados']


def _agregar_participante_rechazado(premio_id, participante_id):
    rechazados = _obtener_rechazados_premio(premio_id)
    if participante_id not in rechazados:
        rechazados.append(participante_id)
        session.modified = True


def _limpiar_rechazados_premio(premio_id):
    estado = _obtener_estado_sorteos()
    if str(premio_id) in estado:
        estado.pop(str(premio_id), None)
        session.modified = True


def _serializar_candidato(ganador):
    return {
        'id': ganador['id'],
        'participante_id': ganador['participante_id'],
        'nombre': ganador['nombre'],
        'cedula': ganador['cedula'],
        'telefono': ganador['telefono'],
        'email': ganador.get('email') or '',
        'boleto': ganador['numero_boleto'],
        'factura': ganador.get('numero_factura') or '—',
        'marca': ganador.get('marca') or '—'
    }


@app.route('/')
def index():
    return render_template('index.html', marcas=MARCAS, fecha_inicio=FECHA_INICIO, fecha_fin=FECHA_FIN)


@app.route('/api/validar-factura', methods=['POST'])
def api_validar_factura():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Datos inválidos'}), 400

    numero_factura = data.get('numero_factura', '').strip()
    if not numero_factura:
        return jsonify({'success': False, 'message': 'El número de factura es requerido'}), 400

    # Validar factura contra Rodelag con checks
    checks, datos_factura = validar_factura_para_sorteo(numero_factura)

    # Verificar si ya fue registrada en la promoción (check adicional)
    if datos_factura:
        if obtener_factura_por_numero(numero_factura):
            checks.append({'campo': 'No registrada previamente', 'pass': False, 'mensaje': 'Esta factura ya fue registrada anteriormente en la promoción.'})
            return jsonify({'success': False, 'checks': checks, 'datos': None}), 400
        else:
            checks.append({'campo': 'No registrada previamente', 'pass': True, 'mensaje': 'Factura disponible para registrar.'})

    # Verificar si todos los checks pasaron
    todos_pass = all(c['pass'] for c in checks)

    if not todos_pass:
        return jsonify({'success': False, 'checks': checks, 'datos': None}), 400

    # Calcular boletos por producto para mostrar en frontend
    resumen_boletos = calcular_boletos_por_productos(
        datos_factura['productos'], datos_factura['credito_una']
    )
    datos_factura['boletos_estimados'] = resumen_boletos['total_boletos']
    datos_factura['boletos_base'] = resumen_boletos['boletos_base']
    datos_factura['monto_elegible'] = resumen_boletos['monto_elegible']
    datos_factura['detalle_boletos'] = resumen_boletos['detalle']

    return jsonify({
        'success': True,
        'checks': checks,
        'datos': datos_factura
    })


@app.route('/api/registrar', methods=['POST'])
def api_registrar():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Datos inválidos'}), 400

    # Validar campos requeridos
    campos_requeridos = ['numero_factura', 'marca']
    for campo in campos_requeridos:
        if not data.get(campo):
            return jsonify({'success': False, 'message': f'El campo {campo} es requerido'}), 400

    numero_factura = data.get('numero_factura', '').strip()
    marca_solicitada = data.get('marca', '').strip()

    # === VALIDACIONES CONTRA BASE DE DATOS RODELAG ===

    # 1. Validar factura y obtener datos
    checks, datos_factura = validar_factura_para_sorteo(numero_factura)
    if not datos_factura:
        return jsonify({'success': False, 'message': checks[-1]['mensaje'] if checks else 'Factura no válida'}), 400

    # 2. Verificar que la marca solicitada esté en las marcas de la factura
    marcas_factura = [m.upper() for m in datos_factura['marcas']]
    if marca_solicitada.upper() not in marcas_factura:
        marcas_str = ', '.join(datos_factura['marcas'])
        return jsonify({'success': False, 'message': f'La factura contiene productos de las marcas: {marcas_str}, pero no de {marca_solicitada}.'}), 400

    # 3. Verificar si la factura ya fue registrada en la promoción
    if obtener_factura_por_numero(numero_factura):
        return jsonify({'success': False, 'message': 'Esta factura ya fue registrada anteriormente en la promoción.'}), 400

    # Obtener datos del cliente desde la factura (origen Rodelag)
    cliente = datos_factura['cliente']
    credito_una = datos_factura['credito_una']

    # Usar datos del frontend si el usuario los completó/corrigió,
    # de lo contrario usar los de Rodelag
    nombre = data.get('nombre', '').strip() or cliente['nombre']
    cedula = data.get('cedula', '').strip() or cliente['cedula']
    telefono = data.get('telefono', '').strip() or cliente['telefono']
    email = data.get('email', '').strip() or cliente['email']
    direccion = data.get('direccion', '').strip() or cliente['direccion']

    # === REGISTRO EN LA PROMOCIÓN ===

    # Insertar o actualizar participante
    participante_id = insertar_participante(nombre, cedula, telefono, email, direccion)
    if not participante_id:
        return jsonify({'success': False, 'message': 'Error al registrar participante'}), 500

    # Calcular boletos por monto participante acumulado
    resumen_boletos = calcular_boletos_por_productos(
        datos_factura['productos'], credito_una
    )
    boletos = resumen_boletos['total_boletos']
    monto_real = datos_factura['subtotal']

    # Insertar factura
    factura_id = insertar_factura(participante_id, numero_factura, marca_solicitada, monto_real,
                                   datos_factura.get('sucursal') or '', datos_factura['fecha'], credito_una, boletos)
    if not factura_id:
        return jsonify({'success': False, 'message': 'Error al registrar factura'}), 500

    # Generar boletos
    boletos_generados = []
    for _ in range(boletos):
        numero_boleto = generar_numero_boleto()
        while not insertar_boleto(participante_id, factura_id, numero_boleto):
            numero_boleto = generar_numero_boleto()
        boletos_generados.append(numero_boleto)

    # Enviar correo de confirmación
    enviar_correo_confirmacion(
        destinatario=email,
        nombre=nombre,
        numero_factura=numero_factura,
        boletos=boletos,
        numeros_boletos=boletos_generados,
        credito_una=credito_una
    )

    return jsonify({
        'success': True,
        'message': 'Registro exitoso',
        'boletos': boletos,
        'numeros_boletos': boletos_generados,
        'credito_una': credito_una,
        'monto_validado': monto_real,
        'cliente': nombre
    })


@app.route('/api/consultar', methods=['GET'])
def api_consultar():
    cedula = request.args.get('cedula', '').strip()
    boleto = request.args.get('boleto', '').strip().upper()
    factura = request.args.get('factura', '').strip()

    if not cedula and not boleto and not factura:
        return jsonify({'success': False, 'message': 'Ingresa una cédula, número de boleto o número de factura'}), 400

    # Buscar por número de boleto
    if boleto:
        boleto_data = obtener_boleto_por_numero(boleto)
        if not boleto_data:
            return jsonify({'success': False, 'message': 'No se encontró el boleto ingresado'}), 404
        participante = {
            'id': boleto_data['participante_id'],
            'nombre': boleto_data['nombre'],
            'cedula': boleto_data['cedula'],
            'telefono': boleto_data['telefono'],
            'email': boleto_data['email'],
            'es_ganador': boleto_data['es_ganador']
        }
        boletos = obtener_boletos_por_participante(participante['id'])
        return jsonify({
            'success': True,
            'participante': participante,
            'total_boletos': len(boletos),
            'boletos': boletos,
            'busqueda': 'boleto'
        })

    # Buscar por número de factura
    if factura:
        participante = obtener_participante_por_factura(factura)
        if not participante:
            return jsonify({'success': False, 'message': 'No se encontró la factura ingresada'}), 404
        boletos = obtener_boletos_por_participante(participante['id'])
        return jsonify({
            'success': True,
            'participante': participante,
            'total_boletos': len(boletos),
            'boletos': boletos,
            'busqueda': 'factura'
        })

    # Buscar por cédula (flexible: con o sin guiones)
    participante = obtener_participante_por_cedula_flexible(cedula)
    if not participante:
        return jsonify({'success': False, 'message': 'No se encontraron registros para esta cédula'}), 404

    boletos = obtener_boletos_por_participante(participante['id'])
    return jsonify({
        'success': True,
        'participante': participante,
        'total_boletos': len(boletos),
        'boletos': boletos,
        'busqueda': 'cedula'
    })


@app.route('/bases')
def bases():
    return render_template('bases.html', marcas=MARCAS, premios=SORTEOS)


# ============== ADMIN ==============

@app.route('/admin')
def admin_login():
    if 'admin' in session:
        return redirect(url_for('admin_dashboard'))
    return render_template('admin_login.html')


@app.route('/admin/login', methods=['POST'])
def admin_do_login():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()

    from src.database import get_connection, TABLE_USUARIOS_ADMIN
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f'SELECT * FROM {TABLE_USUARIOS_ADMIN} WHERE username = %s', (username,))
    user = cursor.fetchone()
    conn.close()

    if user and check_password_hash(user['password_hash'], password):
        session['admin'] = username
        return redirect(url_for('admin_dashboard'))

    flash('Usuario o contraseña incorrectos', 'error')
    return redirect(url_for('admin_login'))


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('admin_login'))


@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    init_config_table()
    stats = obtener_estadisticas()
    try:
        from src.mysql_db import get_rodelag_connection
        conn_prod = get_rodelag_connection()
        cursor_prod = conn_prod.cursor()
        marcas_placeholder = ', '.join(['%s'] * len(MARCAS))
        cursor_prod.execute(f'''
            SELECT 
                COUNT(*) AS total_facturas_elegibles,
                COUNT(DISTINCT Cliente) AS total_clientes_elegibles
            FROM (
                SELECT b.id, b.Cliente
                FROM bills b
                JOIN bills_details bd ON bd.Bill = b.id
                JOIN products p ON p.id = bd.Codigo
                WHERE b.Status NOT IN ('ABORTED', 'MIGRATED')
                  AND b.Date BETWEEN %s AND %s
                  AND p.Marca IN ({marcas_placeholder})
                GROUP BY b.id, b.Cliente
                HAVING SUM(bd.Precio_Unitario * bd.Unidades) >= 100
            ) AS elegibles
        ''', (FECHA_INICIO, FECHA_FIN, *MARCAS))
        row = cursor_prod.fetchone()
        stats['total_facturas_rodelag_elegibles'] = row['total_facturas_elegibles'] if row else 0
        stats['total_clientes_rodelag_elegibles'] = row['total_clientes_elegibles'] if row else 0
        conn_prod.close()
    except Exception as e:
        stats['total_facturas_rodelag_elegibles'] = '—'
        stats['total_clientes_rodelag_elegibles'] = '—'
    modo_pruebas = obtener_config('modo_pruebas_email', '1') == '1'
    return render_template('admin_dashboard.html', stats=stats, sorteos=SORTEOS, modo_pruebas_email=modo_pruebas)


@app.route('/admin/facturas')
@login_required
def admin_facturas():
    facturas = obtener_todas_las_facturas()
    return render_template('admin_facturas.html', facturas=facturas)


@app.route('/admin/ganadores')
@login_required
def admin_ganadores():
    sorteo_id = request.args.get('sorteo', type=int)
    ganadores = obtener_ganadores(sorteo_id)
    return render_template('admin_ganadores.html', ganadores=ganadores, sorteos=SORTEOS)


@app.route('/admin/sorteo')
@login_required
def admin_sorteo():
    sorteo_id = request.args.get('sorteo', type=int)
    if not sorteo_id or sorteo_id not in SORTEOS:
        return redirect(url_for('admin_dashboard'))
    
    premios = obtener_premios_disponibles(sorteo_id)
    config = SORTEOS[sorteo_id]
    return render_template('admin_sorteo.html', premios=premios, config=config, sorteo_id=sorteo_id)


@app.route('/api/admin/estadisticas')
@login_required
def api_admin_estadisticas():
    stats = obtener_estadisticas()
    return jsonify(stats)


@app.route('/api/admin/modo-pruebas', methods=['GET'])
@login_required
def api_get_modo_pruebas():
    init_config_table()
    valor = obtener_config('modo_pruebas_email', '1')
    return jsonify({'modo_pruebas': valor == '1'})


@app.route('/api/admin/modo-pruebas', methods=['POST'])
@login_required
def api_set_modo_pruebas():
    data = request.get_json() or {}
    activo = bool(data.get('activo', False))
    guardar_config('modo_pruebas_email', '1' if activo else '0')
    return jsonify({'success': True, 'modo_pruebas': activo})


@app.route('/api/admin/factura-detalle/<numero_factura>')
@login_required
def api_factura_detalle(numero_factura):
    productos = obtener_productos_factura(numero_factura)
    boletos = obtener_boletos_por_factura_numero(numero_factura)
    # Marcar cuáles aplican a la promoción
    marcas_participantes = [m.upper() for m in MARCAS]
    for p in productos:
        marca = (p.get('Marca') or '').strip()
        p['aplica'] = bool(marca and marca.upper() in marcas_participantes)
    return jsonify({'success': True, 'productos': productos, 'boletos': [b['numero_boleto'] for b in boletos]})


@app.route('/api/admin/realizar-sorteo', methods=['POST'])
@login_required
def api_realizar_sorteo():
    data = request.get_json() or {}
    sorteo_id = data.get('sorteo_id')
    premio_id = data.get('premio_id')

    if not sorteo_id or not premio_id:
        return jsonify({'success': False, 'message': 'Datos incompletos'}), 400

    premios_disp = obtener_premios_disponibles(sorteo_id)
    premio = next((p for p in premios_disp if p['id'] == premio_id), None)
    if not premio:
        return jsonify({'success': False, 'message': 'Premio no disponible'}), 400

    ganador_pendiente = obtener_ganador_pendiente_por_premio(premio_id)
    if ganador_pendiente:
        return jsonify({
            'success': True,
            'pendiente': True,
            'message': 'Ya hay un candidato pendiente de confirmar para este premio.',
            'ganador': _serializar_candidato(ganador_pendiente)
        })
    boletos = obtener_boletos_para_sorteo(marca=premio.get('marca'))
    if not boletos:
        return jsonify({'success': False, 'message': 'No hay boletos disponibles para el sorteo'}), 400

    participantes_rechazados = set(_obtener_rechazados_premio(premio_id))
    participantes_pendientes = set(obtener_participantes_con_ganador_pendiente())
    participantes_excluidos = participantes_rechazados | participantes_pendientes
    boletos_disponibles = [b for b in boletos if b['participante_id'] not in participantes_excluidos]
    if not boletos_disponibles:
        return jsonify({'success': False, 'message': 'No hay más participantes disponibles para este premio.'}), 400

    ganador_boleto = random.choice(boletos_disponibles)
    ganador_id = registrar_ganador_pendiente(ganador_boleto['participante_id'], premio_id, sorteo_id, ganador_boleto['id'])
    ganador_pendiente = obtener_ganador_pendiente_por_premio(premio_id)
    if not ganador_id or not ganador_pendiente:
        return jsonify({'success': False, 'message': 'No se pudo preparar el candidato para confirmación.'}), 500

    return jsonify({
        'success': True,
        'pendiente': True,
        'message': 'Candidato seleccionado. Confirme si contestó la llamada.',
        'ganador': _serializar_candidato(ganador_pendiente)
    })


@app.route('/api/admin/confirmar-ganador', methods=['POST'])
@login_required
def api_confirmar_ganador():
    data = request.get_json() or {}
    ganador_id = data.get('ganador_id')
    premio_id = data.get('premio_id')

    if not ganador_id or not premio_id:
        return jsonify({'success': False, 'message': 'Datos incompletos'}), 400

    ganador = confirmar_ganador_pendiente(ganador_id)
    if not ganador or ganador['premio_id'] != premio_id:
        return jsonify({'success': False, 'message': 'El candidato ya no está disponible para confirmar.'}), 400

    _limpiar_rechazados_premio(premio_id)

    return jsonify({
        'success': True,
        'message': 'Ganador confirmado correctamente.'
    })


@app.route('/api/admin/rechazar-ganador', methods=['POST'])
@login_required
def api_rechazar_ganador():
    data = request.get_json() or {}
    ganador_id = data.get('ganador_id')
    premio_id = data.get('premio_id')

    if not ganador_id or not premio_id:
        return jsonify({'success': False, 'message': 'Datos incompletos'}), 400

    ganador = descartar_ganador_pendiente(ganador_id)
    if not ganador or ganador['premio_id'] != premio_id:
        return jsonify({'success': False, 'message': 'El candidato ya no está disponible para descartar.'}), 400

    _agregar_participante_rechazado(premio_id, ganador['participante_id'])

    return jsonify({
        'success': True,
        'message': 'Candidato descartado. Puede buscar otro.'
    })


@app.route('/api/admin/exportar-facturas')
@login_required
def api_exportar_facturas():
    import csv
    import io
    facturas = obtener_todas_las_facturas()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Numero Factura', 'Nombre', 'Cedula', 'Email', 'Marca', 'Monto', 'Sucursal', 
                     'Fecha Compra', 'Fecha Registro', 'Credito Una', 'Boletos', 'Estado'])
    for f in facturas:
        writer.writerow([
            f['id'], f['numero_factura'], f['nombre'], f['cedula'], f['email'],
            f['marca'], f['monto'], f['sucursal'], f['fecha_compra'], f['fecha_registro'],
            'Si' if f['credito_una'] else 'No', f['boletos_asignados'], f['estado']
        ])
    output.seek(0)
    return Response(output, mimetype='text/csv',
                    headers={"Content-Disposition": "attachment;filename=facturas_parking_futbolero.csv"})


@app.route('/api/admin/exportar-ganadores')
@login_required
def api_exportar_ganadores():
    import csv
    import io
    sorteo_id = request.args.get('sorteo', type=int)
    ganadores = obtener_ganadores(sorteo_id)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Nombre', 'Cedula', 'Telefono', 'Email', 'Premio', 'Marca', 'Partido', 
                     'Fecha Fiesta', 'Fecha Sorteo', 'Sorteo ID'])
    for g in ganadores:
        writer.writerow([
            g['id'], g['nombre'], g['cedula'], g['telefono'], g['email'],
            g['tv'], g['marca'], g['partido'], g['fecha_fiesta'],
            g['fecha_sorteo'].strftime('%Y-%m-%d') if g.get('fecha_sorteo') else '',
            g['sorteo_id']
        ])
    output.seek(0)
    filename = f"ganadores_sorteo_{sorteo_id}.csv" if sorteo_id else "ganadores_parking_futbolero.csv"
    return Response(output, mimetype='text/csv',
                    headers={"Content-Disposition": f"attachment;filename={filename}"})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=FLASK_PORT, debug=True)
