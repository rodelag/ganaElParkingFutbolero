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
  - Gestión de facturas
  - Sorteos electrónicos
  - Exportación a CSV
  - Control de ganadores

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
│   ├── config.py          # Configuración
│   └── database.py        # Base de datos SQLite
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
├── data/                   # Base de datos SQLite
├── logs/                   # Logs del sistema
├── requirements.txt
├── .env
└── .env.example
```

## Tecnologías

- Python 3.10+
- Flask
- SQLite
- Tailwind CSS (CDN)
- Vanilla JavaScript

## Licencia

© 2026 Rodelag, S.A. Todos los derechos reservados.
