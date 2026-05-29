# Gana el Parkin Futbolero - Rodelag

Aplicación web para la promoción comercial "Gana el Parkin Futbolero" de Rodelag, S.A.

## Descripción

Promoción válida del 30 de abril al 30 de junio de 2026. Los clientes acumulan boletos electrónicos por compras de las marcas LG, Sankey, Mystic, RCA, Hisense y Samsung.

## Características

- **Registro de facturas** para clientes
- **Cálculo automático** de boletos electrónicos
- **Beneficio Crédito de Una** (doble boletos)
- **Consulta de boletos** por cédula
- **Dashboard administrativo** con:
  - Estadísticas en tiempo real
  - **Indicadores de elegibilidad**: total de facturas y de clientes con compras
    de marcas participantes que alcanzan el mínimo de B/.100 dentro del período
    (consultados en la base de datos de producción de Rodelag, con manejo seguro
    de errores que muestra `—` si la consulta no está disponible)
  - **Cifras formateadas con separador de miles** (filtro `miles` de Jinja2)
  - Gestión de facturas
  - Sorteos electrónicos **filtrados por marca del premio** (el ganador se
    selecciona aleatoriamente entre los boletos elegibles de esa marca; si el
    premio no define marca, participan todas las marcas)
  - Exportación a CSV
  - Control de ganadores
- **Soporte UTF-8** de extremo a extremo (acentos y caracteres en español):
  conexiones MySQL en `utf8mb4`, respuestas HTML con `charset=utf-8` y locale
  `es_PA.UTF-8` en el contenedor Docker

## Instalación

```bash
# Crear entorno virtual
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con las credenciales correspondientes

# Ejecutar
python app.py
```

## Credenciales Admin

Para generar el hash de la contraseña de administrador:

```python
from werkzeug.security import generate_password_hash
print(generate_password_hash('tu_password'))
```

Copiar el resultado en la variable `ADMIN_PASSWORD_HASH` del archivo `.env`.

## Estructura del Proyecto

```
.
├── app.py                  # Aplicación Flask principal
├── src/
│   ├── config.py          # Configuración (variables de entorno)
│   ├── database.py        # Acceso a la BD de la promoción (MySQL desarrollo)
│   ├── mysql_db.py        # Conexiones MySQL y validaciones contra producción Rodelag
│   ├── email_service.py   # Envío de correos de confirmación
│   └── init_mysql_tables.py # Creación inicial de tablas
├── templates/              # Templates HTML (Jinja2)
│   ├── base.html
│   ├── index.html
│   ├── bases.html
│   ├── admin_login.html
│   ├── admin_dashboard.html
│   ├── admin_facturas.html
│   ├── admin_ganadores.html
│   └── admin_sorteo.html
├── static/
│   ├── css/style.css
│   └── js/app.js
├── tests/                  # Pruebas unitarias (pytest)
├── data/                   # Datos locales
├── requirements.txt        # Dependencias de producción
├── requirements-dev.txt    # Dependencias de desarrollo/pruebas
├── pytest.ini              # Configuración de pytest
├── Dockerfile
├── .env
└── .env.example
```

## Pruebas

El proyecto incluye una suite de pruebas unitarias con **pytest** en el directorio
`tests/`. Para ejecutarlas:

```bash
# Instalar las dependencias de desarrollo (solo la primera vez)
.venv/bin/python -m pip install -r requirements-dev.txt

# Ejecutar toda la suite
.venv/bin/python -m pytest
```

La configuración de pytest está en `pytest.ini` (descubre los tests en `tests/`
con el patrón `test_*.py`). Las pruebas cubren la lógica de `app.py`,
`src/database.py` y `src/mysql_db.py`.

## Tecnologías

- Python 3.10+
- Flask
- MySQL (PyMySQL)
- Tailwind CSS (CDN)
- Vanilla JavaScript
- pytest (pruebas)

## Licencia

© 2026 Rodelag, S.A. Todos los derechos reservados.
