"""
Tests unitarios para src/mysql_db.py

Cubre:
- calcular_monto_participante: lógica pura de suma de montos de marcas
  participantes (la función más importante, sin acceso a BD).
- get_rodelag_connection / get_dev_connection: verifica los parámetros de
  conexión introducidos/garantizados por el PR (charset='utf8mb4',
  use_unicode=True, connect_timeout=10) y que cada función apunte a la
  base de datos correcta (DB_NAME vs DB_NAME_DEV).

Ejecución:
    .venv/bin/python -m pytest tests/test_mysql_db.py -v
"""
from unittest.mock import patch

import pytest

from src import mysql_db


# Marcas participantes tal como las pasa el código de producción:
# siempre en MAYÚSCULAS (ver validar_factura_para_sorteo / validar_factura_completa,
# que hacen [m.upper() for m in MARCAS]).
MARCAS_PARTICIPANTES = ['LG', 'SANKEY', 'MYSTIC', 'RCA', 'HISENSE', 'SAMSUNG']


def _producto(marca=None, unidades=0, precio=0, total=0):
    """Helper para construir un dict de producto como el que devuelve la BD."""
    return {
        'Marca': marca,
        'Unidades': unidades,
        'Precio_Unitario': precio,
        'Total': total,
    }


# ---------------------------------------------------------------------------
# calcular_monto_participante  (LÓGICA PURA)
# ---------------------------------------------------------------------------
class TestCalcularMontoParticipante:

    # --- Casos positivos: marca participante ---
    class TestCuandoLaMarcaParticipa:

        def test_usa_total_cuando_es_mayor_a_cero(self):
            # Arrange
            productos = [_producto(marca='LG', unidades=1, precio=50, total=150.00)]
            # Act
            monto = mysql_db.calcular_monto_participante(productos, MARCAS_PARTICIPANTES)
            # Assert: usa Total (150), NO unidades*precio (50)
            assert monto == 150.00

        def test_marca_el_producto_como_aplica_true(self):
            # Arrange
            productos = [_producto(marca='Samsung', unidades=1, precio=100, total=200.00)]
            # Act
            mysql_db.calcular_monto_participante(productos, MARCAS_PARTICIPANTES)
            # Assert
            assert productos[0]['aplica'] is True

        def test_usa_unidades_por_precio_cuando_total_es_cero(self):
            # Arrange: Total = 0 -> debe usar Unidades * Precio_Unitario
            productos = [_producto(marca='RCA', unidades=3, precio=40.00, total=0)]
            # Act
            monto = mysql_db.calcular_monto_participante(productos, MARCAS_PARTICIPANTES)
            # Assert
            assert monto == 120.00

        def test_usa_unidades_por_precio_cuando_total_es_negativo(self):
            # Arrange: Total <= 0 (negativo) también recae en Unidades * Precio
            productos = [_producto(marca='RCA', unidades=2, precio=30.00, total=-5)]
            # Act
            monto = mysql_db.calcular_monto_participante(productos, MARCAS_PARTICIPANTES)
            # Assert
            assert monto == 60.00

        def test_suma_varios_productos_participantes(self):
            # Arrange
            productos = [
                _producto(marca='LG', total=100.00),
                _producto(marca='Hisense', total=50.50),
                _producto(marca='Mystic', unidades=2, precio=10.00, total=0),  # 20.00
            ]
            # Act
            monto = mysql_db.calcular_monto_participante(productos, MARCAS_PARTICIPANTES)
            # Assert
            assert monto == 170.50

    # --- Casos de marca NO participante ---
    class TestCuandoLaMarcaNoParticipa:

        def test_ignora_producto_de_marca_no_participante(self):
            # Arrange
            productos = [_producto(marca='Sony', total=999.99)]
            # Act
            monto = mysql_db.calcular_monto_participante(productos, MARCAS_PARTICIPANTES)
            # Assert
            assert monto == 0.0

        def test_marca_el_producto_no_participante_como_aplica_false(self):
            # Arrange
            productos = [_producto(marca='Sony', total=999.99)]
            # Act
            mysql_db.calcular_monto_participante(productos, MARCAS_PARTICIPANTES)
            # Assert
            assert productos[0]['aplica'] is False

        def test_solo_suma_los_participantes_de_una_mezcla(self):
            # Arrange: mezcla de participantes y no participantes
            productos = [
                _producto(marca='LG', total=100.00),      # participa
                _producto(marca='Sony', total=500.00),    # NO participa
                _producto(marca='Samsung', total=80.00),  # participa
            ]
            # Act
            monto = mysql_db.calcular_monto_participante(productos, MARCAS_PARTICIPANTES)
            # Assert
            assert monto == 180.00

        def test_marca_aplica_correctamente_en_cada_item_de_la_mezcla(self):
            # Arrange
            productos = [
                _producto(marca='LG', total=100.00),
                _producto(marca='Sony', total=500.00),
                _producto(marca='Samsung', total=80.00),
            ]
            # Act
            mysql_db.calcular_monto_participante(productos, MARCAS_PARTICIPANTES)
            # Assert
            assert [p['aplica'] for p in productos] == [True, False, True]

    # --- Casos de normalización de la marca (espacios / minúsculas) ---
    class TestNormalizacionDeMarca:

        def test_marca_con_espacios_y_minusculas_igual_matchea(self):
            # Arrange: ' lg ' debe matchear con 'LG' (strip + upper)
            productos = [_producto(marca=' lg ', total=100.00)]
            # Act
            monto = mysql_db.calcular_monto_participante(productos, MARCAS_PARTICIPANTES)
            # Assert
            assert monto == 100.00
            assert productos[0]['aplica'] is True

        def test_marca_en_minusculas_matchea(self):
            # Arrange
            productos = [_producto(marca='samsung', total=75.00)]
            # Act
            monto = mysql_db.calcular_monto_participante(productos, MARCAS_PARTICIPANTES)
            # Assert
            assert monto == 75.00
            assert productos[0]['aplica'] is True

        def test_marca_mayusculas_con_espacios_internos_circundantes(self):
            # Arrange: espacios alrededor de una marca ya en mayúsculas
            productos = [_producto(marca='  HISENSE  ', total=33.33)]
            # Act
            monto = mysql_db.calcular_monto_participante(productos, MARCAS_PARTICIPANTES)
            # Assert
            assert monto == 33.33
            assert productos[0]['aplica'] is True

    # --- Casos límite ---
    class TestCasosLimite:

        def test_lista_vacia_devuelve_cero(self):
            # Arrange / Act
            monto = mysql_db.calcular_monto_participante([], MARCAS_PARTICIPANTES)
            # Assert
            assert monto == 0.0

        def test_marca_none_no_aplica(self):
            # Arrange: Marca None -> (None or '') -> '' -> no aplica
            productos = [_producto(marca=None, total=100.00)]
            # Act
            monto = mysql_db.calcular_monto_participante(productos, MARCAS_PARTICIPANTES)
            # Assert
            assert monto == 0.0
            assert productos[0]['aplica'] is False

        def test_marca_vacia_no_aplica(self):
            # Arrange
            productos = [_producto(marca='   ', total=100.00)]
            # Act
            monto = mysql_db.calcular_monto_participante(productos, MARCAS_PARTICIPANTES)
            # Assert
            assert monto == 0.0
            assert productos[0]['aplica'] is False

        def test_total_none_con_unidades_y_precio_validos(self):
            # Arrange: Total=None -> (None or 0)=0 -> usa Unidades*Precio
            productos = [_producto(marca='LG', unidades=2, precio=25.00, total=None)]
            # Act
            monto = mysql_db.calcular_monto_participante(productos, MARCAS_PARTICIPANTES)
            # Assert
            assert monto == 50.00

        def test_unidades_y_precio_none_dan_cero(self):
            # Arrange: Total=0 y Unidades/Precio None -> (None or 0) -> 0*0 = 0
            productos = [_producto(marca='LG', unidades=None, precio=None, total=0)]
            # Act
            monto = mysql_db.calcular_monto_participante(productos, MARCAS_PARTICIPANTES)
            # Assert
            assert monto == 0.0
            # Aunque el monto sea 0, el producto SÍ es de marca participante
            assert productos[0]['aplica'] is True

        def test_todos_los_valores_none(self):
            # Arrange: Marca None además de los montos -> no aplica, monto 0
            productos = [_producto(marca=None, unidades=None, precio=None, total=None)]
            # Act
            monto = mysql_db.calcular_monto_participante(productos, MARCAS_PARTICIPANTES)
            # Assert
            assert monto == 0.0
            assert productos[0]['aplica'] is False

        def test_marcas_participantes_vacias_no_aplica_nada(self):
            # Arrange: si no hay marcas participantes, nada suma
            productos = [_producto(marca='LG', total=100.00)]
            # Act
            monto = mysql_db.calcular_monto_participante(productos, [])
            # Assert
            assert monto == 0.0
            assert productos[0]['aplica'] is False

        def test_redondea_a_dos_decimales(self):
            # Arrange: tres líneas de 0.333... que suman 0.999... -> round(,2)
            productos = [
                _producto(marca='LG', total=0.333),
                _producto(marca='LG', total=0.333),
                _producto(marca='LG', total=0.334),
            ]
            # Act
            monto = mysql_db.calcular_monto_participante(productos, MARCAS_PARTICIPANTES)
            # Assert
            assert monto == 1.0

        def test_total_como_string_numerico_se_convierte(self):
            # Arrange: la BD a veces entrega valores como string; float() los acepta
            productos = [_producto(marca='LG', total='125.50')]
            # Act
            monto = mysql_db.calcular_monto_participante(productos, MARCAS_PARTICIPANTES)
            # Assert
            assert monto == 125.50


