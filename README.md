# lula.py 💶

### Artificial Intelligence for CryptoTrading - Expert of Monero
**Made with LOVE for Orange Pi 5 Max. [Python 3.9]** 🐼

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Platform](https://img.shields.io/badge/Hardware-Orange_Pi_5_Max_(RK3588)-orange)](http://www.orangepi.org/)
[![Status](https://img.shields.io/badge/Mode-CypherPunk-black)](https://getmonero.org/)

> *(Blessed by Sor. Concha)* #CypherPunk

---

## 🏗️ Arquitectura del Sistema
Lula utiliza una **Arquitectura Híbrida** para garantizar soberanía y rendimiento:

1.  **El Cerebro (PC / Kali Linux):** Entrenamos la IA en un ordenador potente usando TensorFlow. Generamos un "cerebro congelado" (`.rknn`).
2.  **El Cuerpo (Orange Pi 5 Max):** Ejecutamos el cerebro usando el chip NPU (IA dedicada) de bajo consumo, aislado en Docker.
3.  **La Misión (Lullaby):** Especular con criptos volátiles (BTC, SOL) para acumular **Monero (XMR)** gratis.

---

## 🛠️ FASE 1: Preparación de la Orange Pi (El Servidor)

Estos pasos configuran el sistema operativo, Docker, los drivers de la NPU y la estructura de carpetas.

1.  **Conéctate por SSH:**
    ```bash
    ssh root@<IP_DE_TU_ORANGE_PI>
    ```

2.  **Ejecuta el Instalador Maestro:**
    ```bash
    # Asumiendo que has copiado la carpeta lula_project a tu home
    cd lula_project/scripts/
    chmod +x install_lula.sh
    sudo ./install_lula.sh
    ```

3.  **Verifica la Instalación:**
    Al finalizar, reinicia la placa (`sudo reboot`). Al volver, deberías tener la carpeta `lula_project` con las subcarpetas `libs`, `data`, `src` y `docker` listas.

    > **Nota:** Usa **FileZilla** o `scp` para subir tus archivos de código fuente (`src/`) y tu archivo de secretos (`.env`) a la Orange Pi ahora.

---

## 🔌 FASE 2: Test de Conexión (Sanity Check)

Antes de levantar el sistema complejo, verificamos que la Orange Pi tiene salida a internet y que tus API Keys de Kraken funcionan.

1.  **Instala dependencias temporales (solo para el test):**
    ```bash
    pip install ccxt python-dotenv
    ```

2.  **Ejecuta el test:**
    ```bash
    cd lula_project/scripts/
    python3 connection_test.py
    ```
    *Si ves mensajes en VERDE ✅, puedes proceder.*

---

## 🧠 FASE 3: El Entrenamiento (En tu PC / Kali Linux)

**⚠️ IMPORTANTE:** Esto NO se hace en la Orange Pi. Se hace en tu ordenador.

### 1. Preparar Entorno en Kali Linux
```bash
# Instalar librerías de sistema necesarias para compilar
sudo apt install -y python3-dev python3-pip python3-venv libxslt1-dev zlib1g-dev libgl1-mesa-glx

# Crear y activar entorno virtual
cd lula_project/scripts/trainer
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias de Python
pip install -r trainer_requirements.txt