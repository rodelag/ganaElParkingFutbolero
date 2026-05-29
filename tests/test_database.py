"""
Tests unitarios para src/database.py

Estos tests cubren las funciones modificadas/nuevas del flujo de sorteo del
proyecto "Gana el Parking Futbolero". No requieren una base de datos real:
se parchea `src.database.get_connection` con mocks de unittest.mock para
inspeccionar el SQL ejecutado, los parametros enviados y el manejo de la
conexion (commit/close).

Ejecutar con:
    .venv/bin/python -m pytest tests/test_database.py -v
"""

import re
from unittest.mock import patch, MagicMock

import pytest

from src import database
from src.config import MARCAS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_conn(fetchall=None, fetchone=None, fetchone_side_effect=None,
              lastrowid=None):
    """Crea un par (conn, cursor) mockeado que simula pymysql/DictCursor.

    - `fetchall`: lista devuelta por cursor.fetchall().
    - `fetchone`: valor devuelto por cursor.fetchone().
    - `fetchone_side_effect`: lista de valores devueltos en llamadas
      sucesivas a cursor.fetchone() (util cuando una funcion llama
      fetchone() varias veces, como obtener_estadisticas).
    - `lastrowid`: valor de cursor.lastrowid tras un INSERT.
    """
    conn = MagicMock(name='conn')
    cursor = MagicMock(name='cursor')
    conn.cursor.return_value = cursor
    cursor.fetchall.return_value = fetchall if fetchall is not None else []
    if fetchone_side_effect is not None:
        cursor.fetchone.side_effect = fetchone_side_effect
    else:
        cursor.fetchone.return_value = fetchone
    if lastrowid is not None:
        cursor.lastrowid = lastrowid
    return conn, cursor


def normalizar_sql(sql):
    """Colapsa espacios en blanco para comparar fragmentos de SQL sin
    depender de la indentacion exacta."""
    return re.sub(r'\s+', ' ', sql).strip()


def sql_ejecutado(cursor, call_index=-1):
    """Devuelve el string SQL (primer argumento posicional) de la llamada
    indicada a cursor.execute."""
    args, _ = cursor.execute.call_args_list[call_index]
    return args[0]


def params_ejecutados(cursor, call_index=-1):
    """Devuelve la tupla de parametros (segundo argumento posicional) de la
    llamada indicada a cursor.execute, o None si no hubo parametros."""
    args, _ = cursor.execute.call_args_list[call_index]
    return args[1] if len(args) > 1 else None


# ===========================================================================
# 1) obtener_boletos_para_sorteo(marca=None)
# ===========================================================================

