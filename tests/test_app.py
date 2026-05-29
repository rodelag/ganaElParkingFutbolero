"""
Tests unitarios para app.py (proyecto Flask "Gana el Parking Futbolero").

Cobertura:
  1. app.miles_filter        -> formateo con separador de miles
  2. app._serializar_candidato -> serializacion de fila de BD a dict de respuesta
  3. app.add_charset         -> after_request fuerza charset=utf-8 en text/html
  4. /admin/dashboard        -> NO-regresion del fix de fuga de conexion a Rodelag

Ejecutar con:
    .venv/bin/python -m pytest tests/test_app.py -v

Notas:
  - Se importa el modulo como `app`; la instancia Flask es `app.app`.
  - Para las rutas se usa `app.app.test_client()`.
  - No se conecta a ninguna BD real: se parchean las funciones de acceso a datos.
"""

from unittest.mock import patch

import pytest
from flask import Response

import app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    """Cliente de pruebas Flask con TESTING activado."""
    app.app.config['TESTING'] = True
    with app.app.test_client() as c:
        yield c


@pytest.fixture
def app_context():
    """Contexto de aplicacion para funciones que usan `session`, `url_for`, etc.

    add_charset no necesita request context, pero render/url_for si lo
    necesitarian; este fixture se usa solo donde es estrictamente necesario.
    """
    with app.app.app_context():
        yield


# ---------------------------------------------------------------------------
# 1. app.miles_filter
# ---------------------------------------------------------------------------

class TestMilesFilter:
    """Filtro de plantilla 'miles': formatea enteros con separador de comas."""

    # --- Casos validos / camino feliz ---

    def test_formatea_mil_con_coma(self):
        # Arrange / Act
        resultado = app.miles_filter(1000)
        # Assert
        assert resultado == "1,000"

    def test_formatea_millones_con_comas(self):
        assert app.miles_filter(1234567) == "1,234,567"

    def test_cero_sin_separador(self):
        assert app.miles_filter(0) == "0"

    def test_acepta_string_numerica(self):
        # int("123") == 123 -> "123" (no llega a 4 digitos, sin coma)
        assert app.miles_filter("1234") == "1,234"

    def test_acepta_float_lo_trunca_a_entero(self):
        # int(1999.9) == 1999
        assert app.miles_filter(1999.9) == "1,999"

    def test_numero_negativo(self):
        assert app.miles_filter(-1000) == "-1,000"

    # --- Casos de error: el except (ValueError, TypeError) devuelve el value ---

    def test_string_no_numerica_devuelve_value_original(self):
        # int("abc") lanza ValueError -> retorna "abc"
        assert app.miles_filter("abc") == "abc"

    def test_none_devuelve_none(self):
        # int(None) lanza TypeError -> retorna None
        assert app.miles_filter(None) is None

    def test_em_dash_devuelve_em_dash(self):
        # int("—") lanza ValueError -> retorna "—"
        assert app.miles_filter("—") == "—"

    def test_lista_devuelve_value_original(self):
        # int([...]) lanza TypeError -> retorna la lista intacta (no-regresion
        # del cambio de except desnudo a except (ValueError, TypeError))
        valor = [1, 2, 3]
        assert app.miles_filter(valor) is valor


# ---------------------------------------------------------------------------
# 2. app._serializar_candidato
# ---------------------------------------------------------------------------

