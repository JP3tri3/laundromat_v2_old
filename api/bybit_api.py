import sys
sys.path.append("..")
import bybit # type: ignore
from logic.calc import Calc as calc # type: ignore
from time import time, sleep
import asyncio
import time
import pprint
# import random
# import string
import math


class Bybit_Api:

    def __init__(self, api_key, api_secret, symbol, symbol_pair, key_input):
        # TODO: Update client for mainnet: 
        self.client = bybit.bybit(test=True, api_key=api_key, api_secret=api_secret)
        self.symbol = symbol
        self.symbol_pair = symbol_pair
        self.key_input = key_input
        self.interval = 0

        print(f'... Bybit_API initialized : symbol: {self.symbol_pair} ...')

    def get_key_input(self):
        return self.key_input

    def wallet_result(self):
        my_wallet = self.client.Wallet.Wallet_getBalance(
            coin=self.symbol).result()
        wallet_info = my_wallet[0]['result'][self.symbol]
        return wallet_info

    def wallet_balance(self):
        wallet_result = self.wallet_result()
        balance = wallet_result['available_balance']
        return(balance)

    def wallet_realized_p_l(self):
        wallet_result = self.wallet_result()
        balance_p_l = wallet_result['realised_pnl']
        return(balance_p_l)

    def wallet_equity(self):
        wallet_result = self.wallet_result()
        equity = wallet_result['equity']
        return(equity)

#symbol:

    def symbol_info_result(self):
        info = self.client.Market.Market_symbolInfo().result()
        return(info[0]['result'])

    def symbol_info_keys(self):
        infoKeys = self.symbol_info_result()
        return infoKeys[self.key_input]

#price:

    def price_info(self):
        keys = self.symbol_info_result()
        key_info = keys[self.key_input]

        last_price = key_info['last_price']
        mark_price = key_info['mark_price']
        ask_price = key_info['ask_price']
        index_price = key_info['index_price']

        print("")
        print("Last Price: " + self.symbol_pair + " " + last_price)
        print("Mark Price: " + self.symbol_pair + " " + mark_price)
        print("Ask Price: " + self.symbol_pair + " " + ask_price)
        print("Index Price: " + self.symbol_pair + " " + index_price)
        print("")

    def last_price(self):
        keys = self.symbol_info_result()
        return float(keys[self.key_input]['last_price'])

#order:

    def get_orders(self):
        active_order = self.client.Order.Order_query(symbol=self.symbol_pair).result()
        order = active_order[0]['result']
        return(order)

    def get_order_id(self):
        try:
            order = self.get_orders()
            if (order == []):
                print('no order ids available')
                return []
            else:
                order_id = order[0]['order_id']
                return order_id
        except Exception as e:
            print("an exception occured - {}".format(e))
            return False

    def cancel_order(self, order_id):
        print("Cancelling Order: " + order_id)
        self.client.Order.Order_cancel(symbol=self.symbol_pair, order_id=order_id).result()

    def cancel_all_orders(self):
        # Cancel all API call: doesn't seem to be working / double check the following:
        # self.client.Order.Order_cancelAll(symbol=self.symbol).result()
        print("Cancelling All Orders...")
        orders_list = self.get_orders()
        for x in range(len(orders_list)):
            order_id = orders_list[x]['order_id']
            self.cancel_order(order_id)

    def get_orders_info(self):
        active_orders = self.get_orders()
        kv_list = []
        index = 0

        try:
            if(active_orders == []) or (active_orders == None):
                kv_list = []
            else:
                for x in range(len(active_orders)):
                    order = active_orders[x]
                    index +=1
                    kv_list.append({'side': order['side'], 'price':  float(order['price']), 'input_quantity': order['qty'], 'order_id': order['order_id']})
            return kv_list    
        except Exception as e:
            print("an exception occured - {}".format(e))

