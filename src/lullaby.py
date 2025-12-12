# --- CONFIGURACIÓN DE ESTRATEGIA ---
GENERATOR_COINS = ['SOL/USD', 'ETH/USD', 'BTC/USD']
TARGET_COIN = 'XMR/USD'

# Reglas de Seguridad
MAX_XMR_PERCENT = 0.40         
MIN_CASH_RESERVE = 100.0          
MIN_XMR_BUY_SIZE = 15.0             

def manage_wealth(connection, xmr_price, brain_score, xmr_rsi):
    """
    Decide si coge el exceso de liquidez y compra Monero.
    """
    balance = connection.get_balance()
    if not balance: return

    # 1. Normalizar nombres de Kraken
    usd_total = balance.get('USD', {}).get('total', 0)
    if usd_total == 0: usd_total = balance.get('ZUSD', {}).get('total', 0)
    
    xmr_total = balance.get('XMR', {}).get('total', 0)
    if xmr_total == 0: xmr_total = balance.get('XXMR', {}).get('total', 0)

    total_wealth_usd = usd_total + (xmr_total * xmr_price)

    if total_wealth_usd == 0: return 

    current_xmr_pct = (xmr_total * xmr_price) / total_wealth_usd

    print(f"   💼 Patrimonio Total: ${total_wealth_usd:.2f}")
    print(f"   📊 Estado XMR:       {current_xmr_pct*100:.1f}% (Límite: {MAX_XMR_PERCENT*100}%)")
    print(f"   💵 Liquidez (USD):   ${usd_total:.2f}")

    # Regla A: Techo de Ahorro
    if current_xmr_pct >= MAX_XMR_PERCENT:
        print("   ✋ Límite de XMR alcanzado. Acumulando USD.")
        return

    # Regla B: Excedente de Liquidez
    surplus = usd_total - MIN_CASH_RESERVE
    if surplus < MIN_XMR_BUY_SIZE:
        print("   🌱 Capital creciendo (Aún no hay excedente para ahorrar).")
        return

    # Regla C: Oportunidad de Mercado
    is_good_time = (xmr_rsi < 35) or (brain_score > 0.85)

    if is_good_time:
        print(f"   🧸 Oportunidad detectada (Brain: {brain_score:.2f} | RSI: {xmr_rsi:.1f})")
        print(f"   💸 Invirtiendo excedente (${surplus:.2f}) en Monero...")
        
        xmr_amount = surplus / xmr_price
        connection.execute_order(TARGET_COIN, 'market', 'buy', xmr_amount)
    else:
        print("   ⏳ Precio de XMR no es óptimo. Esperando mejor oportunidad.")

def operate_speculation(connection, brain, symbol):
    """
    Analiza una moneda generadora y opera solo si la señal es MUY clara.
    """
    data = connection.get_data(symbol)
    if not data: return

    prob, rsi, price = brain.analyze(data)
    if prob is None: return

    print(f"   🔹 {symbol}: ${price} | Brain Score: {prob:.2f} | RSI: {rsi:.1f}")

    # Lógica conservadora: Solo entrar si la probabilidad es > 90%
    if prob > 0.90:
        print(f"   🚀 SEÑAL FUERTE DE COMPRA en {symbol}.")
        # connection.execute_order(symbol, 'market', 'buy', amount...)
    
    elif prob < 0.20:
         print(f"   📉 SEÑAL DE VENTA en {symbol}.")
         # connection.execute_order(symbol, 'market', 'sell', amount...)