# ---------------------------------------------------------------------------
# get_rodelag_connection / get_dev_connection  (conexiones)
# ---------------------------------------------------------------------------
class TestGetRodelagConnection:

    @patch('src.mysql_db.pymysql.connect')
    def test_invoca_connect_una_vez(self, mock_connect):
        # Act
        mysql_db.get_rodelag_connection()
        # Assert
        mock_connect.assert_called_once()

    @patch('src.mysql_db.pymysql.connect')
    def test_usa_charset_utf8mb4(self, mock_connect):
        # Act
        mysql_db.get_rodelag_connection()
        # Assert (cambio del PR para soportar acentos/UTF-8)
        _, kwargs = mock_connect.call_args
        assert kwargs['charset'] == 'utf8mb4'

    @patch('src.mysql_db.pymysql.connect')
    def test_usa_use_unicode_true(self, mock_connect):
        # Act
        mysql_db.get_rodelag_connection()
        # Assert (cambio del PR)
        _, kwargs = mock_connect.call_args
        assert kwargs['use_unicode'] is True

    @patch('src.mysql_db.pymysql.connect')
    def test_usa_connect_timeout_10(self, mock_connect):
        # Act
        mysql_db.get_rodelag_connection()
        # Assert
        _, kwargs = mock_connect.call_args
        assert kwargs['connect_timeout'] == 10

    @patch('src.mysql_db.DB_NAME', 'BD_PRODUCCION_SENTINELA')
    @patch('src.mysql_db.pymysql.connect')
    def test_usa_la_base_de_datos_de_produccion(self, mock_connect):
        # Act
        mysql_db.get_rodelag_connection()
        # Assert: producción usa DB_NAME
        _, kwargs = mock_connect.call_args
        assert kwargs['database'] == 'BD_PRODUCCION_SENTINELA'

    @patch('src.mysql_db.pymysql.connect')
    def test_retorna_la_conexion_creada(self, mock_connect):
        # Arrange
        mock_connect.return_value = 'conexion_fake'
        # Act
        resultado = mysql_db.get_rodelag_connection()
        # Assert
        assert resultado == 'conexion_fake'


