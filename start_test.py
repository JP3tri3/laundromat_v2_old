import sys
sys.path.append("..")
import config
from api.bybit_api import Bybit_Api
from logic.trade_logic import Trade_Logic
import asyncio

api_key = config.BYBIT_TESTNET_API_KEY
api_secret = config.BYBIT_TESTNET_API_SECRET
leverage = 5
symbol_pair = 'BTCUSD'
input_quantity = 100 * leverage
strat_id = '1_min'
trade_id = 'bybit_auto_1'
vwap_margin_neg = -10
vwap_margin_pos = 10

async def main():

    if (symbol_pair == "BTCUSD"):
        symbol = 'BTC'
        key_input = 0
        limit_price_difference = 0.50
        # db().update_trade_values(trade_id, strat_id, symbol, symbol_pair,  key_input, limit_price_difference, leverage, input_quantity, 'empty', 0, 0, 0)
    elif (symbol_pair == "ETHUSD"):
        symbol = 'ETH'
        key_input = 1
        limit_price_difference = 0.05
        # db().update_trade_values(trade_id, strat_id, symbol, symbol_pair, key_input, limit_price_difference, leverage, input_quantity, 'empty', 0, 0, 0)
    else:
        print("Invalid Symbol Pair")

    # strat = Strategy_DCA(api_key, api_secret, trade_id, strat_id, symbol, symbol_pair, key_input, input_quantity, leverage, limit_price_difference)
    api = Bybit_Api(api_key, api_secret, symbol, symbol_pair, key_input)
    tl = Trade_Logic(api_key, api_secret, symbol, symbol_pair, key_input, leverage, limit_price_difference)

    #TEST:
    print("!!!!!!")
    print("!!!!!!")
    print("!!!!!!")
    print("!!!!!!")
    print("!!!!!!")
    #Cancel All Orders:

    api.cancel_all_orders()
    tl.close_position_market()

    print('')
    print('Wallet Balance: ')
    print(api.wallet_result())
    print('')

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
