lula.py 💶
----------------------------------------

Artificial Intelligence for CryptoTrading — Expert of Monero
Made with LOVE for Orange Pi 5 Max — Python 3.9 🐼

LICENSE: Apache 2.0
HARDWARE: Orange Pi 5 Max
MODE: CypherPunk

Blessed by Sor. Concha — #CypherPunk

----------------------------------------
DESCRIPCIÓN
----------------------------------------
Lula es una IA de trading soberana diseñada para ejecutarse aislada en Docker dentro 
de una Orange Pi 5 Max.  
Su lógica (Lullaby) especula en mercados volátiles (BTC, SOL, ETH) para acumular 
automáticamente Monero (XMR) como reserva de valor privada.

----------------------------------------
1. INSTALACIÓN EN ORANGE PI 5 MAX
----------------------------------------

1) Conéctate por SSH:
    ssh root@<TU_IP>

2) Entra en el directorio de scripts:
    cd lula_project/scripts/
    chmod +x install_lula.sh

3) Ejecuta instalador:
    sudo ./install_lula.sh

NOTA: Al finalizar, sube src/, data/ y .env dentro de lula_project/

----------------------------------------
2. TEST DE CONEXIÓN A KRAKEN
----------------------------------------

1) Instala dependencias temporales:
    pip install ccxt python-dotenv

2) Ejecuta test:
    cd lula_project/scripts/
    python3 connection_test.py

----------------------------------------
3. ENTRENAMIENTO EN PC (Kali / Ubuntu)
----------------------------------------

El entrenamiento generará madness.rknn para la NPU RK3588.

1) Instalar dependencias del sistema:
    sudo apt install -y python3-dev python3-pip python3-venv libxslt1-dev zlib1g-dev libgl1-mesa-glx

2) Crear entorno virtual:
    cd lula_project/scripts/trainer
    python3 -m venv venv
    source venv/bin/activate

3) Instalar dependencias:
    pip install -r trainer_requirements.txt

4) Ejecutar entrenador:
    python trainer.py

----------------------------------------
4. GENERACIÓN DE madness.rknn
----------------------------------------

OPCIÓN A (NATIVA):
Si existe rknn-toolkit2, el .rknn aparecerá en data/.

OPCIÓN B (DOCKER):
    docker run -v $(pwd)/../../data:/data --entrypoint python3 \
    rockchip/rknn-toolkit2 \
    -c "from rknn.api import RKNN; r=RKNN(verbose=False); r.config(target_platform='rk3588'); r.load_onnx('/data/madness.onnx'); r.build(do_quantization=False); r.export_rknn('/data/madness.rknn')"

----------------------------------------
5. EJECUCIÓN EN PRODUCCIÓN (ORANGE PI)
----------------------------------------

Levantar Lula:
    cd lula_project/docker
    docker compose up -d --build

Comandos útiles:
    docker logs -f lula_bot
    docker compose down

----------------------------------------
LICENCIA
----------------------------------------
Apache 2.0