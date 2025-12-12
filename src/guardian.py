import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests

class Guardian:
    def __init__(self):
        print("🛡️ Inicializando El Guardián (Lógica Macro)...")

    def obtener_fear_and_greed(self):
        """
        Regla 4: Teoría de la Opinión Contraria.
        Descarga el índice de Miedo y Codicia de alternative.me
        """
        try:
            url = "https://api.alternative.me/fng/"
            r = requests.get(url, timeout=5)
            data = r.json()
            return int(data['data'][0]['value'])
        except:
            print("⚠️ Error obteniendo Fear & Greed.")
            return 50 # Neutro por defecto

    def analizar_macro(self, symbol_crypto, crypto_data):
        """
        Analiza el estado del mundo y devuelve un 'Permiso de Trading'.
        Retorna: (Puede_Operar: bool, Mensaje: str)
        """
        # 1. Descarga de Datos Macro (VIX, DXY, SP500)
        try:
            # ^VIX = Volatilidad (Miedo)
            # DX-Y.NYB = Índice Dólar (Poder del sistema FIAT)
            tickers = ["^VIX", "DX-Y.NYB"]
            macro = yf.download(tickers, period="1mo", interval="1d", progress=False)
            
            # Últimos valores
            # Manejo seguro de MultiIndex de Yahoo
            try:
                vix_now = macro['Close']['^VIX'].iloc[-1]
                dxy_now = macro['Close']['DX-Y.NYB'].iloc[-1]
            except:
                # Fallback si la estructura cambia
                vix_now = macro.iloc[-1, 0]
                dxy_now = macro.iloc[-1, 1]
                
        except Exception as e:
            return True, "⚠️ Guardián ciego (Sin datos Yahoo). Operando con precaución."

        # 2. Dato de Sentimiento (Fear & Greed)
        fng = self.obtener_fear_and_greed()

        # --- APLICACIÓN DE TUS REGLAS ---

        # REGLA 1: FILTRO DE TENDENCIA (SMA 200)
        # Calculamos la media de 200 sesiones en los datos crypto
        crypto_df = pd.DataFrame(crypto_data, columns=['ts', 'o', 'h', 'l', 'close', 'v'])
        sma200 = crypto_df.ta.sma(close=crypto_df['close'], length=200)
        
        if sma200 is not None:
            precio_actual = crypto_df['close'].iloc[-1]
            sma200_val = sma200.iloc[-1]
            if precio_actual < sma200_val:
                # Estamos en mercado bajista secular.
                # Solo permitimos compras si hay Pánico extremo (Rebote)
                if fng > 20: 
                    return False, f"⛔ Tendencia Bajista (Precio < SMA200). Solo opero rebotes extremos."

        # REGLA 2: CONTROL DE DAÑOS (VIX)
        if vix_now > 25:
            return False, f"⛔ VIX Crítico ({vix_now:.1f}). Miedo extremo en Wall Street."
        
        # REGLA 4: OPINIÓN CONTRARIA (Si todos son codiciosos, vende/no compres)
        if fng > 80:
            return False, f"⛔ Euforia irracional (F&G: {fng}). Peligro de desplome."

        # REGLA 5 & 7: ANÁLISIS DE PODER (DXY - El Dólar)
        # Si el Dólar se dispara, los activos de riesgo (Cripto) sufren.
        # Asumimos que DXY > 106 es "Intervención/Pánico Global"
        if dxy_now > 106:
            return False, f"⛔ El Dólar está destruyendo todo (DXY: {dxy_now:.1f}). Cash is King."

        # REGLA 6: ESTOICISMO (Comprar en pánico)
        if fng < 15:
            return True, "🟢 PÁNICO TOTAL DETECTADO. Aplicando Estoicismo: COMPRAR SANGRE."

        # Si pasamos todos los filtros
        return True, f"✅ Macro Estable (VIX: {vix_now:.1f} | DXY: {dxy_now:.1f} | F&G: {fng})"