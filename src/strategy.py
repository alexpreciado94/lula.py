TARGET_XMR_PCT = 0.40   # Máximo 40% del portafolio en XMR
RSI_BUY_LIMIT = 40      # Comprar solo si RSI < 40
MIN_USDT_RESERVE = 50   # Siempre dejar 50 USDT para operar

def gestionar_oportunidad_xmr(exchange, precio_xmr, rsi_xmr, score_ia):
    """Decide si comprar Monero hoy"""
    
    # 1. Chequear Saldo
    bal = exchange.fetch_balance()
    usdt_total = bal['USDT']['total']
    xmr_total = bal['XMR']['total'] if 'XMR' in bal else 0
    
    # Valor total
    val_xmr = xmr_total * precio_xmr
    val_total = usdt_total + val_xmr
    
    # % Actual
    pct_xmr = val_xmr / val_total if val_total > 0 else 0
    
    # 2. Reglas de Negocio
    if pct_xmr >= TARGET_XMR_PCT:
        return False, "Techo de XMR alcanzado"
        
    if usdt_total < MIN_USDT_RESERVE + 10:
        return False, "Sin liquidez suficiente"
        
    # 3. El Francotirador (Técnico + IA)
    # Compramos si está barato (RSI bajo) O si la IA ve un pump inminente (Score alto)
    should_buy = (rsi_xmr < RSI_BUY_LIMIT) or (score_ia > 0.85)
    
    if should_buy:
        amount_to_spend = usdt_total - MIN_USDT_RESERVE
        return True, amount_to_spend
    
    return False, "Esperando mejor oportunidad"