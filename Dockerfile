# Dockerfile para Parking Futbolero - Rodelag
FROM python:3.11-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    build-essential \
    pkg-config \
    curl \
    locales \
    && locale-gen es_PA.UTF-8 \
    && rm -rf /var/lib/apt/lists/*

ENV LANG=es_PA.UTF-8
ENV LANGUAGE=es_PA:es
ENV LC_ALL=es_PA.UTF-8
ENV PYTHONIOENCODING=utf-8

# Crear directorio de trabajo
WORKDIR /app

# Copiar requirements primero para aprovechar cache de Docker
COPY requirements.txt .

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del proyecto
COPY . .

# Crear directorio para datos
RUN mkdir -p /app/data

# Exponer puerto
EXPOSE 8080

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/ || exit 1

# Comando por defecto
CMD ["python3", "app.py"]
