import ccxt

# Configura tus llaves de la Testnet
exchange = ccxt.binance(
    {
        "apiKey": "n0La6UfYaxhW2OphtD1Kfd3klqnlask8Uu4zjRiqe7Z4Dvn2ESzTNhKt1hBYSTa0",
        "secret": "tB8njbhaUAOENlAipvXeZNlCcocGm14a8Lzje5nyyc3bLxasXG3lJJaaB187Gmfj",
        "enableRateLimit": True,
        "options": {"defaultType": "spot"},
    }
)
exchange.set_sandbox_mode(True)  # ¡IMPORTANTE! Activa el modo Testnet


def total_cleanup():
    print("🧹 Iniciando limpieza de activos en Testnet...")
    balance = exchange.fetch_balance()

    for asset, amount in balance["total"].items():
        if amount > 0 and asset != "USDT":
            symbol = f"{asset}/USDT"
            try:
                print(f"📦 Vendiendo {amount} de {asset}...")
                # Vendemos todo a precio de mercado
                exchange.create_market_order(symbol, "sell", amount)
                print(f"✅ {asset} liquidado.")
            except Exception as e:
                print(f"⚠️ No se pudo vender {asset}: {e} (posiblemente muy poca cantidad)")

    # Verificación final
    final_bal = exchange.fetch_balance()
    print(f"\n💰 Saldo final en USDT: ${final_bal['total']['USDT']:.2f}")
    print("🚀 Cuenta lista para el Ciclo #1.")


if __name__ == "__main__":
    total_cleanup()
