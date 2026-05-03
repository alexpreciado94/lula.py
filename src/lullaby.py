import os
from datetime import datetime

# XMR eliminado de GENERATOR_COINS — Binance no lo tiene desde 2024
# Se gestiona exclusivamente desde connection.safe (CoinEx)
GENERATOR_COINS = [
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "NEAR/USDT", "FET/USDT",
    "PENDLE/USDT", "RENDER/USDT", "SUI/USDT",
    "LINK/USDT", "AVAX/USDT", "POL/USDT", "XRP/USDT",
    "PEPE/USDT", "ADA/USDT", "DOT/USDT"
]

TARGET_COIN = "XMR/USDT"  # Solo se opera desde CoinEx (connection.safe)

# =========================
# UTILIDADES
# =========================

def normalize(val, min_v, max_v):
    if max_v - min_v == 0:
        return 0
    return max(0, min(1, (val - min_v) / (max_v - min_v)))

def trend_filter(price, ema200=None):
    if ema200 is not None and price < ema200 * 0.985:
        return False
    return True

def get_env_float(key, default):
    return float(os.getenv(key, default))

# =========================
# UMBRAL DINÁMICO
# =========================

def get_dynamic_threshold(vix=20.0, rvol=1.0):
    base       = float(os.getenv("BUY_THRESHOLD_IA", 0.55))
    vix_factor = max(0, (vix - 20) * 0.003)
    rvol_factor= max(0, (rvol - 1.5) * 0.02)
    return min(base + vix_factor + rvol_factor, 0.28)

# =========================
# SCORE PROMETHEUS v7.7
# =========================

def calculate_weighted_score(prob, rsi, imbalance, rvol=1.0, vix=20.0):
    buy_threshold = float(os.getenv("BUY_THRESHOLD_IA", 0.55))
    rsi_buy_zone  = float(os.getenv("RSI_BUY_ZONE", 40))
    rsi_sell_zone = float(os.getenv("RSI_SELL_ZONE", 75))

    prob_n = min(1.0, prob / buy_threshold)
    if prob > 0:
        prob_n = max(0.20, prob_n)

    rsi_clamped = max(20, min(rsi_sell_zone, rsi))
    rsi_n = 1 - ((rsi_clamped - 20) / (rsi_sell_zone - 20))
    if rsi <= rsi_buy_zone:
        rsi_n += 0.15

    imb_n  = (max(-0.5, min(0.5, imbalance)) + 0.5)
    rvol_n = (max(0.5, min(2.5, rvol)) - 0.5) / 2.0

    w_ia, w_rsi, w_imb, w_vol = 0.45, 0.25, 0.20, 0.10
    score_f = (prob_n * w_ia) + (rsi_n * w_rsi) + (imb_n * w_imb) + (rvol_n * w_vol)

    return max(0, min(100, int(score_f * 100)))

# =========================================================
# LULA CA$H FLOW v7.7 - GESTIÓN DE RIESGO INTEGRADA
# =========================================================

def get_status_label(prob, score, ok_macro, val_usd, rsi, **kwargs):
    from show import C

    symbol  = kwargs.get('symbol', "")
    price   = kwargs.get('price', 0)
    guardian = kwargs.get('guardian', None)

    if "XMR" in symbol:
        return f"{C.C}💎 AHORROS{C.R}"

    if not ok_macro:
        return f"{C.RE}☣️ RIESGO{C.R}"

    # =========================================================
    # REGLAS DE SALIDA ACTIVA (GESTIÓN DE RIESGO)
    # =========================================================
    if val_usd >= 5.0:
        # --- REGLA 1: STOP-LOSS ---
        if guardian and price > 0:
            datos = guardian.get_datos_posicion(symbol)
            precio_entrada = datos.get("precio_entrada", 0)
            sl_pct = float(os.getenv("STOP_LOSS_PCT", 0.05))

            if precio_entrada > 0 and price <= precio_entrada * (1 - sl_pct):
                return f"{C.RE}🛑 STOP{C.R}"

        # --- REGLA 3: SCORE MÍNIMO PARA HOLDING ---
        if score < 40:
            return f"{C.RE}📉 SCORE{C.R}"

        # --- LÓGICA DE SALIDA POR ESTRATEGIA ---
        sell_threshold = float(os.getenv("SELL_THRESHOLD_IA", 0.38))
        rsi_sell_zone  = float(os.getenv("RSI_SELL_ZONE", 75))

        if rsi >= rsi_sell_zone or prob <= sell_threshold:
            return f"{C.RE}💥 VENTA{C.R}"

        return f"{C.G}📈 HOLDING{C.R}"

    # =========================================================
    # LÓGICA DE ENTRADA
    # =========================================================
    buy_threshold = float(os.getenv("BUY_THRESHOLD_IA", 0.55))
    rsi_buy_zone  = float(os.getenv("RSI_BUY_ZONE", 40))

    if prob >= buy_threshold and score >= 65:
        return f"{C.G}🚀 COMPRA{C.R}"

    if prob > (buy_threshold * 0.75) or rsi <= rsi_buy_zone:
        if score >= 38:
            return f"{C.Y}📡 ACECHO{C.R}"

    return f"{C.GR}💤 REPOSO{C.R}"


