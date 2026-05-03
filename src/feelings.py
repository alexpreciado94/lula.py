# feelings.py — Psicología de Mercado y Gestión de Tiers
import os

def get_market_permission(btc_imb, dxy, vix, fng, total_equity):
    """
    Define el riesgo según el capital y el pánico del mercado.
    """
    # 1. IDENTIFICACIÓN DE TIER (Escalabilidad Automática)
    if total_equity < 1500:
        tier = "SEED"          # Tu fase actual ($300+)
        max_positions = 2      # Concentración máxima para vencer comisiones
        base_exposure = 0.40   # Permitimos hasta 40% invertido ($120 de $300)
    elif total_equity < 10000:
        tier = "GROWTH"        # Fase de expansión
        max_positions = 5      
        base_exposure = 0.50   
    else:
        tier = "INSTITUTIONAL" # Fase de preservación
        max_positions = 10     
        base_exposure = 0.65   

    # 2. FRENO DE MANO (Protección de cuenta pequeña)
    # En cuentas SEED, el pánico de BTC es letal. Somos más estrictos.
    panic_threshold = -0.70 if total_equity < 1500 else -0.80
    
    if btc_imb <= panic_threshold:
        return "CRITICAL", 0.05, 1, tier # Solo 5% de riesgo, 1 posición
    
    # 3. FILTRO VOLATILIDAD
    if vix > 22.0 or dxy > 102.0:
        return "CAUTION", base_exposure * 0.5, max_positions // 2, tier

    return "NORMAL", base_exposure, max_positions, tier