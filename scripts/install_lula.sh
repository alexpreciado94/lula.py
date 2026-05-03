#!/bin/bash

# ==========================================
# 🏴‍☠️ LULA INSTALLER - Orange Pi 5 Max
# ==========================================
# Ubicación: lula_project/scripts/install_lula.sh

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 1. VERIFICAR SUPERUSUARIO
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}❌ Error: Este script necesita permisos de administrador.${NC}"
  echo -e "Ejecuta: sudo ./install_lula.sh"
  exit 1
fi

# 2. DETECTAR USUARIO REAL Y RUTAS
REAL_USER=${SUDO_USER:-$USER}
REAL_GROUP=$(id -gn $REAL_USER)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# La raíz es un nivel arriba de /scripts
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${GREEN}🚀 Iniciando despliegue para el usuario: ${YELLOW}$REAL_USER${NC}"
echo -e "${YELLOW}📂 Raíz del proyecto detectada: $PROJECT_DIR${NC}"

# 3. ACTUALIZACIÓN DEL SISTEMA
echo -e "${YELLOW}📦 Actualizando sistema y herramientas base...${NC}"
apt-get update && apt-get upgrade -y
apt-get install -y curl wget git htop build-essential python3-pip

# 4. DOCKER & PORTAINER
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}🐳 Instalando Docker...${NC}"
    curl -fsSL https://get.docker.com | sh
    usermod -aG docker $REAL_USER
    echo -e "${GREEN}✅ Docker instalado.${NC}"
else
    echo -e "${GREEN}✅ Docker ya estaba instalado.${NC}"
fi

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

# 5. CONFIGURACIÓN NPU (RK3588)
echo -e "${YELLOW}🧠 Configurando permisos de NPU (IA)...${NC}"
echo 'SUBSYSTEM=="misc", KERNEL=="rknpu", MODE="0666"' > /etc/udev/rules.d/99-rknpu.rules
udevadm control --reload-rules && udevadm trigger

if [ -e /dev/rknpu ]; then
    echo -e "${GREEN}✅ Chip NPU detectado.${NC}"
else
    echo -e "${RED}⚠️ ALERTA: No se detecta /dev/rknpu. ¿Es una Orange Pi 5?${NC}"
fi

# 6. ESTRUCTURA DE DIRECTORIOS
echo -e "${YELLOW}🔨 Creando estructura de carpetas...${NC}"
mkdir -p "$PROJECT_DIR/libs"
mkdir -p "$PROJECT_DIR/data/monero_db"
mkdir -p "$PROJECT_DIR/logs"
mkdir -p "$PROJECT_DIR/src"
mkdir -p "$PROJECT_DIR/docker"

# 7. DESCARGAR DRIVER NPU
DRIVER_FILE="rknn_toolkit_lite2-2.3.0-cp39-cp39-linux_aarch64.whl"
TARGET_PATH="$PROJECT_DIR/libs/$DRIVER_FILE"
URL="https://github.com/rockchip-linux/rknn-toolkit2/raw/master/rknn_toolkit_lite2/packages/$DRIVER_FILE"

if [ ! -f "$TARGET_PATH" ]; then
    echo -e "${YELLOW}⬇️ Descargando driver RKNN Lite...${NC}"
    wget -q --show-progress -O "$TARGET_PATH" "$URL"
else
    echo -e "${GREEN}✅ Driver NPU ya existe en libs/.${NC}"
fi

# 8. FIX DE PERMISOS (Vital para poder editar archivos luego)
echo -e "${YELLOW}🔑 Asignando propiedad de archivos a $REAL_USER...${NC}"
chown -R $REAL_USER:$REAL_GROUP "$PROJECT_DIR"

echo -e ""
echo -e "${GREEN}🎉 INSTALACIÓN COMPLETADA 🎉${NC}"
echo -e "---------------------------------------------------"
echo -e "1. Reinicia para aplicar permisos: ${YELLOW}sudo reboot${NC}"
echo -e "2. Sube tus archivos (src/, .env, pandas_ta.zip) por SFTP."
echo -e "3. Arranca: ${YELLOW}cd $PROJECT_DIR/docker && docker compose up -d --build${NC}"
echo -e "---------------------------------------------------"