class TestGetDevConnection:

    @patch('src.mysql_db.pymysql.connect')
    def test_invoca_connect_una_vez(self, mock_connect):
        # Act
        mysql_db.get_dev_connection()
        # Assert
        mock_connect.assert_called_once()

    @patch('src.mysql_db.pymysql.connect')
    def test_usa_charset_utf8mb4(self, mock_connect):
        # Act
        mysql_db.get_dev_connection()
        # Assert
        _, kwargs = mock_connect.call_args
        assert kwargs['charset'] == 'utf8mb4'

    @patch('src.mysql_db.pymysql.connect')
    def test_usa_use_unicode_true(self, mock_connect):
        # Act
        mysql_db.get_dev_connection()
        # Assert
        _, kwargs = mock_connect.call_args
        assert kwargs['use_unicode'] is True

    @patch('src.mysql_db.pymysql.connect')
    def test_usa_connect_timeout_10(self, mock_connect):
        # Act
        mysql_db.get_dev_connection()
        # Assert
        _, kwargs = mock_connect.call_args
        assert kwargs['connect_timeout'] == 10

    @patch('src.mysql_db.DB_NAME_DEV', 'BD_DESARROLLO_SENTINELA')
    @patch('src.mysql_db.pymysql.connect')
    def test_usa_la_base_de_datos_de_desarrollo(self, mock_connect):
        # Act
        mysql_db.get_dev_connection()
        # Assert: desarrollo usa DB_NAME_DEV
        _, kwargs = mock_connect.call_args
        assert kwargs['database'] == 'BD_DESARROLLO_SENTINELA'

    @patch('src.mysql_db.DB_NAME', 'BD_PRODUCCION_SENTINELA')
    @patch('src.mysql_db.DB_NAME_DEV', 'BD_DESARROLLO_SENTINELA')
    @patch('src.mysql_db.pymysql.connect')
    def test_dev_no_apunta_a_la_base_de_produccion(self, mock_connect):
        # Act
        mysql_db.get_dev_connection()
        # Assert: garantiza que dev != produccion
        _, kwargs = mock_connect.call_args
        assert kwargs['database'] == 'BD_DESARROLLO_SENTINELA'
        assert kwargs['database'] != 'BD_PRODUCCION_SENTINELA'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