#trade records:

    def get_trade_record(self):
        epoch_string = str(int(time.time()) - 100)
        trade_records = self.client.Execution.Execution_getTrades(symbol=self.symbol_pair, start_time=epoch_string).result()
        trade_records = trade_records[0]['result']['trade_list']
        return trade_records


    def get_last_trade_price_record(self, order_link_id):
        #TODO: Note: Last_trade_price in record may be different than actual w/ Market
        try:
            trade_records = self.get_trade_record()
            trade_price = 0.0
            num_orders = 0

            if (trade_records == None):
                return self.last_price()
            else:
                for record in trade_records:
                    if record['order_link_id'] == order_link_id:
                        trade_price += float(record['exec_price'])
                        num_orders += 1

                if (trade_price == 0):
                    return trade_price
                else:
                    return math.ceil(trade_price / num_orders)
        except Exception as e:
            print("an exception occured - {}".format(e))

#orders:
    def place_order(self, price, order_type, side, input_quantity, stop_loss, reduce_only, link_id):
        try:
            if link_id:
                order_link_id = self.generate_order_link_id(link_id)
            else:
                order_link_id = link_id

            price = round(price, 1)

            if(order_type == 'Market'):
                print(f"sending order {price} - {side} {input_quantity} {self.symbol_pair} {order_type} {stop_loss}")
                self.client.Order.Order_new(side=side, symbol=self.symbol_pair, order_type="Market",
                                            qty=input_quantity, time_in_force='PostOnly', stop_loss=str(stop_loss), reduce_only=reduce_only, order_link_id=order_link_id).result()
            elif(order_type == "Limit"):
                print(f"sending order {price} - {side} {input_quantity} {self.symbol_pair} {order_type} {stop_loss}")
                self.client.Order.Order_new(side=side, symbol=self.symbol_pair, order_type="Limit",
                                            qty=input_quantity, price=price, time_in_force='PostOnly', stop_loss=str(stop_loss), reduce_only=reduce_only, order_link_id=order_link_id).result()
            else:
                print("Invalid Order")
        except Exception as e:
            print("an exception occured - {}".format(e))
            return False
        return order_link_id

    #TODO: Futureproof
    def generate_order_link_id(self, identifier):
        epoch_string = str(time.time())
        order_link_id = identifier + epoch_string
        # letters = string.ascii_lowercase
        # order_link_id = ( ''.join(random.choice(letters) for i in range(30)) )
        return order_link_id

    def create_limit_order(self, price, side, input_quantity, stop_loss, reduce_only, link_id):
        # new_num_orders = len(self.get_orders()) + 1
        print('\ncreating limit order: ')
        self.place_order(price, 'Limit', side, input_quantity, stop_loss, reduce_only, link_id)
        return self.get_order_id()
        # num_orders = len(self.get_orders())
        # if (num_orders == new_num_orders):
        #     print('limit order created successfully: ')
        #     return self.get_order_id()
        # else:
        #     print('limit order not successful')
        #     return 0 

    # force limit with create limit order
    async def force_limit_order(self, side, input_quantity, limit_price_difference, stop_loss, reduce_only, link_id):
        print('')
        print('creating_limit_order in force: ')
        order_id = None
        pos_size = self.get_position_size()
        total_pos_size = (input_quantity + pos_size)
        num_orders = len(self.get_orders()) + 1
        current_price = self.last_price()

        while(total_pos_size != pos_size):
            new_num_orders = len(self.get_orders())
            await asyncio.sleep(0.025)
            if (new_num_orders == num_orders):
                last_price = self.last_price()
                if (last_price != current_price) and (last_price != price):
                    print(f"last_price: {last_price}")
                    print(f"current_price: {current_price}")
                    print(f"price: {price}")
                    current_price = last_price
                    price = calc().calc_limit_price_difference(side, last_price, limit_price_difference)
                    self.change_order_price_size(price, input_quantity, order_id)
                    print(f"Order Price Updated: {price}\n")
            else:
                current_price = self.last_price()
                price = calc().calc_limit_price_difference(side, current_price, limit_price_difference)
                print('force limit order id not available')
                pos_size = self.get_position_size()
                input_quantity = total_pos_size - pos_size
                print(f'input_quantity: {input_quantity}')
                print(f'pos_size: {pos_size}')
                print(f'total_pos_size: {total_pos_size}')
                order_id = self.create_limit_order(price, side, input_quantity, stop_loss, reduce_only, link_id)
                print(f'force_limit_order_id: {order_id}')
        print('Force Limit Order Successful')

    def change_order_price(self, price, order_link_id):
        try:
            print(f"changing order price: {order_link_id} - {price}")
            order = self.client.Order.Order_replace(symbol=self.symbol_pair, order_link_id=order_link_id, p_r_price=str(price)).result()
        except Exception as e:
            print("an exception occured - {}".format(e))
            return False
        return order

    def change_order_size(self, input_quantity, order_link_id):
        input_quantity = int(input_quantity)
        try:
            print(f"changing order size: {order_link_id} - {input_quantity}")
            order = self.client.Order.Order_replace(symbol=self.symbol_pair, order_link_id=order_link_id, p_r_qty=str(input_quantity)).result()
        except Exception as e:
            print("an exception occured - {}".format(e))
            return False
        return order

    def change_order_price_size(self, price, input_quantity, order_id):
        input_quantity = int(input_quantity)
        try:
            print(f"changing order {order_id} - {price} {input_quantity}")
            order = self.client.Order.Order_replace(symbol=self.symbol_pair, order_id=order_id, p_r_qty=str(input_quantity), p_r_price=str(price)).result()
        except Exception as e:
            print("an exception occured - {}".format(e))
            return False
        return order

