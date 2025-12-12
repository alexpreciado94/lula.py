# --- CONFIGURACIÓN ---
GENERATOR_COINS = ['SOL/USDT', 'ETH/USDT', 'BTC/USDT'] # En Exchange A
TARGET_COIN = 'XMR/USDT'                               # En Exchange B

# Ajustes Trezor
MIN_XMR_TO_WITHDRAW = 0.5  # No retirar migajas para no pagar fees tontos
TREZOR_ADDRESS = None      # Se carga desde .env en main

def manage_cold_storage(connection):
    """
    Fase final: Vaciar el Exchange B hacia el Trezor.
    """
    from os import getenv
    trezor_addr = getenv('TREZOR_XMR_ADDRESS')
    if not trezor_addr: return

    # Miramos saldo en el Exchange de Refugio (self.safe)
    balance = connection.get_balance(connection.safe)
    if not balance: return
    
    xmr_free = balance.get('XMR', {}).get('free', 0)
    
    if xmr_free > MIN_XMR_TO_WITHDRAW:
        print(f"   ❄️ BÓVEDA: Detectados {xmr_free:.4f} XMR listos para frío.")
        # Retiramos TODO menos una migaja para fees
        amount = xmr_free - 0.001 
        connection.withdraw_to_trezor('XMR', amount, trezor_addr)
    else:
        print(f"   🧊 Acumulando XMR ({xmr_free:.4f}/{MIN_XMR_TO_WITHDRAW}).")

def strategy_generator(connection, brain, symbol, sp500):
    """
    Lógica Agresiva para Exchange A (Binance).
    Objetivo: Generar USDT.
    """
    # Usamos el exchange GEN
    data = connection.get_data(connection.gen, symbol)
    if not data: return

    prob, rsi, price, _ = brain.analyze(data, sp500)
    if prob is None: return

    print(f"   ⚡ GEN {symbol}: ${price} | IA: {prob:.2f}")

    # COMPRA AGRESIVA
    if prob > 0.92:
        print(f"   🚀 COMPRA GENERADORA: {symbol}")
        # connection.execute_order(connection.gen, symbol, 'buy', ...)
    
    # VENTA RÁPIDA (Take Profit)
    elif prob < 0.30:
        print(f"   💰 TOMA DE BENEFICIOS: {symbol}")
        # connection.execute_order(connection.gen, symbol, 'sell', ...)

def strategy_savings(connection, brain, sp500):
    """
    Lógica Paciente para Exchange B (KuCoin).
    Objetivo: Comprar XMR barato.
    """
    # Usamos el exchange SAFE
    data = connection.get_data(connection.safe, TARGET_COIN)
    if not data: return

    prob, rsi, price, rvol = brain.analyze(data, sp500)
    
    # Chequear saldo USDT en el exchange B
    bal = connection.get_balance(connection.safe)
    usdt = bal.get('USDT', {}).get('free', 0)
    
    if usdt < 10: 
        print("   ⚠️ Refugio: Sin USDT. (Recuerda transferir ganancias del Generador).")
        return

    # Lógica Lullaby (Más exigente que la generadora)
    # Solo compramos si está MUY barato (RSI < 30) o Squeeze
    is_buy = (rsi < 30) or (prob > 0.85)
    
    if is_buy:
        print(f"   🧸 OPORTUNIDAD XMR: Comprando con ${usdt:.2f}")
        connection.execute_order(connection.safe, TARGET_COIN, 'buy', usdt / price)