class TestObtenerBoletosParaSorteo:
    """Verifica el comportamiento de obtener_boletos_para_sorteo en sus dos
    ramas (con marca especifica y sin marca) ademas de la no-regresion de
    que ya NO usa ORDER BY RAND()."""

    def test_con_marca_usa_filtro_marca_igual_y_param_unico(self):
        # Arrange
        filas = [{'id': 1, 'numero_boleto': 'B-001'}]
        conn, cursor = make_conn(fetchall=filas)

        # Act
        with patch('src.database.get_connection', return_value=conn):
            resultado = database.obtener_boletos_para_sorteo(marca='LG')

        # Assert: SQL contiene el filtro por marca exacta y params correctos
        sql = normalizar_sql(sql_ejecutado(cursor))
        assert 'f.marca = %s' in sql
        assert params_ejecutados(cursor) == ('LG',)
        assert resultado == filas

    def test_con_marca_no_usa_in_de_marcas(self):
        # Arrange
        conn, cursor = make_conn(fetchall=[])

        # Act
        with patch('src.database.get_connection', return_value=conn):
            database.obtener_boletos_para_sorteo(marca='Samsung')

        # Assert: la rama con marca NO debe construir el IN(...) de MARCAS
        sql = normalizar_sql(sql_ejecutado(cursor))
        assert 'f.marca IN (' not in sql

    def test_sin_marca_usa_in_con_todas_las_marcas(self):
        # Arrange
        conn, cursor = make_conn(fetchall=[])

        # Act
        with patch('src.database.get_connection', return_value=conn):
            database.obtener_boletos_para_sorteo()  # marca=None por defecto

        # Assert: usa IN(...) y los params son exactamente tuple(MARCAS)
        sql = normalizar_sql(sql_ejecutado(cursor))
        assert 'f.marca IN (' in sql
        assert params_ejecutados(cursor) == tuple(MARCAS)

    def test_sin_marca_numero_de_placeholders_igual_a_len_marcas(self):
        # Arrange
        conn, cursor = make_conn(fetchall=[])

        # Act
        with patch('src.database.get_connection', return_value=conn):
            database.obtener_boletos_para_sorteo(marca=None)

        # Assert: el IN(...) tiene exactamente len(MARCAS) placeholders %s
        sql = sql_ejecutado(cursor)
        # Extraer el contenido del IN(...) para contar placeholders ahi dentro
        match = re.search(r'f\.marca IN \(([^)]*)\)', normalizar_sql(sql))
        assert match is not None
        placeholders = match.group(1).count('%s')
        assert placeholders == len(MARCAS)

    def test_ambas_ramas_hacen_join_a_facturas_y_seleccionan_campos(self):
        # Arrange / Act: rama con marca
        conn1, cursor1 = make_conn(fetchall=[])
        with patch('src.database.get_connection', return_value=conn1):
            database.obtener_boletos_para_sorteo(marca='RCA')
        sql_con_marca = normalizar_sql(sql_ejecutado(cursor1))

        # Arrange / Act: rama sin marca
        conn2, cursor2 = make_conn(fetchall=[])
        with patch('src.database.get_connection', return_value=conn2):
            database.obtener_boletos_para_sorteo()
        sql_sin_marca = normalizar_sql(sql_ejecutado(cursor2))

        # Assert: ambas hacen JOIN a facturas e incluyen numero_factura y f.marca
        for sql in (sql_con_marca, sql_sin_marca):
            assert database.TABLE_FACTURAS in sql
            assert 'JOIN' in sql
            assert 'numero_factura' in sql
            assert 'f.marca' in sql

    def test_no_regresion_no_ordena_por_rand(self):
        """No-regresion: la aleatoriedad ahora vive en app.py (random.choice),
        por lo que el SQL NO debe contener ORDER BY RAND()."""
        # Arrange / Act: rama con marca
        conn1, cursor1 = make_conn(fetchall=[])
        with patch('src.database.get_connection', return_value=conn1):
            database.obtener_boletos_para_sorteo(marca='LG')
        sql_con_marca = sql_ejecutado(cursor1).upper()

        # Arrange / Act: rama sin marca
        conn2, cursor2 = make_conn(fetchall=[])
        with patch('src.database.get_connection', return_value=conn2):
            database.obtener_boletos_para_sorteo()
        sql_sin_marca = sql_ejecutado(cursor2).upper()

        # Assert
        assert 'RAND()' not in sql_con_marca
        assert 'RAND()' not in sql_sin_marca

    def test_retorna_lo_que_devuelve_fetchall(self):
        # Arrange
        filas = [
            {'id': 10, 'numero_boleto': 'B-010', 'marca': 'LG'},
            {'id': 11, 'numero_boleto': 'B-011', 'marca': 'LG'},
        ]
        conn, cursor = make_conn(fetchall=filas)

        # Act
        with patch('src.database.get_connection', return_value=conn):
            resultado = database.obtener_boletos_para_sorteo(marca='LG')

        # Assert
        assert resultado == filas

    def test_retorna_lista_vacia_cuando_no_hay_boletos(self):
        # Arrange (caso limite: sin resultados)
        conn, cursor = make_conn(fetchall=[])

        # Act
        with patch('src.database.get_connection', return_value=conn):
            resultado = database.obtener_boletos_para_sorteo(marca='LG')

        # Assert
        assert resultado == []

    def test_cierra_la_conexion(self):
        # Arrange
        conn, cursor = make_conn(fetchall=[])

        # Act
        with patch('src.database.get_connection', return_value=conn):
            database.obtener_boletos_para_sorteo(marca='LG')

        # Assert
        conn.close.assert_called_once()


# ===========================================================================
# 2) obtener_estadisticas()
# ===========================================================================

