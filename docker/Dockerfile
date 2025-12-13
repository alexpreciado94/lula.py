FROM python:3.9-slim

# Instalamos git y gcc (Git sigue siendo útil para otras cosas internas)
RUN apt-get update && apt-get install -y \
    gcc \
    libhdf5-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1. Copiamos configuraciones
COPY pyproject.toml README.md LICENSE ./

# 2. Copiamos la carpeta de librerías locales
COPY libs/ libs/

# --- INSTALACIÓN MANUAL DE LIBRERÍAS LOCALES ---
# Primero instalamos pandas_ta desde el archivo local (Offline)
RUN pip install libs/pandas_ta.zip

# Luego el driver NPU
RUN pip install libs/rknn_toolkit_lite2-2.3.0-cp39-cp39-linux_aarch64.whl

# Finalmente, el resto de dependencias del proyecto (ccxt, pandas, etc.)
RUN pip install --no-cache-dir .

# 3. Copiamos el código fuente
COPY src/ src/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

CMD ["python", "src/main.py"]