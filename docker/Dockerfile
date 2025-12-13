# ==========================================
# ETAPA 1: BUILDER (El Constructor)
# ==========================================
# Usamos una imagen base estable de Debian Bookworm
FROM python:3.9-slim-bookworm as builder

# Evitamos archivos basura de Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 1. Instalar herramientas de compilación (Solo necesarias para instalar, no para ejecutar)
# 'git' es necesario para pandas_ta
# 'build-essential' y 'gcc' para compilar librerías de C
# 'libhdf5-dev' para dependencias matemáticas complejas
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    libhdf5-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# 2. Crear un entorno virtual (Best Practice PEP 668)
# Instalamos todo aquí para luego copiar solo esta carpeta
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 3. Preparar contexto de dependencias
WORKDIR /build

# Copiamos primero los archivos de configuración para aprovechar la caché de Docker
# Si no cambias pyproject.toml, Docker se salta este paso en el futuro (build instantáneo)
COPY pyproject.toml README.md LICENSE ./
COPY libs/ libs/

# 4. Instalación de Dependencias
# Actualizamos pip
RUN pip install --upgrade pip

# A) Instalamos las dependencias del pyproject.toml
# El '.' instala las dependencias definidas en [project.dependencies]
RUN pip install --no-cache-dir .

# B) Instalamos el driver de la NPU (wheel local)
# Usamos find para localizar el archivo sin importar si cambia ligeramente el nombre
RUN pip install --no-cache-dir $(find libs -name "rknn_toolkit_lite2*.whl")

# ==========================================
# ETAPA 2: RUNNER (La Imagen Final)
# ==========================================
FROM python:3.9-slim-bookworm

# Variables de entorno de producción
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# 1. Instalar solo librerías de sistema runtime (necesarias para ejecutar, no compilar)
# libhdf5-serial-dev suele ser necesario para que numpy/pandas funcionen en ARM
RUN apt-get update && apt-get install -y --no-install-recommends \
    libhdf5-serial-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. COPIAR EL CEREBRO DESDE LA ETAPA BUILDER
# Aquí ocurre la magia: Copiamos solo el entorno virtual ya preparado.
COPY --from=builder /opt/venv /opt/venv

# 3. Copiar el código fuente (Esto cambia frecuentemente, por eso va al final)
COPY src/ src/

# 4. Chequeo de Salud (Opcional pero pro)
# Verifica que el proceso python esté corriendo
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD pgrep python || exit 1

# 5. Ejecución
# Usamos exec para que python reciba las señales de parada (SIGTERM) correctamente
CMD ["python", "src/main.py"]