class TestObtenerEstadisticas:
    """obtener_estadisticas hace varias consultas COUNT/SUM y devuelve un dict
    con las claves agregadas. Mockeamos fetchone con side_effect en el orden
    en que la funcion las consume."""

    def _side_effect_completo(self, participantes=5, facturas=12, boletos=40,
                              ganadores=2, monto=1500.5, elegibles=8):
        """Devuelve la lista de valores que fetchone retornara en orden:
        1) total_participantes  -> {'total': ...}
        2) total_facturas       -> {'total': ...}
        3) total_boletos        -> {'total': ...}
        4) total_ganadores      -> {'total': ...}
        5) monto_total (SUM)    -> {'total': ...}
        6) total_participantes_elegibles -> {'total': ...}
        """
        return [
            {'total': participantes},
            {'total': facturas},
            {'total': boletos},
            {'total': ganadores},
            {'total': monto},
            {'total': elegibles},
        ]

    def test_dict_incluye_todas_las_claves(self):
        # Arrange
        conn, cursor = make_conn(
            fetchone_side_effect=self._side_effect_completo()
        )

        # Act
        with patch('src.database.get_connection', return_value=conn):
            stats = database.obtener_estadisticas()

        # Assert: todas las claves esperadas, incluida la nueva
        claves_esperadas = {
            'total_participantes',
            'total_facturas',
            'total_boletos',
            'total_ganadores',
            'monto_total',
            'total_participantes_elegibles',
        }
        assert claves_esperadas.issubset(set(stats.keys()))

    def test_incluye_clave_nueva_total_participantes_elegibles(self):
        # Arrange
        conn, cursor = make_conn(
            fetchone_side_effect=self._side_effect_completo(elegibles=8)
        )

        # Act
        with patch('src.database.get_connection', return_value=conn):
            stats = database.obtener_estadisticas()

        # Assert (no-regresion: la clave nueva existe y trae el valor correcto)
        assert 'total_participantes_elegibles' in stats
        assert stats['total_participantes_elegibles'] == 8

    def test_valores_mapeados_en_orden_correcto(self):
        # Arrange: valores distintos para detectar mapeos cruzados
        conn, cursor = make_conn(
            fetchone_side_effect=self._side_effect_completo(
                participantes=5, facturas=12, boletos=40,
                ganadores=2, monto=1500.5, elegibles=8,
            )
        )

        # Act
        with patch('src.database.get_connection', return_value=conn):
            stats = database.obtener_estadisticas()

        # Assert
        assert stats['total_participantes'] == 5
        assert stats['total_facturas'] == 12
        assert stats['total_boletos'] == 40
        assert stats['total_ganadores'] == 2
        assert stats['monto_total'] == 1500.5
        assert stats['total_participantes_elegibles'] == 8

    def test_monto_total_es_float(self):
        # Arrange: la BD podria devolver un Decimal/entero; la funcion lo castea
        conn, cursor = make_conn(
            fetchone_side_effect=self._side_effect_completo(monto=999)
        )

        # Act
        with patch('src.database.get_connection', return_value=conn):
            stats = database.obtener_estadisticas()

        # Assert
        assert isinstance(stats['monto_total'], float)
        assert stats['monto_total'] == 999.0

    def test_monto_total_none_se_convierte_en_cero(self):
        # Arrange (caso limite: SUM sobre tabla vacia devuelve NULL/None)
        conn, cursor = make_conn(
            fetchone_side_effect=self._side_effect_completo(monto=None)
        )

        # Act
        with patch('src.database.get_connection', return_value=conn):
            stats = database.obtener_estadisticas()

        # Assert: `row['total'] or 0` evita el None
        assert stats['monto_total'] == 0.0
        assert isinstance(stats['monto_total'], float)

    def test_consulta_elegibles_filtra_por_marcas(self):
        # Arrange
        side_effect = self._side_effect_completo()
        conn, cursor = make_conn(fetchone_side_effect=side_effect)

        # Act
        with patch('src.database.get_connection', return_value=conn):
            database.obtener_estadisticas()

        # Assert: la ultima consulta (elegibles) usa IN(...) y tuple(MARCAS)
        sql_ultima = normalizar_sql(sql_ejecutado(cursor, call_index=-1))
        assert 'f.marca IN (' in sql_ultima
        assert params_ejecutados(cursor, call_index=-1) == tuple(MARCAS)

    def test_cierra_la_conexion(self):
        # Arrange
        conn, cursor = make_conn(
            fetchone_side_effect=self._side_effect_completo()
        )

        # Act
        with patch('src.database.get_connection', return_value=conn):
            database.obtener_estadisticas()

        # Assert
        conn.close.assert_called_once()


