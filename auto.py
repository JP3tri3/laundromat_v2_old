import sys
sys.path.append("..")
from database import config
from strategies.dca import Strategy_DCA
from database.database import Database as db
import asyncio

api_key = config.BYBIT_TESTNET_API_KEY
api_secret = config.BYBIT_TESTNET_API_SECRET
leverage = 5
symbol_pair = 'BTCUSD'
input_quantity = 100 * leverage
max_active_positions = 10
strat_id = '1_min'
trade_id = 'bybit_auto_1'
entry_side = 'Buy'
vwap_margin_neg = -10
vwap_margin_pos = 10

async def main():

    #input true to clear:
    # db().clear_all_tables_values(True)
    db().delete_trade_records(True)

    if (symbol_pair == "BTCUSD"):
        symbol = 'BTC'
        key_input = 0
        limit_price_difference = 0.50
        db().update_trade_values(trade_id, strat_id, symbol, symbol_pair,  key_input, limit_price_difference, leverage, input_quantity, 'empty', 0, 0, 0)
    elif (symbol_pair == "ETHUSD"):
        symbol = 'ETH'
        key_input = 1
        limit_price_difference = 0.05
        db().update_trade_values(trade_id, strat_id, symbol, symbol_pair, key_input, limit_price_difference, leverage, input_quantity, 'empty', 0, 0, 0)
    else:
        print("Invalid Symbol Pair")

    strat = Strategy_DCA(api_key, api_secret, trade_id, strat_id, symbol, symbol_pair, \
        key_input, input_quantity, leverage, limit_price_difference, max_active_positions, entry_side)

    await strat.main()


if __name__ == "__main__":  
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("closed by interrupt")
        loop.close()

