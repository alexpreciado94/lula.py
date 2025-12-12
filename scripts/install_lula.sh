#!/bin/bash

# ==========================================
# LULA - INSTALADOR MAESTRO (Orange Pi 5 Max)
# ==========================================
# Ubicación recomendada: lula_project/scripts/install_lula.sh

# --- COLORES PARA LOGS ---
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# --- 1. VERIFICACIONES INICIALES ---

# Comprobar si es ROOT
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}❌ Error: Debes ejecutar este script como root.${NC}"
  echo -e "Uso: sudo ./install_lula.sh"
  exit 1
fi

# Detectar usuario real (el que invocó sudo)
REAL_USER=${SUDO_USER:-$USER}
echo -e "${GREEN}🚀 Iniciando configuración de Lula para: $REAL_USER${NC}"

# Detectar directorios dinámicamente
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")" # Subir un nivel (raíz del proyecto)

echo -e "${YELLOW}📂 Raíz del proyecto detectada en: $PROJECT_DIR${NC}"

# --- 2. ACTUALIZACIÓN DEL SISTEMA ---
echo -e "${YELLOW}📦 Actualizando repositorios y herramientas base...${NC}"
apt-get update && apt-get upgrade -y
apt-get install -y curl wget git htop build-essential

# --- 3. INSTALACIÓN DE DOCKER & DOCKER COMPOSE ---
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}🐳 Instalando Docker...${NC}"
    curl -fsSL https://get.docker.com | sh
    
    # Añadir usuario al grupo docker
    usermod -aG docker $REAL_USER
    echo -e "${GREEN}✅ Docker instalado.${NC}"
else
    echo -e "${GREEN}✅ Docker ya estaba instalado.${NC}"
fi

# --- 4. DESPLIEGUE DE PORTAINER (Panel de Control) ---
if [ ! "$(docker ps -a -q -f name=portainer)" ]; then
    echo -e "${YELLOW}🚢 Desplegando Portainer (Puerto 9000)...${NC}"
    docker run -d -p 9000:9000 --name portainer \
    --restart=always \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v portainer_data:/data \
    portainer/portainer-ce:latest
else
    echo -e "${GREEN}✅ Portainer ya está corriendo.${NC}"
fi

# --- 5. HABILITAR NPU (Chip IA RK3588) ---
echo -e "${YELLOW}🧠 Configurando permisos de la NPU...${NC}"
# Regla UDEV para acceso sin restricciones al chip de IA
echo 'SUBSYSTEM=="misc", KERNEL=="rknpu", MODE="0666"' > /etc/udev/rules.d/99-rknpu.rules
udevadm control --reload-rules && udevadm trigger

if [ -e /dev/rknpu ]; then
    echo -e "${GREEN}✅ Hardware NPU detectado y configurado.${NC}"
else
    echo -e "${RED}⚠️ ADVERTENCIA: No se detecta /dev/rknpu. ¿Es una Orange Pi 5?${NC}"
fi

# --- 6. PREPARAR ESTRUCTURA DE CARPETAS ---
echo -e "${YELLOW}🔨 Verificando estructura de directorios...${NC}"

# Crear carpetas necesarias
mkdir -p "$PROJECT_DIR/libs"
mkdir -p "$PROJECT_DIR/data/monero_db"
mkdir -p "$PROJECT_DIR/logs"
mkdir -p "$PROJECT_DIR/src"
mkdir -p "$PROJECT_DIR/docker"

# --- 7. DESCARGAR DRIVER NPU (RKNN Lite) ---
DRIVER_NAME="rknn_toolkit_lite2-2.3.0-cp39-cp39-linux_aarch64.whl"
TARGET_FILE="$PROJECT_DIR/libs/$DRIVER_NAME"
RKNN_URL="https://github.com/rockchip-linux/rknn-toolkit2/raw/master/rknn_toolkit_lite2/packages/$DRIVER_NAME"

if [ ! -f "$TARGET_FILE" ]; then
    echo -e "${YELLOW}⬇️ Descargando driver NPU ($DRIVER_NAME)...${NC}"
    wget -q --show-progress -O "$TARGET_FILE" "$RKNN_URL"
    
    if [ -f "$TARGET_FILE" ]; then
        echo -e "${GREEN}✅ Driver descargado en libs/.${NC}"
    else
        echo -e "${RED}❌ Error descargando driver. Revisa tu conexión.${NC}"
    fi
else
    echo -e "${GREEN}✅ El driver NPU ya existe.${NC}"
fi

# --- 8. PERMISOS FINALES ---
echo -e "${YELLOW}🔑 Ajustando propietario de archivos a $REAL_USER...${NC}"
chown -R $REAL_USER:$REAL_USER "$PROJECT_DIR"

# --- FIN ---
echo -e ""
echo -e "${GREEN}🎉 INSTALACIÓN DE LULA COMPLETADA 🎉${NC}"
echo -e "------------------------------------------------------------"
echo -e "🔹 1. Reinicia para aplicar permisos de Docker:"
echo -e "      ${YELLOW}sudo reboot${NC}"
echo -e "🔹 2. Al volver, inicia a Lula:"
echo -e "      ${YELLOW}cd $PROJECT_DIR/docker && docker compose up -d --build${NC}"
echo -e "------------------------------------------------------------"