# ===========================================================================
# 3) obtener_ganador_pendiente_por_premio(premio_id)
# ===========================================================================

class TestObtenerGanadorPendientePorPremio:

    def test_select_incluye_campos_y_join_facturas(self):
        # Arrange
        ganador = {'id': 1, 'numero_factura': 'F-100', 'marca': 'LG'}
        conn, cursor = make_conn(fetchone=ganador)

        # Act
        with patch('src.database.get_connection', return_value=conn):
            database.obtener_ganador_pendiente_por_premio(3)

        # Assert
        sql = normalizar_sql(sql_ejecutado(cursor))
        assert 'numero_factura' in sql
        assert 'f.marca' in sql
        assert f'JOIN {database.TABLE_FACTURAS}' in sql

    def test_pasa_premio_id_como_parametro(self):
        # Arrange
        conn, cursor = make_conn(fetchone=None)

        # Act
        with patch('src.database.get_connection', return_value=conn):
            database.obtener_ganador_pendiente_por_premio(7)

        # Assert
        assert params_ejecutados(cursor) == (7,)

    def test_retorna_fetchone(self):
        # Arrange
        ganador = {'id': 42, 'participante_id': 9, 'numero_factura': 'F-1'}
        conn, cursor = make_conn(fetchone=ganador)

        # Act
        with patch('src.database.get_connection', return_value=conn):
            resultado = database.obtener_ganador_pendiente_por_premio(1)

        # Assert
        assert resultado == ganador

    def test_retorna_none_cuando_no_hay_ganador_pendiente(self):
        # Arrange (caso limite: premio sin ganador pendiente)
        conn, cursor = make_conn(fetchone=None)

        # Act
        with patch('src.database.get_connection', return_value=conn):
            resultado = database.obtener_ganador_pendiente_por_premio(99)

        # Assert
        assert resultado is None

    def test_filtra_por_confirmado_cero_y_premio_libre(self):
        # Arrange (no-regresion: solo ganadores pendientes de premios sin asignar)
        conn, cursor = make_conn(fetchone=None)

        # Act
        with patch('src.database.get_connection', return_value=conn):
            database.obtener_ganador_pendiente_por_premio(2)

        # Assert
        sql = normalizar_sql(sql_ejecutado(cursor))
        assert 'g.confirmado = 0' in sql
        assert 'pr.ganador_id IS NULL' in sql

    def test_cierra_la_conexion(self):
        # Arrange
        conn, cursor = make_conn(fetchone=None)

        # Act
        with patch('src.database.get_connection', return_value=conn):
            database.obtener_ganador_pendiente_por_premio(1)

        # Assert
        conn.close.assert_called_once()


# ===========================================================================
# 4) obtener_participantes_con_ganador_pendiente()
# ===========================================================================

class TestObtenerParticipantesConGanadorPendiente:

    def test_retorna_lista_de_participante_id(self):
        # Arrange
        filas = [{'participante_id': 1}, {'participante_id': 2}]
        conn, cursor = make_conn(fetchall=filas)

        # Act
        with patch('src.database.get_connection', return_value=conn):
            resultado = database.obtener_participantes_con_ganador_pendiente()

        # Assert
        assert resultado == [1, 2]

    def test_retorna_lista_vacia_cuando_no_hay_filas(self):
        # Arrange (caso limite)
        conn, cursor = make_conn(fetchall=[])

        # Act
        with patch('src.database.get_connection', return_value=conn):
            resultado = database.obtener_participantes_con_ganador_pendiente()

        # Assert
        assert resultado == []

    def test_extrae_solo_la_columna_participante_id(self):
        # Arrange: filas con columnas extra, debe extraer solo participante_id
        filas = [
            {'participante_id': 5, 'otro': 'x'},
            {'participante_id': 8, 'otro': 'y'},
            {'participante_id': 13, 'otro': 'z'},
        ]
        conn, cursor = make_conn(fetchall=filas)

        # Act
        with patch('src.database.get_connection', return_value=conn):
            resultado = database.obtener_participantes_con_ganador_pendiente()

        # Assert
        assert resultado == [5, 8, 13]

    def test_usa_distinct_y_filtros_pendiente(self):
        # Arrange
        conn, cursor = make_conn(fetchall=[])

        # Act
        with patch('src.database.get_connection', return_value=conn):
            database.obtener_participantes_con_ganador_pendiente()

        # Assert
        sql = normalizar_sql(sql_ejecutado(cursor))
        assert 'DISTINCT g.participante_id' in sql
        assert 'g.confirmado = 0' in sql
        assert 'pr.ganador_id IS NULL' in sql

    def test_cierra_la_conexion(self):
        # Arrange
        conn, cursor = make_conn(fetchall=[])

        # Act
        with patch('src.database.get_connection', return_value=conn):
            database.obtener_participantes_con_ganador_pendiente()

        # Assert
        conn.close.assert_called_once()


