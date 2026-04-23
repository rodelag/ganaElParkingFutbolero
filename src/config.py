import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-me')
ADMIN_PASSWORD_HASH = os.getenv('ADMIN_PASSWORD_HASH')
DATABASE_PATH = os.getenv('DATABASE_PATH', os.path.join(DATA_DIR, 'parking_futbolero.db'))
FLASK_PORT = int(os.getenv('FLASK_PORT', '8080'))

# MySQL Rodelag
DB_HOST = os.getenv('DB_HOST', 'reportes.rodelag.com')
DB_PORT = int(os.getenv('DB_PORT', '3306'))
DB_USER = os.getenv('DB_USER', 'rodelag_it')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_NAME = os.getenv('DB_NAME', 'enx_rodelag')
DB_NAME_DEV = os.getenv('DB_NAME_DEV', 'rodelag_desarrollo_interno')
TABLE_PREFIX = 'parkingfutbolero2026_'

# Marcas participantes
MARCAS = ['LG', 'Sankey', 'Mystic', 'RCA', 'Hisense', 'Samsung']

# Monto mínimo para boleto
MONTO_BOLETO = 100.00

# Beneficio Crédito de Una multiplicador
MULTIPLICADOR_CREDITO_UNA = 2

# Restricciones
EDAD_MINIMA = 18

# Fechas de la promocion
FECHA_INICIO = '2026-04-30'
FECHA_FIN = '2026-06-30'

# Premios y fechas de fiestas
PREMIOS = [
    {'id': 1, 'marca': 'LG', 'tv': 'TV LG de 100"', 'valor': 5999.99, 'partido': 'Brasil vs Marruecos', 'fecha_fiesta': '2026-06-13', 'sorteo': 1},
    {'id': 2, 'marca': 'Hisense', 'tv': 'TV Hisense de 65"', 'valor': 619.99, 'partido': 'Panama vs Ghana', 'fecha_fiesta': '2026-06-17', 'sorteo': 1},
    {'id': 3, 'marca': 'Sankey', 'tv': 'TV Sankey 70"', 'valor': 419.99, 'partido': 'Panama vs Croacia', 'fecha_fiesta': '2026-06-23', 'sorteo': 1},
    {'id': 4, 'marca': 'Mystic', 'tv': 'TV Mystic 70"', 'valor': 539.99, 'partido': 'Panama vs Inglaterra', 'fecha_fiesta': '2026-06-27', 'sorteo': 1},
    {'id': 5, 'marca': 'Samsung', 'tv': 'TV Samsung de 85"', 'valor': 2299.00, 'partido': 'Semifinal', 'fecha_fiesta': '2026-07-18', 'sorteo': 2},
    {'id': 6, 'marca': 'RCA', 'tv': 'TV RCA de 70"', 'valor': 499.99, 'partido': 'La Final', 'fecha_fiesta': '2026-07-19', 'sorteo': 2},
]

# Fechas de sorteos
SORTEOS = {
    1: {'nombre': 'Sorteo 1', 'fecha': '2026-06-02', 'premios': [1, 2, 3, 4], 'ganadores_a_escoger': 4},
    2: {'nombre': 'Sorteo 2', 'fecha': '2026-07-03', 'premios': [5, 6], 'ganadores_a_escoger': 5},
}
