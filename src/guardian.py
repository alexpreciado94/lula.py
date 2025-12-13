import pandas as pd
import pandas_ta as ta  # noqa: F401
import requests
import yfinance as yf


class Guardian:
    def __init__(self):
        print("🛡️ Inicializando El Guardián (Sentinel System)...")

    def obtener_sentimiento_social(self):
        """
        API Gratuita de Sentimiento (Alternative.me).
        Detecta el 'Ruido' emocional del mercado.
        """
        try:
            url = "https://api.alternative.me/fng/"
            r = requests.get(url, timeout=5)
            data = r.json()
            score = int(data["data"][0]["value"])
            return score
        except Exception:
            return 50  # Valor neutro por defecto

    def analizar_macro(self, connection, exchange_obj, symbol, crypto_data):
        """
        Análisis 360: Macro, Técnico, Social, Microestructura y Ballenas.
        """
        # --- 1. FILTRO MACRO GLOBAL (VIX & DXY) ---
        try:
            macro = yf.download(
                ["^VIX", "DX-Y.NYB"], period="5d", interval="1d", progress=False
            )
            if isinstance(macro.columns, pd.MultiIndex):
                vix = macro["Close"]["^VIX"].iloc[-1]
                dxy = macro["Close"]["DX-Y.NYB"].iloc[-1]
            else:
                vix = macro.iloc[-1, 0]
                dxy = macro.iloc[-1, 1]
                
            # Reglas de Acero
            if vix > 32: return False, f"⛔ VIX Pánico ({vix:.1f}). Apagando compras."
            if dxy > 107.5: return False, f"⛔ Dólar Parabólico ({dxy:.1f}). Liquidez seca."
            
        except Exception:
            pass # Si falla Yahoo, seguimos (Fail-Open)

        # --- 2. SENTIMIENTO SOCIAL (RUIDO) ---
        fng = self.obtener_sentimiento_social()
        
        # Teoría de la Opinión Contraria:
        # Si F&G > 85 (Euforia Extrema) -> Todos son avariciosos -> Vende/Espera.
        if fng > 88:
            return False, f"⛔ Euforia Social Irracional (F&G: {fng}). Riesgo de Crash."

        # --- 3. MICROESTRUCTURA (ORDER BOOK IMBALANCE) ---
        imbalance = connection.get_order_book_imbalance(exchange_obj, symbol)
        
        # Imbalance negativo fuerte (< -0.4) significa muchos vendedores bloqueando el precio
        if imbalance < -0.5:
            return False, f"⛔ Muro de Venta detectado (Imbalance: {imbalance:.2f})."

        # --- 4. WHALE WATCHER (ON-CHAIN SIMULADO) ---
        # Si hay ballenas operando, aumenta el riesgo de volatilidad
        hay_ballenas = connection.check_whale_trades(exchange_obj, symbol)
        if hay_ballenas and fng > 70:
             # Ballenas moviéndose en un mercado eufórico suele significar distribución (Venta)
             return False, "⛔ Ballenas activas en zona de euforia (Posible Dump)."

        # --- 5. TENDENCIA TÉCNICA (SMA 200) ---
        df = pd.DataFrame(crypto_data, columns=["ts", "o", "h", "l", "close", "v"])
        if len(df) > 200:
            sma200 = df.ta.sma(close=df["close"], length=200).iloc[-1]
            precio = df["close"].iloc[-1]
            
            # Solo prohibimos compras si estamos BAJO la media Y el sentimiento es malo
            if precio < sma200 and fng < 40:
                # A menos que el imbalance sea muy positivo (Suelo encontrado)
                if imbalance < 0.2:
                    return False, "⛔ Tendencia Bajista y sin presión de compra."

        # Si pasamos todo esto...
        msg = f"✅ Macro OK. (F&G: {fng} | Imbalance: {imbalance:.2f})"
        return True, msg