# ===========================================================================
# 5) registrar_ganador_pendiente(participante_id, premio_id, sorteo_id, boleto_id)
# ===========================================================================

class TestRegistrarGanadorPendiente:

    def test_hace_insert_con_confirmado_cero(self):
        # Arrange
        conn, cursor = make_conn(lastrowid=55)

        # Act
        with patch('src.database.get_connection', return_value=conn):
            database.registrar_ganador_pendiente(1, 2, 3, 4)

        # Assert: es un INSERT en la tabla de ganadores con confirmado = 0
        sql = normalizar_sql(sql_ejecutado(cursor))
        assert sql.upper().startswith('INSERT INTO')
        assert database.TABLE_GANADORES in sql
        assert 'confirmado' in sql
        # El valor literal 0 de confirmado va embebido en el VALUES (...)
        assert re.search(r',\s*0\s*\)', sql) is not None

    def test_pasa_los_ids_como_parametros(self):
        # Arrange
        conn, cursor = make_conn(lastrowid=1)

        # Act
        with patch('src.database.get_connection', return_value=conn):
            database.registrar_ganador_pendiente(11, 22, 33, 44)

        # Assert: los 4 primeros params son los ids en orden
        params = params_ejecutados(cursor)
        assert params[0] == 11  # participante_id
        assert params[1] == 22  # premio_id
        assert params[2] == 33  # sorteo_id
        assert params[3] == 44  # boleto_id
        # el ultimo parametro es la fecha (datetime)
        assert len(params) == 5

    def test_llama_commit(self):
        # Arrange
        conn, cursor = make_conn(lastrowid=1)

        # Act
        with patch('src.database.get_connection', return_value=conn):
            database.registrar_ganador_pendiente(1, 2, 3, 4)

        # Assert
        conn.commit.assert_called_once()

    def test_retorna_lastrowid(self):
        # Arrange
        conn, cursor = make_conn(lastrowid=777)

        # Act
        with patch('src.database.get_connection', return_value=conn):
            resultado = database.registrar_ganador_pendiente(1, 2, 3, 4)

        # Assert
        assert resultado == 777

    def test_cierra_la_conexion(self):
        # Arrange
        conn, cursor = make_conn(lastrowid=1)

        # Act
        with patch('src.database.get_connection', return_value=conn):
            database.registrar_ganador_pendiente(1, 2, 3, 4)

        # Assert
        conn.close.assert_called_once()

    def test_cierra_la_conexion_aunque_falle_el_insert(self):
        """El close() esta en un finally: debe ejecutarse aun si execute lanza
        una excepcion (caso de error)."""
        # Arrange
        conn, cursor = make_conn()
        cursor.execute.side_effect = Exception('fallo de insert')

        # Act / Assert: la excepcion se propaga (no se silencia)
        with patch('src.database.get_connection', return_value=conn):
            with pytest.raises(Exception, match='fallo de insert'):
                database.registrar_ganador_pendiente(1, 2, 3, 4)

        # Assert: aun asi se cerro la conexion via finally
        conn.close.assert_called_once()
        # y NO se hizo commit porque execute fallo antes
        conn.commit.assert_not_called()
