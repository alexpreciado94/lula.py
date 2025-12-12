FROM python:3.9-slim

# Instalamos dependencias del sistema para compilar y seguridad
RUN apt-get update && apt-get install -y \
    gcc libhdf5-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1. Instalar librerías
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. Instalar Driver NPU (Rockchip)
COPY libs/ libs/
RUN pip install libs/rknn_toolkit_lite2-2.3.0-cp39-cp39-linux_aarch64.whl

# 3. Copiar Código Fuente
COPY src/ src/

# Variables de entorno para que Python no guarde caché
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

CMD ["python", "src/main.py"]