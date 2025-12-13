import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests

class Guardian:
    def __init__(self):
        print("🛡️ Inicializando El Guardián (Filtro Macro)...")

    def obtener_fear_and_greed(self):
        """Consulta el índice de Miedo y Codicia (0-100)"""
        try:
            url = "https://api.alternative.me/fng/"
            r = requests.get(url, timeout=5)
            data = r.json()
            return int(data['data'][0]['value'])
        except:
            return 50 # Valor neutro si falla la API

    def analizar_macro(self, symbol, crypto_data):
        """
        Devuelve: (True/False, "Razón")
        """
        # 1. DATOS MACRO (VIX y DXY)
        try:
            # Bajamos datos recientes
            macro = yf.download(["^VIX", "DX-Y.NYB"], period="5d", interval="1d", progress=False)
            
            # Manejo de índices de Yahoo
            if isinstance(macro.columns, pd.MultiIndex):
                vix = macro['Close']['^VIX'].iloc[-1]
                dxy = macro['Close']['DX-Y.NYB'].iloc[-1]
            else:
                # Fallback simple
                vix = macro.iloc[-1, 0] 
                dxy = macro.iloc[-1, 1]
        except:
            # Si falla Yahoo, permitimos operar pero con aviso (Fail-Open)
            return True, "⚠️ Sin datos Macro (Yahoo caído)."

        # 2. SENTIMIENTO
        fng = self.obtener_fear_and_greed()

        # --- REGLAS DEL GUARDIÁN ---

        # A) VIX (Índice del Miedo): Si > 30, el mercado está roto.
        if vix > 30:
            return False, f"⛔ VIX Crítico ({vix:.1f}). Riesgo de crash."

        # B) DXY (Dólar): Si el dólar está parabólico (>107), cripto sufre.
        if dxy > 107:
            return False, f"⛔ Dólar demasiado fuerte ({dxy:.1f})."

        # C) TENDENCIA (SMA 200)
        # Convertimos los datos de Kraken a DataFrame para calcular la media
        df = pd.DataFrame(crypto_data, columns=['ts', 'o', 'h', 'l', 'close', 'v'])
        if len(df) > 200:
            sma200 = df.ta.sma(close=df['close'], length=200).iloc[-1]
            precio = df['close'].iloc[-1]
            
            # Si estamos debajo de la media de 200, solo compramos si hay pánico extremo (Rebote)
            if precio < sma200 and fng > 25:
                return False, f"⛔ Tendencia Bajista (Precio < SMA200)."

        # D) CONTRARIAN (Si todos son codiciosos, cuidado)
        if fng > 85:
            return False, f"⛔ Euforia Extrema (F&G: {fng}). Esperando corrección."

        return True, "✅ Mercado Estable."