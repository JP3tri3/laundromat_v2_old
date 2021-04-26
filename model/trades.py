
import sys
sys.path.append("..")
from database.database import Database as db
import datetime

class Trade:

    def __init__(self, trade_id, trade_record_id):
        self.trade_id = trade_id
        self.trade_record_id = trade_record_id
        print('... Trade initialized ...')

    def commit_trade_record(self, coin_gain, dollar_gain, entry_price, exit_price, percent_gain, input_quantity):

        kv_dict = db().get_trade_values(self.trade_id)

        strat_id = kv_dict['strat_id']
        symbol = kv_dict['symbol']
        symbol_pair = kv_dict['symbol_pair']
        input_quantity = input_quantity
        side = kv_dict['side']
        stop_loss = kv_dict['stop_loss']

        if (self.trade_record_id > 1):
            trade_record_id = (self.trade_record_id - 1)
            previous_dollar_total = float(db().get_trade_record_value(trade_record_id, self.trade_id, 'total_p_l_dollar'))
            previous_coin_total = float(db().get_trade_record_value(trade_record_id, self.trade_id, 'total_p_l_coin'))
            total_p_l_dollar = previous_dollar_total + float(dollar_gain)
            total_p_l_coin = previous_coin_total + float(coin_gain)
        else:
            total_p_l_dollar = dollar_gain
            total_p_l_coin = coin_gain

        db().create_trade_record(self.trade_record_id, self.trade_id, strat_id, symbol_pair, side, \
            input_quantity, entry_price, exit_price, stop_loss, str(percent_gain), str(dollar_gain), \
                str(coin_gain), str(total_p_l_dollar), str(total_p_l_coin))





