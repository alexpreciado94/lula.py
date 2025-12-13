# lula.py 💶

### High-Performance AI Crypto Trading Bot - Monero Sovereign Accumulator
**Optimized for Orange Pi 5 Max (RK3588 NPU). [Python 3.9]**

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Platform](https://img.shields.io/badge/Hardware-Orange_Pi_5_Max-orange)](http://www.orangepi.org/)
[![Architecture](https://img.shields.io/badge/Architecture-Dual_Exchange-red)](https://ccxt.network/)

---

## 📝 Descripción Técnica

**Lula** es un sistema de trading algorítmico diseñado para operar en el borde (*Edge Computing*). Su objetivo es la acumulación soberana de **Monero (XMR)** mediante una estrategia de arbitraje temporal y generación de flujo de caja en mercados volátiles.

El sistema utiliza una **Arquitectura de Doble Exchange** para mitigar riesgos de contraparte y maximizar la privacidad:

1.  **🏭 Motor Generador (Exchange A):** Opera en pares de alta liquidez (BTC, ETH, SOL) utilizando inferencia neuronal (NPU) para *swing trading* agresivo. El objetivo es maximizar el balance en USDT.
2.  **🌉 Puente de Liquidez (The Bridge):** Al alcanzar umbrales de beneficio, el sistema ejecuta automáticamente transferencias *cross-exchange* (vía TRC20) hacia el entorno seguro.
3.  **🛡️ Motor de Refugio (Exchange B):** Ejecuta órdenes de compra pasivas sobre XMR/USDT basadas en análisis de volumen y RSI, minimizando el deslizamiento (*slippage*).
4.  **❄️ Custodia Fría:** Automatización de retiros hacia hardware wallets (Trezor) para asegurar la propiedad final de los activos.

---

## ⚡ Requisitos de Hardware

*   **Dispositivo:** Orange Pi 5 Max (SoC Rockchip RK3588).
*   **Alimentación:** ⚠️ **Fuente PD 5V/4A (20W) Mínimo.** El uso de fuentes inestables provocará corrupción de datos en operaciones de I/O intensivas (Docker/NPU).
*   **Almacenamiento:** NVMe SSD recomendado para logs y base de datos.

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