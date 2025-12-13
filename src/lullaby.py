import os

# CONFIGURACIÓN
GENERATOR_COINS = ["SOL/USDT", "ETH/USDT", "BTC/USDT", "DOGE/USDT", "XRP/USDT"]
TARGET_COIN = "XMR/USDT"
MAX_XMR_PERCENT = 0.40
MIN_CASH_RESERVE = 100.0
MIN_BRIDGE_BATCH = 50.0
MIN_XMR_WITHDRAW = 0.5


def detect_liquidity_squeeze(connection, symbol, current_rvol):
    if current_rvol < 2.5:
        return False, ""

    ask_depth, bid_depth = connection.get_order_book_depth(
        connection.safe, symbol
    )
    if ask_depth == 0:
        return False, ""

    if current_rvol > 3.5:
        return True, f"🔥 SQUEEZE (Vol: {current_rvol:.1f}x)"
    return False, ""


def manage_wealth(connection, brain_score, xmr_rsi, xmr_rvol, xmr_price):
    bal = connection.get_balance(connection.safe)
    if not bal:
        return

    usdt = bal.get("USDT", {}).get("total", 0)
    xmr = bal.get("XMR", {}).get("total", 0)

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

    is_squeeze, msg = detect_liquidity_squeeze(connection, TARGET_COIN, xmr_rvol)

    if (xmr_rsi < 35) or (brain_score > 0.85) or is_squeeze:
        print(f"   🧸 Oportunidad! ({msg} Score: {brain_score:.2f})")
        connection.execute_order(
            connection.safe, TARGET_COIN, "buy", usdt / xmr_price
        )
    else:
        print("   ⏳ Esperando mejor entrada XMR.")


def strategy_generator(connection, brain, guardian, symbol, sp500):
    if not connection.validate_symbol(connection.gen, symbol):
        return

    data = connection.get_data(connection.gen, symbol, limit=300)
    if not data:
        return

    ok, msg = guardian.analizar_macro(symbol, data)
    if not ok:
        print(f"   🛡️ BLOQUEO {symbol}: {msg}")
        return

    prob, rsi, price, rvol = brain.analyze(data, sp500)
    if prob is None:
        return

    bal = connection.get_balance(connection.gen)
    base = symbol.split("/")[0]
    held = bal.get(base, {}).get("free", 0)
    usdt = bal.get("USDT", {}).get("free", 0)
    value_held = held * price

    print(f"   ⚡ GEN {symbol}: ${price} | IA: {prob:.2f} | Guardián: OK")

    if prob > 0.92 and value_held < 50:
        if usdt > 15:
            print(f"   🚀 COMPRA AGRESIVA: {symbol}")
            connection.execute_order(
                connection.gen, symbol, "buy", 20.0 / price
            )

    elif (prob < 0.30 or rsi > 75) and value_held > 10:
        print(f"   💰 TAKE PROFIT: {symbol} (RSI: {rsi:.1f})")
        connection.execute_order(connection.gen, symbol, "sell", held)


def manage_bridge(connection):
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
    addr = os.getenv("TREZOR_XMR_ADDRESS")
    if not addr:
        return
    bal = connection.get_balance(connection.safe)
    if not bal:
        return

    xmr_free = bal.get("XMR", {}).get("free", 0)
    if xmr_free > MIN_XMR_WITHDRAW:
        connection.withdraw_to_trezor("XMR", xmr_free - 0.001, addr)