import os
import sys
import time

import ccxt
import yfinance as yf


class DualExchangeManager:
    def __init__(self):
        print("🔌 Inicializando Sistema de Doble Exchange...")

        # 1. Configurar GENERADOR
        self.gen = self._connect(
            os.getenv("GEN_EXCHANGE_ID", "binance"),
            os.getenv("GEN_API_KEY"),
            os.getenv("GEN_SECRET_KEY"),
        )

        # 2. Configurar REFUGIO
        self.safe = self._connect(
            os.getenv("XMR_EXCHANGE_ID", "kucoin"),
            os.getenv("XMR_API_KEY"),
            os.getenv("XMR_SECRET_KEY"),
            os.getenv("XMR_PASSWORD"),
        )

    def _connect(self, exchange_id, key, secret, password=None):
        if not key or not secret:
            print(f"❌ Falta API Key para {exchange_id}")
            sys.exit(1)

        if not hasattr(ccxt, exchange_id):
            print(f"❌ Exchange '{exchange_id}' no soportado por CCXT.")
            sys.exit(1)

        exchange_class = getattr(ccxt, exchange_id)
        config = {
            "apiKey": key,
            "secret": secret,
            "enableRateLimit": True,
            "options": {"defaultType": "spot", "adjustForTimeDifference": True},
        }
        if password:
            config["password"] = password

        return exchange_class(config)

    def validate_symbol(self, exchange_obj, symbol):
        try:
            if not exchange_obj.markets:
                exchange_obj.load_markets()
            return symbol in exchange_obj.markets
        except Exception:
            return False

    def get_data(self, exchange_obj, symbol, limit=100):
        for _ in range(3):
            try:
                bars = exchange_obj.fetch_ohlcv(symbol, "1h", limit=limit)
                if bars:
                    return bars
            except Exception:
                time.sleep(2)
        return None

    def get_balance(self, exchange_obj):
        try:
            return exchange_obj.fetch_balance()
        except Exception:
            return None

    def execute_order(self, exchange_obj, symbol, side, amount):
        try:
            amount = exchange_obj.amount_to_precision(symbol, amount)
            return exchange_obj.create_market_order(symbol, side, amount)
        except Exception as e:
            print(f"❌ Error Orden ({symbol}): {e}")
            return None

    # --- NUEVAS HERRAMIENTAS AVANZADAS ---

    def get_order_book_imbalance(self, exchange_obj, symbol):
        """
        Calcula el desequilibrio entre compradores y vendedores.
        Retorna: Ratio (-1.0 a 1.0). Positivo = Presión de Compra.
        """
        try:
            # Analizamos los 50 niveles más cercanos
            book = exchange_obj.fetch_order_book(symbol, limit=50)
            if not book["asks"] or not book["bids"]:
                return 0

            # Sumar volumen de bids (compras) vs asks (ventas)
            vol_bids = sum([bid[1] for bid in book["bids"]])
            vol_asks = sum([ask[1] for ask in book["asks"]])
            
            total_vol = vol_bids + vol_asks
            if total_vol == 0: return 0

            # Fórmula de Imbalance: (Bids - Asks) / Total
            imbalance = (vol_bids - vol_asks) / total_vol
            return imbalance
        except Exception:
            return 0

    def check_whale_trades(self, exchange_obj, symbol, threshold_usd=50000):
        """
        Busca 'Elephant Trades' (operaciones masivas) en los últimos minutos.
        Retorna: True si hay ballenas activas moviendo el precio.
        """
        try:
            # Descargar últimas operaciones públicas
            trades = exchange_obj.fetch_trades(symbol, limit=100)
            if not trades: return False

            # Buscar si alguna operación supera el umbral (ej. $50k de golpe)
            for trade in trades:
                # trade['cost'] es precio * cantidad
                if trade['cost'] and trade['cost'] > threshold_usd:
                    side = trade['side'].upper()
                    print(f"   🐋 BALLENA DETECTADA en {symbol}: {side} de ${trade['cost']:.0f}")
                    return True
            return False
        except Exception:
            return False

    def bridge_transfer(self, amount, target_address, network="TRX"):
        try:
            bal = self.get_balance(self.gen)
            free = bal.get("USDT", {}).get("free", 0)
            if amount > (free - 1.5):
                amount = free - 1.5

            if amount < 10:
                return None

            print(f"   🌉 PUENTE: Enviando {amount:.2f} USDT -> Refugio")
            return self.gen.withdraw(
                "USDT", amount, target_address, params={"network": network}
            )
        except Exception as e:
            print(f"   ❌ Error Puente: {e}")
            return None

    def withdraw_to_trezor(self, currency, amount, address):
        try:
            if amount <= 0:
                return None
            print(f"   ❄️ BÓVEDA: Retirando {amount} {currency} a Trezor...")
            return self.safe.withdraw(currency, amount, address)
        except Exception as e:
            print(f"   ❌ Error Bóveda: {e}")
            return None

    def get_sp500_data(self):
        try:
            spx = yf.download("^GSPC", period="7d", interval="1h", progress=False)
            if spx.empty:
                return None
            return spx["Close"] if "Close" in spx.columns else spx.iloc[:, 0]
        except Exception:
            return None