#position:
    def get_position_result(self):
        try:
            position_result = self.client.Positions.Positions_myPosition(symbol=self.symbol_pair).result()
            position_result = position_result[0]['result']
            if 'data' not in position_result:
                return position_result
            else:
                return position_result[0]['data']

# TODO: Check this again 'data' JSON change:
# ({'ret_code': 0, 'ret_msg': 'OK', 'ext_code': '', 'ext_info': '', 'result': {'id': 0, 'position_idx': 0, 'mode': 0, 'user_id': 141887, 'risk_id': 1, 'symbol': 'BTCUSD', 'side': 'None', 'size': 0, 'position_value': '0', 'entry_price': '0', 'is_isolated': True, 'auto_add_margin': 0, 'leverage': '5', 'effective_leverage': '5', 'position_margin': '0', 'liq_price': '0', 'bust_price': '0', 'occ_closing_fee': '0', 'occ_funding_fee': '0', 'take_profit': '0', 'stop_loss': '0', 'trailing_stop': '0', 'position_status': 'Normal', 'deleverage_indicator': 0, 'oc_calc_data': '{"blq":0,"slq":0,"bmp":0,"smp":0,"bv2c":0.20165,"sv2c":0.20135}', 'order_margin': '0', 'wallet_balance': '0.00999328', 'realised_pnl': '0', 'unrealised_pnl': 0, 'cum_realised_pnl': '-0.00846891', 'cross_seq': 3187902013, 'position_seq': 0, 'created_at': '2021-02-08T22:11:27.331382323Z', 'updated_at': '2021-05-15T01:43:53.80825405Z', 'tp_sl_mode': 'Full'}, 'time_now': '1621043034.064140', 'rate_limit_status': 119, 'rate_limit_reset_ms': 1621043034061, 'rate_limit': 120}, <bravado.requests_client.RequestsResponseAdapter object at 0x000002509C534BB0>)

        except Exception as e:
            print("an exception occured in get_position_result - {}".format(e))
            #TODO: doublecheck / fix 
            self.get_position_result()

    def get_position_side(self):
        try:
            position_result = self.get_position_result()
            return position_result['side']
        except Exception as e:
            print("an exception occured - {}".format(e))   
            return 'null'     

    def get_position_size(self):
        try:
            position_result = self.get_position_result()
            position_size = position_result['size']
            return position_size
        except Exception as e:
            print("an exception occured - {}".format(e))

    def get_position_value(self):
        position_result = self.get_position_result()
        return position_result['position_value']

    def get_active_position_entry_price(self):
        position_result = self.get_position_result()
        entry_price = position_result['entry_price']
        if (entry_price == None):
            return 0
        else:
            return float(entry_price)

    def update_main_pos_exit_order(self, profit_percent, order_id, entry_side):
        print('')
        print('update_main_pos_exit_order')
        try:
            if self.get_position_size() == 0:
                print('position closed')
            else:
                if (entry_side == 'Buy'):
                    long_short = 'long'
                else:
                    long_short = 'short'

                main_pos_entry = float(self.get_active_position_entry_price())
                main_pos_quantity = self.get_position_size()
                price = calc().calc_percent_difference(long_short, 'exit', main_pos_entry, profit_percent)
                self.change_order_price_size(price, main_pos_quantity, order_id)
        except Exception as e:
            print("an exception occured - {}".format(e))
            return False

