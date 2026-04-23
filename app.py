import os
import random
import string
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
    obtener_participante_por_cedula, obtener_factura_por_numero,
    obtener_boletos_por_participante, obtener_estadisticas,
    obtener_premios_disponibles, obtener_boletos_para_sorteo,
    asignar_ganador, obtener_ganadores, obtener_todas_las_facturas,
    invalidar_boletos_por_factura
)
from src.mysql_db import (
    buscar_cliente_por_ruc, validar_factura_completa
)

app = Flask(__name__)
app.secret_key = SECRET_KEY


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


def calcular_boletos(monto, credito_una):
    boletos = int(monto // MONTO_BOLETO)
    if credito_una:
        boletos *= MULTIPLICADOR_CREDITO_UNA
    return boletos


@app.route('/')
def index():
    return render_template('index.html', marcas=MARCAS, fecha_inicio=FECHA_INICIO, fecha_fin=FECHA_FIN)


@app.route('/api/registrar', methods=['POST'])
def api_registrar():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Datos inválidos'}), 400

    # Validar campos requeridos
    campos_requeridos = ['nombre', 'cedula', 'telefono', 'email', 'numero_factura', 'marca', 'monto', 'fecha_compra']
    for campo in campos_requeridos:
        if not data.get(campo):
            return jsonify({'success': False, 'message': f'El campo {campo} es requerido'}), 400

    nombre = data.get('nombre', '').strip()
    cedula = data.get('cedula', '').strip()
    telefono = data.get('telefono', '').strip()
    email = data.get('email', '').strip()
    direccion = data.get('direccion', '').strip()
    numero_factura = data.get('numero_factura', '').strip()
    marca_solicitada = data.get('marca', '').strip()
    monto = float(data.get('monto', 0))
    sucursal = data.get('sucursal', '').strip()
    fecha_compra = data.get('fecha_compra', '').strip()
    credito_una = bool(data.get('credito_una', False))

    # === VALIDACIONES CONTRA BASE DE DATOS RODELAG ===
    
    # 1. Validar que el cliente exista en Rodelag
    cliente_rodelag = buscar_cliente_por_ruc(cedula)
    if not cliente_rodelag:
        return jsonify({'success': False, 'message': 'La cédula no existe en nuestro sistema de clientes. Verifique que sea un cliente registrado de Rodelag.'}), 400

    # 2. Validar factura contra Rodelag
    exito, mensaje_error, datos_factura = validar_factura_completa(numero_factura, cedula, monto)
    if not exito:
        return jsonify({'success': False, 'message': mensaje_error}), 400

    # 3. Verificar que la marca solicitada esté en las marcas de la factura
    marcas_factura = [m.upper() for m in datos_factura['marcas']]
    if marca_solicitada.upper() not in marcas_factura:
        marcas_str = ', '.join(datos_factura['marcas'])
        return jsonify({'success': False, 'message': f'La factura contiene productos de las marcas: {marcas_str}, pero no de {marca_solicitada}.'}), 400

    # 4. Verificar si la factura ya fue registrada en la promoción
    if obtener_factura_por_numero(numero_factura):
        return jsonify({'success': False, 'message': 'Esta factura ya fue registrada anteriormente en la promoción.'}), 400

    # === REGISTRO EN LA PROMOCIÓN ===
    
    # Insertar participante
    participante_id = insertar_participante(nombre, cedula, telefono, email, direccion)
    if not participante_id:
        return jsonify({'success': False, 'message': 'Error al registrar participante'}), 500

    # Calcular boletos (usamos el SubTotal real de la factura de Rodelag)
    monto_real = datos_factura['subtotal']
    boletos = calcular_boletos(monto_real, credito_una)

    # Insertar factura
    factura_id = insertar_factura(participante_id, numero_factura, marca_solicitada, monto_real, 
                                   datos_factura.get('sucursal') or sucursal, datos_factura['fecha'], credito_una, boletos)
    if not factura_id:
        return jsonify({'success': False, 'message': 'Error al registrar factura'}), 500

    # Generar boletos
    boletos_generados = []
    for _ in range(boletos):
        numero_boleto = generar_numero_boleto()
        while not insertar_boleto(participante_id, factura_id, numero_boleto):
            numero_boleto = generar_numero_boleto()
        boletos_generados.append(numero_boleto)

    return jsonify({
        'success': True,
        'message': 'Registro exitoso',
        'boletos': boletos,
        'numeros_boletos': boletos_generados,
        'credito_una': credito_una,
        'monto_validado': monto_real,
        'cliente': datos_factura['cliente_nombre']
    })


@app.route('/api/consultar', methods=['GET'])
def api_consultar():
    cedula = request.args.get('cedula', '').strip()
    if not cedula:
        return jsonify({'success': False, 'message': 'Cédula requerida'}), 400

    participante = obtener_participante_por_cedula(cedula)
    if not participante:
        return jsonify({'success': False, 'message': 'No se encontraron registros para esta cédula'}), 404

    boletos = obtener_boletos_por_participante(participante['id'])
    return jsonify({
        'success': True,
        'participante': participante,
        'total_boletos': len(boletos),
        'boletos': boletos
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
    stats = obtener_estadisticas()
    return render_template('admin_dashboard.html', stats=stats, sorteos=SORTEOS)


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


@app.route('/api/admin/realizar-sorteo', methods=['POST'])
@login_required
def api_realizar_sorteo():
    data = request.get_json()
    sorteo_id = data.get('sorteo_id')
    premio_id = data.get('premio_id')

    if not sorteo_id or not premio_id:
        return jsonify({'success': False, 'message': 'Datos incompletos'}), 400

    premios_disp = obtener_premios_disponibles(sorteo_id)
    premio = next((p for p in premios_disp if p['id'] == premio_id), None)
    if not premio:
        return jsonify({'success': False, 'message': 'Premio no disponible'}), 400

    boletos = obtener_boletos_para_sorteo()
    if not boletos:
        return jsonify({'success': False, 'message': 'No hay boletos disponibles para el sorteo'}), 400

    # Seleccionar ganador aleatorio
    ganador_boleto = random.choice(boletos)
    asignar_ganador(ganador_boleto['participante_id'], premio_id, sorteo_id, ganador_boleto['id'])

    return jsonify({
        'success': True,
        'message': 'Ganador seleccionado',
        'ganador': {
            'nombre': ganador_boleto['nombre'],
            'cedula': ganador_boleto['cedula'],
            'telefono': ganador_boleto['telefono'],
            'boleto': ganador_boleto['numero_boleto']
        }
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


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=FLASK_PORT, debug=True)
