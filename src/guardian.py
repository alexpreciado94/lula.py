import pandas as pd
import pandas_ta as ta  # noqa: F401
import requests
import yfinance as yf


class Guardian:
    def __init__(self):
        print("🛡️ Inicializando El Guardián (Filtro Macro)...")

    def obtener_fear_and_greed(self):
        try:
            url = "https://api.alternative.me/fng/"
            r = requests.get(url, timeout=5)
            data = r.json()
            return int(data["data"][0]["value"])
        except Exception:
            return 50  # Valor neutro

    def analizar_macro(self, symbol, crypto_data):
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
        except Exception:
            return True, "⚠️ Sin datos Macro (Yahoo caído)."

        fng = self.obtener_fear_and_greed()

        # Reglas
        if vix > 30:
            return False, f"⛔ VIX Crítico ({vix:.1f})."
        if dxy > 107:
            return False, f"⛔ Dólar demasiado fuerte ({dxy:.1f})."

        df = pd.DataFrame(crypto_data, columns=["ts", "o", "h", "l", "close", "v"])
        if len(df) > 200:
            sma200 = df.ta.sma(close=df["close"], length=200).iloc[-1]
            precio = df["close"].iloc[-1]
            if precio < sma200 and fng > 25:
                return False, "⛔ Tendencia Bajista (Precio < SMA200)."

        if fng > 85:
            return False, f"⛔ Euforia Extrema (F&G: {fng})."

        return True, "✅ Mercado Estable."