#Leverage
 
    def get_position_leverage(self):
        position = self.get_position_result()
        return position['leverage']

    def set_leverage(self, leverage):
        set_leverage = self.client.Positions.Positions_saveLeverage(symbol=self.symbol_pair, leverage=str(leverage)).result()
        print("Leverage set to: " + str(leverage))
        return set_leverage    
#stop_loss

    def change_stop_loss(self, sl_amount):
        self.client.Positions.Positions_tradingStop(
            symbol=self.symbol_pair, stop_loss=str(sl_amount)).result()
        print("")
        print("Changed stop Loss to: " + str(sl_amount))

#Profit & Loss
    def closed_profit_loss(self):
        records = self.client.Positions.Positions_closePnlRecords(symbol=self.symbol_pair).result()
        return records[0]['result']['data']

    def closed_profit_lossQuantity(self, index):
        record_result = self.closed_profit_loss()
        return record_result[index]['closed_size']

    def lastProfitLoss(self, index):
        record_result = self.closed_profit_loss()
        return record_result[index]['closed_pnl']

    def last_exit_price(self, index):
        record_result = self.closed_profit_loss()
        return record_result[index]['avg_exit_price']

    def last_entry_price(self, index):
        record_result = self.closed_profit_loss()
        return record_result[index]['avg_entry_price']

    #Calc Entry_Exit

    def calc_last_gain(self, index, input_quantity):
        total = self.lastProfitLoss(index)
        exit_price = float(self.get_exit_price(input_quantity))
        return round(float('%.10f' % total) * exit_price, 3)

    def calc_total_gain(self, input_quantity):
        total = 0
        index = 0
        total_quantity = 0
        flag = False

        while(flag == False):
            total_quantity += self.closed_profit_lossQuantity(index)
            total += self.calc_last_gain(index, input_quantity)

            if total_quantity < input_quantity:
                index += 1
            else:
                flag = True

        return total

    def calc_total_coin(self, input_quantity):
        index = 0
        total_quantity = 0
        total = 0.0
        flag = False

        while(flag == False):
            amount = float(self.lastProfitLoss(index))
            total += amount
            total_quantity += self.closed_profit_lossQuantity(index)

            if total_quantity < input_quantity:
                index += 1
            else:
                flag = True

        return ('%.10f' % total)

    def get_entry_price(self, input_quantity):
        index = 0
        divisible = 1
        last_entry_price = self.last_entry_price(index)
        entry_price = 0
        total_quantity = 0

        flag = False

        while(flag == False):
            total_quantity += self.closed_profit_lossQuantity(index)
            entry_price += last_entry_price

            if total_quantity < input_quantity:
                index += 1
                divisible += 1
                print("Index = " + str(index))
            else:
                flag = True

        if (index == 0):
            return entry_price
        else:
            return (entry_price / divisible)


    def get_exit_price(self, input_quantity):
        index = 0
        divisible = 1
        last_exit_price = self.last_exit_price(index)
        exit_price = 0
        total_quantity = 0
        flag = False

        while(flag == False):
            total_quantity += self.closed_profit_lossQuantity(index)
            exit_price += last_exit_price

            if total_quantity < input_quantity:
                index += 1
                divisible += 1
                print("Index = " + str(index))
            else:
                flag = True
        
        if (index == 0):
            return exit_price
        else:
            return (exit_price / divisible)



