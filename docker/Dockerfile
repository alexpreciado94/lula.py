FROM python:3.9-slim-bookworm

# 1. Herramientas de compilación
RUN apt-get update && apt-get install -y \
    gcc g++ cmake make git libhdf5-dev libprotobuf-dev protobuf-compiler \
    libgl1-mesa-glx libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2. Archivos base
COPY pyproject.toml README.md LICENSE ./
COPY libs/ libs/

# 3. Instalación manual
RUN pip install --no-cache-dir "numpy<1.24.0" pandas
RUN pip install --no-cache-dir libs/rknn_toolkit2-2.3.2-cp39-cp39-manylinux_2_17_aarch64.manylinux2014_aarch64.whl

# 4. Instalamos el proyecto (sin volver a mirar dependencias conflictivas)
RUN pip install --no-cache-dir --no-deps .

# 5. Resto de dependencias estándar que SI necesitamos de internet
# (CCXT, Dotenv, Joblib suelen venir en el pyproject, pero por si acaso las aseguramos)
RUN pip install --no-cache-dir tensorflow==2.12.0 h5py==3.8.0 onnx==1.14.0 tf2onnx==1.14.0 scikit-learn==1.6.1 ccxt python-dotenv joblib yfinance
RUN pip install --no-cache-dir --upgrade yfinance

COPY src/ src/

ENV PYTHONPATH="/app:/app/libs"
ENV PYTHONUNBUFFERED=1

CMD ["python", "src/main.py"]