class TestSerializarCandidato:
    """Convierte una fila de BD (dict) en el dict de respuesta del candidato."""

    @staticmethod
    def _fila_completa():
        """Fila tipica con todos los campos presentes y no nulos."""
        return {
            'id': 10,
            'participante_id': 99,
            'nombre': 'Juan Perez',
            'cedula': '8-888-8888',
            'telefono': '6000-0000',
            'email': 'juan@example.com',
            'numero_boleto': 'B-12345',
            'numero_factura': 'F-001',
            'marca': 'LG',
        }

    # --- Camino feliz: todos los campos presentes ---

    def test_incluye_factura_y_marca(self):
        # Arrange
        ganador = self._fila_completa()
        # Act
        resultado = app._serializar_candidato(ganador)
        # Assert
        assert resultado['factura'] == 'F-001'
        assert resultado['marca'] == 'LG'

    def test_mapea_todas_las_claves_correctamente(self):
        ganador = self._fila_completa()
        resultado = app._serializar_candidato(ganador)
        assert resultado == {
            'id': 10,
            'participante_id': 99,
            'nombre': 'Juan Perez',
            'cedula': '8-888-8888',
            'telefono': '6000-0000',
            'email': 'juan@example.com',
            'boleto': 'B-12345',   # numero_boleto -> boleto
            'factura': 'F-001',    # numero_factura -> factura
            'marca': 'LG',
        }

    def test_numero_boleto_se_mapea_a_boleto(self):
        ganador = self._fila_completa()
        resultado = app._serializar_candidato(ganador)
        assert resultado['boleto'] == 'B-12345'
        # La clave de salida es 'boleto', no 'numero_boleto'
        assert 'numero_boleto' not in resultado

    # --- Valores None -> em dash / cadena vacia ---

    def test_factura_none_devuelve_em_dash(self):
        ganador = self._fila_completa()
        ganador['numero_factura'] = None
        resultado = app._serializar_candidato(ganador)
        assert resultado['factura'] == '—'

    def test_marca_none_devuelve_em_dash(self):
        ganador = self._fila_completa()
        ganador['marca'] = None
        resultado = app._serializar_candidato(ganador)
        assert resultado['marca'] == '—'

    def test_email_none_devuelve_cadena_vacia(self):
        ganador = self._fila_completa()
        ganador['email'] = None
        resultado = app._serializar_candidato(ganador)
        assert resultado['email'] == ''

    # --- Claves ausentes (usa .get) -> em dash / cadena vacia ---

    def test_factura_y_marca_ausentes_devuelven_em_dash(self):
        # Arrange: dict sin numero_factura ni marca ni email (campos con .get)
        ganador = {
            'id': 5,
            'participante_id': 50,
            'nombre': 'Ana Lopez',
            'cedula': '3-111-2222',
            'telefono': '6111-1111',
            'numero_boleto': 'B-00001',
        }
        # Act
        resultado = app._serializar_candidato(ganador)
        # Assert
        assert resultado['factura'] == '—'
        assert resultado['marca'] == '—'
        assert resultado['email'] == ''

    def test_factura_vacia_devuelve_em_dash(self):
        # Cadena vacia es falsy -> el `or '—'` la reemplaza
        ganador = self._fila_completa()
        ganador['numero_factura'] = ''
        resultado = app._serializar_candidato(ganador)
        assert resultado['factura'] == '—'

    # --- Casos de error: faltan claves de acceso directo (sin .get) ---

    def test_falta_clave_obligatoria_lanza_keyerror(self):
        # 'nombre' se accede con ganador['nombre'] (sin .get): debe fallar.
        ganador = {
            'id': 1,
            'participante_id': 2,
            'cedula': '1-2-3',
            'telefono': '6000',
            'numero_boleto': 'B-1',
        }
        with pytest.raises(KeyError):
            app._serializar_candidato(ganador)


# ---------------------------------------------------------------------------
# 3. app.add_charset (after_request)
# ---------------------------------------------------------------------------

class TestAddCharset:
    """El hook after_request fuerza charset=utf-8 en respuestas text/html."""

    def test_response_html_obtiene_charset_utf8(self, app_context):
        # Arrange: Response HTML sin charset explicito util
        resp = Response('<html></html>', content_type='text/html')
        # Act
        resultado = app.add_charset(resp)
        # Assert
        assert resultado.headers['Content-Type'] == 'text/html; charset=utf-8'

    def test_response_html_con_charset_previo_se_normaliza(self, app_context):
        resp = Response('<html></html>', content_type='text/html; charset=latin-1')
        resultado = app.add_charset(resp)
        assert resultado.headers['Content-Type'] == 'text/html; charset=utf-8'

    def test_response_json_no_se_modifica(self, app_context):
        # No empieza con text/html -> el Content-Type queda igual
        resp = Response('{}', content_type='application/json')
        resultado = app.add_charset(resp)
        assert resultado.headers['Content-Type'] == 'application/json'

    def test_retorna_la_misma_response(self, app_context):
        resp = Response('hola', content_type='text/plain')
        resultado = app.add_charset(resp)
        assert resultado is resp

    def test_via_test_client_login_publico(self, client):
        # GET a la ruta publica /admin (login). Confirma que el after_request
        # se aplica en una peticion real y deja el charset correcto.
        respuesta = client.get('/admin')
        assert respuesta.status_code == 200
        assert respuesta.headers['Content-Type'] == 'text/html; charset=utf-8'


# ---------------------------------------------------------------------------
# 4. /admin/dashboard - NO-regresion del fix de fuga de conexion
# ---------------------------------------------------------------------------

