import sys
sys.path.append("..")
# import auto
import database.sql_connector as conn
from logic.calc import Calc as calc

class Database:

    print('... Database initialized ...')

    # # trades table:

    def update_trade_values(self, trade_id, strat_id, symbol, symbol_pair, key_input, limit_price_difference, leverage, input_quantity, side, stop_loss, percent_gain, trade_record_id):
        return conn.update_trade_values(trade_id, strat_id, symbol, symbol_pair, key_input, limit_price_difference, leverage, input_quantity, side, stop_loss, percent_gain, trade_record_id)

    def get_symbol(self, trade_id):
        return conn.viewDbValue('trades', trade_id, 'symbol')

    def get_key_input(self, trade_id):
        return conn.viewDbValue('trades', trade_id, 'key_input')

    def get_symbol_pair(self, trade_id):
        return conn.viewDbValue('trades', trade_id, 'symbol_pair')

    def get_limit_price_difference(self, trade_id):
        return conn.viewDbValue('trades', trade_id, 'limit_price_difference')

    def get_side(self, trade_id):
        return conn.viewDbValue('trades', trade_id, 'side')

    def set_side(self, trade_id, side):
        return conn.updateTableValue('trades', trade_id, 'side', side)

    def set_stop_loss(self, trade_id, stop_loss):
        return conn.updateTableValue('trades', trade_id, 'stop_loss', stop_loss)

    def get_input_quantity(self, trade_id):
        return conn.viewDbValue('trades', trade_id, 'input_quantity')

    def set_input_quantity(self, trade_id, data_input):
        conn.updateTableValue('trades', trade_id, 'input_quantity', data_input)

    def get_leverage(self, trade_id):
        return conn.viewDbValue('trades', trade_id, 'leverage')

    def set_trade_record_id(self, trade_id, trade_record_id):
        conn.updateTableValue('trades', trade_id, 'trade_record_id', trade_record_id)

    # # strategy table:

    def update_strat_values(self, strat_id, wt1, wt2, last_candle_high, last_candle_low, last_candle_vwap):
        return conn.update_strat_values(strat_id, wt1, wt2, last_candle_high, last_candle_low, last_candle_vwap)

    def get_wt1(self, strat_id):
        return conn.viewDbValue('strategy', strat_id, 'wt1')    

    def get_wt2(self, strat_id):
        return conn.viewDbValue('strategy', strat_id, 'wt2')       

    def get_last_candle_vwap(self, strat_id):
        return conn.viewDbValue('strategy', strat_id, 'last_candle_vwap')       

    def get_last_candle_low(self, strat_id):
        return conn.viewDbValue('strategy', strat_id, 'last_candle_low')  

    def get_last_candle_high(self, strat_id):
        return conn.viewDbValue('strategy', strat_id, 'last_candle_high')  

    def get_active_position(self, strat_id):
        return conn.viewDbValue('strategy', strat_id, 'active_position')  

    def set_active_position(self, strat_id, data_input):
        return conn.updateTableValue('strategy', strat_id, 'active_position', data_input)  

    def get_new_trend(self, strat_id):
        return conn.viewDbValue('strategy', strat_id, 'new_trend')  

    def set_new_trend(self, strat_id, data_input):
        return conn.updateTableValue('strategy', strat_id, 'new_trend', data_input)  

    def get_last_trend(self, strat_id):
        return conn.viewDbValue('strategy', strat_id, 'last_trend')  

    def set_last_trend(self, strat_id, data_input):
        return conn.updateTableValue('strategy', strat_id, 'last_trend', data_input)  

    def get_active_trend(self, strat_id):
        return conn.viewDbValue('strategy', strat_id, 'active_trend')  

    def set_active_trend(self, strat_id, data_input):
        return conn.updateTableValue('strategy', strat_id, 'active_trend', data_input)  

    # # trade_records table:

    def get_trade_record_total_dollar_gain(self, trade_record_id):
        return conn.viewDbValue('trade_records', trade_record_id, 'total_p_l_dollar')

    def get_trade_record_total_coin_gain(self, trade_record_id):
        return conn.viewDbValue('trade_records', trade_record_id, 'total_p_l_coin')

    def create_trade_record(self, trade_record_id, trade_id, strat_id, symbol_pair, side, input_quantity, entry_price, exit_price, stop_loss, percent_gain, dollar_gain, coin_gain, total_p_l_dollar, total_p_l_coin):
        return conn.create_trade_record(trade_record_id, trade_id, strat_id, symbol_pair, side, input_quantity, entry_price, exit_price, stop_loss, percent_gain, dollar_gain, coin_gain, total_p_l_dollar, total_p_l_coin, calc().time_stamp())

    def set_entry_price(self, trade_record_id, entry_price_input):
        return conn.updateTableValue('trade_records', trade_record_id, 'entry_price', entry_price_input)

    def get_entry_price(self, trade_record_id):
        return conn.viewDbValue('trade_records', trade_record_id, 'entry_price')

    def delete_trade_records(self, flag):
        if (flag == True):
            print("Deleting Trade Records...")
            return conn.delete_trade_records()
        else:
            print("Maintaining Trade Records...")
            return 0

    def get_trade_record_value(self, trade_record_id, trade_id, column_name):
        return conn.view_db_values_multiple('trade_records', trade_record_id, trade_id, column_name)

    # # table dicts:

    def get_trade_values(self, trade_id):
        return conn.get_table_pair('trades', trade_id)

    def get_strat_values(self, table_name, strat_id):
        return conn.get_table_pair(table_name, strat_id)



    # # Clear All Values:

    def clear_all_tables_values(self, flag):
        if(flag == True):
            print("Clearing Trade & Strat Table Values...")
            conn.update_trade_values('bybit_manual', 'empty', 'empty', 'empty', 0, 0, 0, 0, 'empty', 0, 0, 0)
            conn.update_trade_values('bybit_auto_1', 'empty', 'empty', 'empty', 0, 0, 0, 0, 'empty', 0, 0, 0)
            conn.update_strat_values('1_min', 0, 0, 0, 0, 0)
            conn.update_strat_values('9_min', 0, 0, 0, 0, 0)
            conn.update_strat_values('16_min', 0, 0, 0, 0, 0)
            conn.update_strat_values('30_min', 0, 0, 0, 0, 0)
            conn.update_strat_trends('1_min', 'null', 'null', 'null', 'null')
            conn.update_strat_trends('9_min', 'null', 'null', 'null', 'null')
            conn.update_strat_trends('16_min', 'null', 'null', 'null', 'null')
            conn.update_strat_trends('30_min', 'null', 'null', 'null', 'null')
        else:
            print("Maintaining Trade & Strat Table Values...")