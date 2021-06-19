import sys
sys.path.append("..")
import config # type: ignore
from strategies.dca import Strategy_DCA # type: ignore
from database import database as mdb # type: ignore
import asyncio

api_key = config.BYBIT_TESTNET_API_KEY
api_secret = config.BYBIT_TESTNET_API_SECRET
symbol_pair = 'ETHUSD'
input_amount = 100
leverage = 5
input_quantity = input_amount * leverage
max_active_positions = 10
strat_id = 'dcamp'
trade_id = 'bybit_auto_2'
instance = 'testnet_1'
entry_side = 'Buy'

run_strat = True
setup_default_tables = False

if (setup_default_tables):
    mdb.create_trigger_values_table('ETH')
    mdb.create_trigger_values_table('BTC')
    # mdb.setup_default_tables()

async def main():

    if run_strat:
        if (symbol_pair == "BTCUSD"):
            symbol = 'BTC'
            key_input = 0
            limit_price_difference = 0.50
            mdb.update_trade_values(trade_id, strat_id, symbol, symbol_pair,  key_input, limit_price_difference, leverage, input_quantity, 'empty', 0, 0, 0)
        elif (symbol_pair == "ETHUSD"):
            symbol = 'ETH'
            key_input = 1
            limit_price_difference = 0.05
            mdb.update_trade_values(trade_id, strat_id, symbol, symbol_pair, key_input, limit_price_difference, leverage, input_quantity, 'empty', 0, 0, 0)
        else:
            print("Invalid Symbol Pair")

        strat = Strategy_DCA(instance, api_key, api_secret, trade_id, strat_id, symbol, symbol_pair, \
            key_input, input_quantity, leverage, limit_price_difference, max_active_positions, entry_side)

        await strat.main()

if __name__ == "__main__":  
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("closed by interrupt")