# =========================================================
# MEJORA A — SCALING IN (Entradas Escalonadas)
# Propuesta en auditoría técnica: en lugar de entrar con un
# bloque fijo, el bot entra en dos tramos según la IA Prob.
#
#   Tramo 1: prob > umbral base        → 50% del monto calculado
#   Tramo 2: prob > umbral_alto (0.75) → 50% restante (si el
#            precio confirma tendencia, gestionado en main.py)
#
# La función devuelve (monto_tramo1, monto_tramo2, es_escalonado)
# Si prob no supera el umbral alto, es_escalonado=False y
# monto_tramo2=0 (entrada única, comportamiento anterior).
# =========================================================

def get_position_size(available_usdt, total_equity, current_val_usd, score, prob, **kwargs):
    """
    LULA v6.2 — Motor de tamaño dinámico para interés compuesto.
    """
    from sub import calculate_ia_weight
    
    # 1. PESO POR TIER (Agresividad vs Capital)
    # Si tienes $300, cada apuesta es del 15% ($45).
    # Si tienes $20,000, cada apuesta baja al 5% ($1000) para mayor estabilidad.
    if total_equity < 1500:
        pct_per_trade = 0.15 
    elif total_equity < 10000:
        pct_per_trade = 0.08
    else:
        pct_per_trade = 0.05

    # 2. IA-WEIGHTING (0.0 a 1.0)
    weight = calculate_ia_weight(prob)
    if weight <= 0: return 0, 0

    # 3. CÁLCULO NOMINAL
    # Monto = Capital Total * % del Tier * Confianza IA * Calidad del Score
    monto_base = total_equity * pct_per_trade * weight * (score / 100)
    
    # Límite de seguridad: no usar más del disponible ni pasarse del 20% en un solo activo
    monto_base = min(monto_base, available_usdt * 0.95, (total_equity * 0.20) - current_val_usd)

    # 4. FILTRO DE MÍNIMO OPERATIVO (Binance/Exchange safety)
    if monto_base < 11.0:
        return 0, 0

    # 5. SCALING IN (Tramo 1 y Tramo 2)
    # IMPORTANTE: Si al dividir en 2 tramos nos quedamos bajo el mínimo ($11), no dividimos.
    scale_thresh = float(os.getenv("SCALE_IN_THRESHOLD_HIGH", 0.75))
    if prob >= scale_thresh and (monto_base * 0.5) >= 11.0:
        return round(monto_base * 0.5, 2), round(monto_base * 0.5, 2)
    
    return round(monto_base, 2), 0


# =========================================================
# MEJORA D — TWAP (Time-Weighted Average Price)
# Para órdenes grandes, divide la compra en N micro-órdenes
# distribuidas a lo largo de `duration_seconds`.
# Activo cuando el monto supera TWAP_MIN_AMOUNT (default $500).
# Configurable por .env:
#   TWAP_MIN_AMOUNT   = 500    (umbral para activar TWAP)
#   TWAP_SLICES       = 5      (número de micro-órdenes)
#   TWAP_DURATION_SEC = 300    (duración total en segundos, 5 min)
# =========================================================

def execute_twap(connection, symbol, total_amount_usd, price, label="TWAP"):
    """
    Ejecuta una compra grande mediante micro-órdenes equidistantes.
    Devuelve el monto total realmente ejecutado (puede ser < total si hay errores parciales).

    Uso en main.py:
        ejecutado = execute_twap(connection, symbol, monto_final, price)
    """
    import time as _time

    twap_min    = get_env_float("TWAP_MIN_AMOUNT", 500.0)
    n_slices    = int(get_env_float("TWAP_SLICES", 5))
    duration    = get_env_float("TWAP_DURATION_SEC", 300.0)
    min_op      = get_env_float("MIN_OP_USDT", 15.0)

    # Solo activar TWAP si el monto lo justifica
    if total_amount_usd < twap_min:
        # Orden única normal
        try:
            qty = connection.gen.amount_to_precision(symbol, total_amount_usd / price)
            connection.gen.create_market_order(symbol, "buy", qty)
            print(f"🚀 COMPRA DIRECTA: {symbol} | ${total_amount_usd:.2f}")
            return total_amount_usd
        except Exception as e:
            print(f"⚠️ Error compra directa {symbol}: {e}")
            return 0.0

    # TWAP activo
    monto_slice  = round(total_amount_usd / n_slices, 2)
    sleep_between = duration / n_slices
    ejecutado    = 0.0

    print(f"⏱️ TWAP {label}: {symbol} | ${total_amount_usd:.2f} en {n_slices} tramos × ${monto_slice:.2f} cada {sleep_between:.0f}s")

    for i in range(n_slices):
        if monto_slice < min_op:
            print(f"  ↳ Tramo {i+1}: slice ${monto_slice:.2f} < mínimo, abortando TWAP")
            break
        try:
            # Refrescamos precio en cada tramo para mejorar precio medio
            try:
                ticker      = connection.gen.fetch_ticker(symbol)
                live_price  = ticker.get("last", price)
            except:
                live_price  = price

            qty = connection.gen.amount_to_precision(symbol, monto_slice / live_price)
            connection.gen.create_market_order(symbol, "buy", qty)
            ejecutado += monto_slice
            print(f"  ↳ Tramo {i+1}/{n_slices}: ${monto_slice:.2f} @ ${live_price:.4f} ✅")
        except Exception as e:
            print(f"  ↳ Tramo {i+1}/{n_slices}: ⚠️ Error — {e}")

        if i < n_slices - 1:
            _time.sleep(sleep_between)

    print(f"  ↳ TWAP completado: ${ejecutado:.2f} ejecutados de ${total_amount_usd:.2f}")
    return ejecutado


