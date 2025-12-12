# lula.py 💶

### Artificial Intelligence for CryptoTrading - Expert of Monero
**Made with LOVE for Orange Pi 5 Max. [Python 3.9]** 🐼

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Platform](https://img.shields.io/badge/Hardware-Orange_Pi_5_Max-orange)](http://www.orangepi.org/)
[![Status](https://img.shields.io/badge/Mode-CypherPunk-black)](https://getmonero.org/)

> *(Blessed by Sor. Concha)* #CypherPunk

---

## 🏴‍☠️ Descripción
Lula es una IA de trading soberana que opera aislada en Docker. Su lógica de negocio ("Lullaby") consiste en generar liquidez mediante especulación en mercados volátiles (BTC, SOL, ETH) para acumular automáticamente **Monero (XMR)** como reserva de valor privada.

---

## ⚙️ 1. Script de Instalación (Orange Pi)

Configura el entorno (Docker, Drivers NPU, Portainer) en tu Orange Pi 5 Max virgen.

1.  **Conéctate por SSH a tu Orange Pi:**
    ```bash
    ssh root@<TU_IP>
    ```

2.  **Ve al directorio de scripts y da permisos:**
    ```bash
    cd lula_project/scripts/
    chmod +x install_lula.sh
    ```

3.  **Ejecútalo como SuperUsuario:**
    ```bash
    sudo ./install_lula.sh
    ```

> **Nota:** Una vez termine el script, usa **FileZilla** o `scp` para pasar tus archivos de código (`src/`, `.env`, `data/`) dentro de la carpeta `lula_project` que se habrá creado.

---

## 🔌 2. Test de Conexión

Verifica que tu Orange Pi tiene acceso a Kraken antes de levantar el sistema completo.

1.  **Instala las dependencias temporales en la Orange Pi:**
    ```bash
    pip install ccxt python-dotenv
    ```

2.  **Ejecuta el Test:**
    ```bash
    cd lula_project/scripts/
    python3 connection_test.py
    ```

---

## 🧠 3. Entrenamiento en PC (Kali Linux)

**Optimizado para Kali Linux / Ubuntu.**
Este proceso descarga datos históricos, entrena la red neuronal y compila el modelo para el chip RK3588.

**1. Instalar Dependencias del Sistema:**
```bash
sudo apt install -y python3-dev python3-pip python3-venv libxslt1-dev zlib1g-dev libgl1-mesa-glx
2. Crear y Activar Entorno Virtual:

code
Bash

download

content_copy

expand_less
cd lula_project/scripts/trainer
python3 -m venv venv
source venv/bin/activate
3. Instalar Dependencias de Python:

code
Bash

download

content_copy

expand_less
pip install -r trainer_requirements.txt
4. Ejecutar Entrenador:

code
Bash

download

content_copy

expand_less
python trainer.py
Sobre el archivo .rknn final
El script intentará generar el archivo madness.rknn automáticamente.

Opción A (Nativa): Si tienes el rknn-toolkit2 instalado en Kali, el archivo se generará en la carpeta data/.
Opción B (Docker Fallback): Si el script solo genera el .onnx por falta de librerías, ejecuta este comando en tu PC para convertirlo:
code
Bash

download

content_copy

expand_less
docker run -v $(pwd)/../../data:/data --entrypoint python3 \
rockchip/rknn-toolkit2 \
-c "from rknn.api import RKNN; r=RKNN(verbose=False); r.config(target_platform='rk3588'); r.load_onnx('/data/madness.onnx'); r.build(do_quantization=False); r.export_rknn('/data/madness.rknn')"
🐳 4. Ejecución (Producción)
Una vez tengas el cerebro (madness.rknn) y las claves (.env) en tu Orange Pi:

code
Bash

download

content_copy

expand_less
cd lula_project/docker
docker compose up -d --build
Comandos útiles:

Ver logs: docker logs -f lula_bot
Apagar: docker compose down
⚖️ Licencia
Distribuido bajo la licencia Apache 2.0.

code
Code

download

content_copy

expand_less
