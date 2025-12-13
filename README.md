# 💶 lula.py

> **Artificial Intelligence for CryptoTrading — Expert of Monero**  
> *Made with LOVE for Orange Pi 5 Max — Python 3.9* 🐼

| **LICENSE** | **HARDWARE** | **MODE** |
| :--- | :--- | :--- |
| Apache 2.0 📜 | Orange Pi 5 Max 🍊 | Need $$$ 🤑 |

🙏 **Blessed by Sor. Concha** — `#CypherPunk`

---
---

## 📝 Descripción

**Lula** es un sistema autónomo de **generación y preservación de capital**, impulsado por Inteligencia Artificial y diseñado para la soberanía, desconfianza estructural y autocustodia. Opera sobre el silicio de una Orange Pi 5 Max, acelerada por NPU.   Su función es clara: **extraer valor del caos**.

### ⚙️ Flujo Operativo

- **Generación de Cash**  
  Explotación sistemática de ineficiencias en mercados líquidos (BTC, ETH, SOL) para producir flujo constante de USDT.

- **Rotación de Liquidez**  
  Conversión automática del excedente de cash en activos fungibles y orientados a privacidad (XMR).

- **Custodia Soberana**  
  Retiro a almacenamiento en frío. Sin intermediarios. Sin confianza delegada.

## 🤓 Filosofía

Lula extrae volatilidad y desconfianza para generar cash, y utiliza ese cash para comprar privacidad.  
Automatiza la disciplina, reduce la exposición y saca el capital del foco.  
La visibilidad es riesgo. La automatización es defensa. La autocustodia es ley.

**Lula es magia y disciplina, ejecución constante y una arquitectura pensada para operar 24/7, incluso cuando tú descansas.**

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