# =========================================================
# MEJORAS PENDIENTES (Roadmap — requieren infraestructura adicional)
# =========================================================
# MEJORA B — HEDGING DINÁMICO
#   Abrir short de BTC/ETH en futuros si DXY sube agresivamente y VIX > 20.
#   Requiere: cuenta de futuros Binance separada + lógica de margin en connection.py
#   TODO: Implementar en connection.py con `defaultType: "future"` y gestión de colateral.
#
# MEJORA C — NLP / SENTIMIENTO SOCIAL
#   Procesar X (Twitter) o Reddit para ajustar el score si el sentimiento contradice la IA.
#   Requiere: API de Twitter/Reddit + modelo NLP (puede ser llamada a API externa).
#   TODO: Añadir módulo `sentiment.py` con función get_sentiment_score(symbol) → [-1, 1].
#
# MEJORA E — SHADOW MODE (ML Feedback Loop)
#   Registrar resultado de cada operación cerrada y reentrenar los pesos del modelo.
#   Requiere: pipeline de reentrenamiento RKNN en el propio RK3588 o servidor externo.
#   TODO: Añadir módulo `shadow.py` que escriba operaciones a un CSV de entrenamiento.
# =========================================================


def manage_bridge(connection):
    try:
        usdt    = connection.get_balance(connection.gen).get("USDT", {}).get("total", 0)
        reserve = float(os.getenv("MIN_CASH_RESERVE", 100.0))
        batch   = float(os.getenv("MIN_BRIDGE_BATCH", 50.0))
        surplus = usdt - reserve
        if surplus >= batch:
            connection.bridge_transfer(
                surplus,
                os.getenv("REFUGE_USDT_DEPOSIT_ADDRESS"),
                os.getenv("BRIDGE_NETWORK", "TRX")
            )
    except:
        pass

def manage_wealth(connection, prob, rsi, price, ok_macro, score=0, riesgo_pct=35, vix=20.0, rvol=1.0):
    """Compra XMR en CoinEx cuando las condiciones son favorables."""
    try:
        usdt = connection.get_balance(connection.safe).get("USDT", {}).get("total", 0)
        if usdt >= 5.1 and ok_macro and prob > 0.05 and score >= 65:
            usdt_a_usar, _ = get_position_size(usdt, usdt, 0, score, prob)
            connection.safe.create_market_order("XMR/USDT", "buy", usdt_a_usar / price)
    except:
        pass

def get_aggressive_allocation(symbol, score, prob, current_balances):
    UMBRAL_AGRESIVO = 85
    if score >= UMBRAL_AGRESIVO and prob > 0.15:
        btc_val       = current_balances.get('BTC', 0)
        eth_val       = current_balances.get('ETH', 0)
        extra_capital = (btc_val * 0.02) + (eth_val * 0.02)
        return True, extra_capital
    return False, 0.0

def get_opportunity_weight(score, prob):
    if score >= 80 and prob > 0.12: return "EXTREMA"
    if score >= 72:                 return "ALTA"
    if score >= 65:                 return "NORMAL"
    return "NULA"

def calculate_rotation_amount(full_bal, prices_map, total_equity):
    """Rotación proporcional al patrimonio total."""
    extra   = 0
    anchors = ['ETH', 'BTC', 'SOL', 'NEAR']
    min_op  = float(os.getenv("MIN_OP_USDT", 11.0))

    for coin in anchors:
        cantidad  = full_bal.get(coin, {}).get('total', 0)
        precio    = prices_map.get(f"{coin}/USDT", 0)
        valor_usd = cantidad * precio
        if valor_usd > (total_equity * 0.15):
            extra += valor_usd * 0.05

    return max(min_op, min(extra, total_equity * 0.10))