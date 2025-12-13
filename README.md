# 💶 lula.py

> **Artificial Intelligence for CryptoTrading — Expert of Monero**  
> *Made with LOVE for Orange Pi 5 Max — Python 3.9* 🐼

| **LICENSE** | **HARDWARE** | **MODE** |
| :--- | :--- | :--- |
| Apache 2.0 📜 | Orange Pi 5 Max 🍊 | Need $$$ 🤑 |

🙏 **Blessed by Sor. Concha** — `#CypherPunk`

---

## 📝 Descripción

**Lula** es un sistema autónomo de **generación y preservación de capital**, impulsado por Inteligencia Artificial y diseñado para la soberanía, desconfianza estructural y autocustodia. Opera sobre el silicio de una Orange Pi 5 Max, acelerada por NPU.   Su función es clara: **extraer valor del caos**.

### ⚙️ Flujo Operativo

- **Generación de Cash**  
  Explotación sistemática de los mercados con mayor liquidez, para producir flujo constante de USDT.

- **Rotación de Liquidez**  
  Conversión automática del excedente de cash en activos fungibles y orientados a privacidad (XMR).

- **Custodia Soberana**  
  Retiro a almacenamiento en frío. Sin intermediarios. Sin confianza delegada.

## 🤓 Filosofía

Lula extrae volatilidad y desconfianza para generar cash, y utiliza ese cash para comprar privacidad. Automatiza la disciplina, reduce la exposición y saca el capital del foco. La visibilidad es riesgo. La automatización es defensa. La autocustodia es ley.

**Lula es magia y disciplina, ejecución constante y una arquitectura pensada para operar 24/7, incluso cuando tú descansas.**

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Platform](https://img.shields.io/badge/Hardware-Orange_Pi_5_Max-orange)](http://www.orangepi.org/)
[![Architecture](https://img.shields.io/badge/Architecture-Dual_Exchange-red)](https://ccxt.network/)

---

## 🛠️ FASE 1: Despliegue de Infraestructura

El sistema se despliega mediante un script automatizado que configura Docker, los drivers de la NPU y el entorno de ejecución.

1.  **Acceso SSH:**
    ```bash
    ssh root@<IP_ORANGE_PI>
    ```

2.  **Ejecución del Instalador:**
    ```bash
    cd lula_project/scripts/
    chmod +x install_lula.sh
    sudo ./install_lula.sh
    ```

3.  **Provisión de Archivos (Manual):**
    Transfiere los siguientes activos al directorio `/home/usuario/lula_project` usando SFTP/SCP:
    *   Directorio `src/` (Código fuente).
    *   Archivo `.env` (Configuración de API Keys para ambos exchanges).
    *   Archivo `libs/pandas_ta.zip` (Dependencia vendorizada).

---

## 🔌 FASE 2: Verificación de Conectividad

Antes del despliegue en producción, se debe validar la latencia y permisos de las APIs de ambos exchanges.

1.  **Instalación de dependencias de test:**
    ```bash
    pip install ccxt python-dotenv
    ```

2.  **Ejecución del Diagnóstico:**
    ```bash
    cd lula_project/scripts/
    python3 connection_test.py
    ```
    *Verificar salida exitosa para "GENERADOR" y "REFUGIO".*

---

## 🧠 FASE 3: Entrenamiento de Modelos (Off-Board)

**Entorno:** PC / Servidor Linux x86_64 (Kali/Ubuntu).
**Objetivo:** Generar el modelo `madness.rknn` optimizado para la NPU.

1.  **Preparación del Entorno:**
    ```bash
    cd lula_project/scripts/trainer
    python3 -m venv venv && source venv/bin/activate
    pip install -r trainer_requirements.txt
    ```

2.  **Ejecución del Pipeline:**
    ```bash
    python trainer.py
    ```
    *Este proceso descarga datos históricos (Kraken + Yahoo Finance), entrena la red neuronal (TensorFlow) y exporta los artefactos.*

3.  **Artefactos Resultantes:**
    Se generarán dos archivos críticos en `data/` que deben ser transferidos a la Orange Pi:
    *   `madness.rknn` (Modelo compilado).
    *   `scaler.pkl` (Objeto de normalización).

---

## 🐳 FASE 4: Ejecución en Producción

Con la infraestructura lista y los modelos cargados:

```bash
cd lula_project/docker
docker compose up -d --build
```

**Monitorización:**
*   Logs en tiempo real: `docker logs -f lula_bot`
*   Gestión de contenedores: Puerto `9000` (Portainer).

---

### ⚖️ Licencia
Distribuido bajo la licencia **Apache 2.0**.

**Descargo de Responsabilidad:** Este software es experimental. El trading algorítmico conlleva riesgos financieros significativos. El autor no se hace responsable de pérdidas por fallos de software, errores de API o volatilidad del mercado.
```