class TestAdminDashboardElegibilidad:
    """Cuando la conexion a Rodelag falla, el dashboard NO debe romperse.

    Comportamiento esperado (app.py ~394-432):
      - stats['total_facturas_rodelag_elegibles'] == '—'
      - stats['total_clientes_rodelag_elegibles'] == '—'
      - se registra un warning
      - la respuesta sigue siendo 200 (no 500)

    Estrategia de aislamiento (sin tocar BD real):
      - sesion admin via session_transaction (clave 'admin', segun login_required)
      - parche de init_config_table / obtener_estadisticas / obtener_config en
        el namespace `app` (ahi se resuelven al estar importadas en app.py)
      - parche de get_rodelag_connection en `src.mysql_db` porque la vista hace
        `from src.mysql_db import get_rodelag_connection` DENTRO de la funcion,
        por lo que se resuelve en tiempo de ejecucion en ese modulo.
    """

    @staticmethod
    def _stats_base():
        """Dict de estadisticas base, como lo devolveria obtener_estadisticas()."""
        return {
            'total_participantes': 3,
            'total_facturas': 5,
            'total_boletos': 12,
            'total_ganadores': 1,
            'monto_total': 1500,
        }

    def test_dashboard_con_fallo_de_rodelag_responde_200_y_em_dash(self, client):
        # Arrange: sesion admin
        with client.session_transaction() as s:
            s['admin'] = 'admin'

        stats_capturadas = {}

        def _fake_render(template_name, **context):
            # Capturamos el dict stats que recibe la plantilla para validarlo
            # sin depender del HTML renderizado.
            stats_capturadas.update(context.get('stats', {}))
            return 'OK-DASHBOARD'

        with patch('app.init_config_table'), \
             patch('app.obtener_estadisticas', return_value=self._stats_base()), \
             patch('app.obtener_config', return_value='1'), \
             patch('src.mysql_db.get_rodelag_connection',
                   side_effect=Exception('conexion a produccion caida')), \
             patch('app.render_template', side_effect=_fake_render), \
             patch.object(app.app.logger, 'warning') as mock_warning:
            # Act
            respuesta = client.get('/admin/dashboard')

        # Assert: el dashboard NO se rompe pese al fallo de conexion
        assert respuesta.status_code == 200
        assert respuesta.data == b'OK-DASHBOARD'
        # Los elegibles quedan en em dash
        assert stats_capturadas['total_facturas_rodelag_elegibles'] == '—'
        assert stats_capturadas['total_clientes_rodelag_elegibles'] == '—'
        # Las estadisticas base se preservan
        assert stats_capturadas['total_participantes'] == 3
        assert stats_capturadas['total_facturas'] == 5
        # Se registro el warning del fallo de conexion
        assert mock_warning.called

    def test_dashboard_camino_feliz_usa_conteos_de_rodelag(self, client):
        # Verifica que cuando la conexion funciona, se asignan los conteos
        # devueltos por la consulta (camino feliz del try).
        with client.session_transaction() as s:
            s['admin'] = 'admin'

        stats_capturadas = {}

        def _fake_render(template_name, **context):
            stats_capturadas.update(context.get('stats', {}))
            return 'OK'

        # Conexion falsa: cursor.fetchone() devuelve la fila con los conteos.
        class _FakeCursor:
            def execute(self, *a, **k):
                return None

            def fetchone(self):
                return {
                    'total_facturas_elegibles': 42,
                    'total_clientes_elegibles': 7,
                }

        class _FakeConn:
            def __init__(self):
                self.cerrada = False

            def cursor(self):
                return _FakeCursor()

            def close(self):
                self.cerrada = True

        fake_conn = _FakeConn()

        with patch('app.init_config_table'), \
             patch('app.obtener_estadisticas', return_value=self._stats_base()), \
             patch('app.obtener_config', return_value='1'), \
             patch('src.mysql_db.get_rodelag_connection', return_value=fake_conn), \
             patch('app.render_template', side_effect=_fake_render):
            respuesta = client.get('/admin/dashboard')

        assert respuesta.status_code == 200
        assert stats_capturadas['total_facturas_rodelag_elegibles'] == 42
        assert stats_capturadas['total_clientes_rodelag_elegibles'] == 7
        # No-regresion del fix: la conexion se cierra en el finally
        assert fake_conn.cerrada is True

    def test_dashboard_sin_sesion_redirige_a_login(self, client):
        # login_required: sin 'admin' en session redirige (302) a /admin.
        respuesta = client.get('/admin/dashboard')
        assert respuesta.status_code == 302
        assert '/admin' in respuesta.headers['Location']
