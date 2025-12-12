# 💶 lula.py

> **Artificial Intelligence for CryptoTrading — Expert of Monero**  
> *Made with LOVE for Orange Pi 5 Max — Python 3.9* 🐼

| **LICENSE** | **HARDWARE** | **MODE** |
| :--- | :--- | :--- |
| Apache 2.0 📜 | Orange Pi 5 Max 🍊 | CypherPunk 🕶️ |

🙏 **Blessed by Sor. Concha** — `#CypherPunk`

---

## 📝 DESCRIPCIÓN

**Lula** es una IA de trading, diseñada para ejecutarse en **Docker** 🐳 dentro de una **Orange Pi 5 Max**.

Su lógica (*Lullaby*) especula en mercados volátiles para acumular automáticamente **Monero (XMR)** 🔒 como reserva de valor privada.

### ☠️ El Modus Operandi

1.  **Hit & Run (El Golpe):** Lula monitorea las monedas ruidosas (BTC, ETH, SOL). Cuando detecta una oportunidad matemática, entra, golpea y extrae liquidez (USDT) antes de que el mercado reaccione.
2.  **Ghost Protocol (El Fantasma):** El dinero en un exchange es dinero vigilado. Lula no deja rastro: convierte automáticamente el botín a **Monero (XMR)**, moviendo el valor fuera del radar.
3.  **System Shutdown:** El mercado nunca cierra, pero tú sí. Lula absorbe el estrés y la paranoia del trading 24/7 para que tú puedas desconectar.

---

## 1. ⚙️ INSTALACIÓN EN ORANGE PI 5 MAX

**1) Conéctate por SSH:**
```bash
ssh root@<TU_IP>
```

**2) Entra en el directorio de scripts:**
```bash
cd lula_project/scripts/
chmod +x install_lula.sh
```

**3) Ejecuta el instalador:**
```bash
sudo ./install_lula.sh
```

> ⚠️ **NOTA:** Al finalizar, asegúrate de subir `src/`, `data/` y `.env` dentro de `lula_project/`.

---

## 2. 🐙 TEST DE CONEXIÓN A KRAKEN

**1) Instala dependencias temporales:**
```bash
pip install ccxt python-dotenv
```

**2) Ejecuta el test:**
```bash
cd lula_project/scripts/
python3 connection_test.py
```

---

## 3. 🧠 ENTRENAMIENTO EN PC (Kali / Ubuntu)

El entrenamiento generará el modelo `madness.rknn` optimizado para la NPU RK3588.

**1) Instalar dependencias del sistema:**
```bash
sudo apt install -y python3-dev python3-pip python3-venv libxslt1-dev zlib1g-dev libgl1-mesa-glx
```

**2) Crear entorno virtual:**
```bash
cd lula_project/scripts/trainer
python3 -m venv venv
source venv/bin/activate
```

**3) Instalar dependencias de Python:**
```bash
pip install -r trainer_requirements.txt
```

**4) Ejecutar el entrenador:**
```bash
python trainer.py
```

---

## 4. 🔮 GENERACIÓN DE `madness.rknn`

### OPCIÓN A (NATIVA) 🖥️
Si tienes instalado `rknn-toolkit2`, el archivo `.rknn` aparecerá automáticamente en `data/`.

### OPCIÓN B (DOCKER) 🐳
Ejecuta el siguiente comando para convertir el modelo usando un contenedor:

```bash
docker run -v $(pwd)/../../data:/data --entrypoint python3 \
rockchip/rknn-toolkit2 \
-c "from rknn.api import RKNN; r=RKNN(verbose=False); r.config(target_platform='rk3588'); r.load_onnx('/data/madness.onnx'); r.build(do_quantization=False); r.export_rknn('/data/madness.rknn')"
```

---

## 5. 🚀 EJECUCIÓN EN PRODUCCIÓN (ORANGE PI)

**Levantar Lula:**
```bash
cd lula_project/docker
docker compose up -d --build
```

**Comandos útiles:**
*   Ver logs: `docker logs -f lula_bot` 📜
*   Apagar: `docker compose down` 🛑

---
