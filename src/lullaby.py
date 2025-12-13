import os

# --- CONFIGURACIÓN ---
GENERATOR_COINS = ["SOL/USDT", "ETH/USDT", "BTC/USDT", "DOGE/USDT", "XRP/USDT"]
TARGET_COIN = "XMR/USDT"

# Reglas Patrimonio
MAX_XMR_PERCENT = 0.40
MIN_CASH_RESERVE = 100.0
MIN_BRIDGE_BATCH = 50.0
MIN_XMR_WITHDRAW = 0.5


def detect_liquidity_squeeze(connection, symbol, current_rvol):
    """Detecta Squeeze: Mucho volumen + Poca oferta en el libro."""
    if current_rvol < 2.5:
        return False, ""

    # Usamos el exchange de refugio (donde compramos XMR)
    ask_depth, bid_depth = connection.get_order_book_depth(connection.safe, symbol)
    if ask_depth == 0:
        return False, ""

    # Si el volumen es 3.5x lo normal, asumimos presión extrema
    if current_rvol > 3.5:
        return True, f"🔥 SQUEEZE (Vol: {current_rvol:.1f}x)"
    return False, ""


def manage_wealth(connection, brain_score, xmr_rsi, xmr_rvol, xmr_price):
    """Estrategia Ahorro (Exchange B - Refugio)."""
    bal = connection.get_balance(connection.safe)
    if not bal:
        return

    # Normalizar nombres (USDT/USD, XMR/XXMR)
    usdt = bal.get("USDT", {}).get("total", 0)
    if usdt == 0:
        usdt = bal.get("USD", {}).get("total", 0)

    xmr = bal.get("XMR", {}).get("total", 0)
    if xmr == 0:
        xmr = bal.get("XXMR", {}).get("total", 0)

    total = usdt + (xmr * xmr_price)
    if total == 0:
        return
    pct = (xmr * xmr_price) / total

    print(f"   💼 [REFUGIO] Total: ${total:.2f} | XMR: {pct*100:.1f}% | Cash: ${usdt:.2f}")

    if pct >= MAX_XMR_PERCENT:
        print("   ✋ Límite XMR alcanzado.")
        return
    if usdt < 5:
        print("   🌱 Sin cash para comprar XMR.")
        return

    # Oportunidad: Barato, IA Segura o Squeeze
    is_squeeze, msg = detect_liquidity_squeeze(connection, TARGET_COIN, xmr_rvol)

    if (xmr_rsi < 35) or (brain_score > 0.85) or is_squeeze:
        print(f"   🧸 Oportunidad! ({msg} Score: {brain_score:.2f})")
        connection.execute_order(connection.safe, TARGET_COIN, "buy", usdt / xmr_price)
    else:
        print("   ⏳ Esperando mejor entrada XMR.")


def strategy_generator(connection, brain, guardian, symbol, sp500):
    """Estrategia Mercenaria (Exchange A - Generador) con Guardián Macro."""
    if not connection.validate_symbol(connection.gen, symbol):
        return

    # Necesitamos historia suficiente para la SMA200 del Guardián
    data = connection.get_data(connection.gen, symbol, limit=300)
    if not data:
        return

    # 1. FILTRO DEL GUARDIÁN (Macro + Ballenas + Imbalance)
    # Pasamos el connection y el exchange object para que pueda mirar el libro
    ok, msg = guardian.analizar_macro(connection, connection.gen, symbol, data)

    if not ok:
        print(f"   🛡️ BLOQUEO {symbol}: {msg}")
        return  # No operamos si el guardián ve peligro

    # 2. ANÁLISIS TÉCNICO (NPU)
    prob, rsi, price, rvol = brain.analyze(data, sp500)
    if prob is None:
        return

    # Check tenencia actual
    bal = connection.get_balance(connection.gen)
    base = symbol.split("/")[0]
    held = bal.get(base, {}).get("free", 0)
    usdt = bal.get("USDT", {}).get("free", 0)
    value_held = held * price

    print(f"   ⚡ GEN {symbol}: ${price} | IA: {prob:.2f} | Guardián: OK")

    # COMPRA (Si IA > 0.92 y tenemos poco invertido)
    if prob > 0.92 and value_held < 50:
        if usdt > 15:
            print(f"   🚀 COMPRA AGRESIVA: {symbol}")
            # Tamaño de orden fijo para gestión de riesgo ($20)
            connection.execute_order(connection.gen, symbol, "buy", 20.0 / price)

    # VENTA (Take Profit o Miedo IA o Sobrecompra Extrema)
    elif (prob < 0.30 or rsi > 75) and value_held > 10:
        print(f"   💰 TAKE PROFIT: {symbol} (RSI: {rsi:.1f})")
        connection.execute_order(connection.gen, symbol, "sell", held)


def manage_bridge(connection):
    """Mueve ganancias del Generador al Refugio."""
    bal = connection.get_balance(connection.gen)
    if not bal:
        return
    usdt = bal.get("USDT", {}).get("total", 0)

    surplus = usdt - MIN_CASH_RESERVE
    if surplus >= MIN_BRIDGE_BATCH:
        addr = os.getenv("REFUGE_USDT_DEPOSIT_ADDRESS")
        net = os.getenv("BRIDGE_NETWORK", "TRX")
        if addr:
            connection.bridge_transfer(surplus, addr, net)


def manage_cold_storage(connection):
    """Mueve XMR del Refugio al Trezor."""
    addr = os.getenv("TREZOR_XMR_ADDRESS")
    if not addr:
        return
    bal = connection.get_balance(connection.safe)
    if not bal:
        return

    xmr_free = bal.get("XMR", {}).get("free", 0)
    if xmr_free > MIN_XMR_WITHDRAW:
        # Dejamos una migaja para fees (0.001)
        connection.withdraw_to_trezor("XMR", xmr_free - 0.001, addr)
