import sys
sys.path.append("..")
import bybit
from logic.calc import Calc as calc
from time import time, sleep
import asyncio
import time
# import random
# import string


class Bybit_Api:

    def __init__(self, api_key, api_secret, symbol, symbol_pair, key_input):
        self.client = bybit.bybit(test=True, api_key=api_key, api_secret=api_secret)
        self.symbol = symbol
        self.symbol_pair = symbol_pair
        self.key_input = key_input
        self.interval = 0

        print('... Bybit_API initialized ...')

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
        self.client.Order.Order_cancel(symbol="BTCUSD", order_id=order_id).result()

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

#orders:
    def place_order(self, price, order_type, side, input_quantity, stop_loss, reduce_only, link_id):
        try:
            if link_id:
                order_link_id = self.generate_order_link_id(link_id)
            else:
                order_link_id = link_id

            if(order_type == 'Market'):
                print(f"sending order {price} - {side} {input_quantity} {self.symbol_pair} {order_type} {stop_loss}")
                order = self.client.Order.Order_new(side=side, symbol=self.symbol_pair, order_type="Market",
                                            qty=input_quantity, time_in_force='PostOnly', stop_loss=str(stop_loss), reduce_only=reduce_only, order_link_id=order_link_id).result()
            elif(order_type == "Limit"):
                print(f"sending order {price} - {side} {input_quantity} {self.symbol_pair} {order_type} {stop_loss}")
                order = self.client.Order.Order_new(side=side, symbol=self.symbol_pair, order_type="Limit",
                                            qty=input_quantity, price=price, time_in_force='PostOnly', stop_loss=str(stop_loss), reduce_only=reduce_only, order_link_id=order_link_id).result()
            else:
                print("Invalid Order")
        except Exception as e:
            print("an exception occured - {}".format(e))
            return False
        return order

    #TODO: Futureproof
    def generate_order_link_id(self, identifier):
        epoch_string = str(time.time())
        order_link_id = identifier + '-' + epoch_string
        # letters = string.ascii_lowercase
        # order_link_id = ( ''.join(random.choice(letters) for i in range(30)) )
        return order_link_id

    #create multiple limit orders at perfect difference
    async def create_multiple_limit_orders(self, num_of_orders, starting_point_price, long_short, side, input_quantity, profit_percent, reduce_only, link_id):
        x = 0
        if (side == 'Buy'):
            entry_exit = 'entry'
        else:
            entry_exit = 'exit'
        price = starting_point_price
        while (x < num_of_orders):
            price = calc().calc_percent_difference(long_short, entry_exit, price, profit_percent)
            print(f'price: {price}')
            self.place_order(price, 'Limit', side, input_quantity, 0, reduce_only, link_id)
            x += 1
            await asyncio.sleep(self.interval)

    def create_limit_order(self, price, side, input_quantity, stop_loss, reduce_only, link_id):
        print(f'create_limit_order price: {price}')
        # new_num_orders = len(self.get_orders()) + 1
        print('')
        print('creating limit order: ')
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
        position_result = self.client.Positions.Positions_myPosition(symbol=self.symbol_pair).result()
        return position_result[0]['result']

    def get_position_side(self):
        try:
            position_result = self.get_position_result()
            return position_result['side']
        except Exception as e:
            print("an exception occured - {}".format(e))   
            return 'null'     

    def get_position_size(self):
        position_result = self.get_position_result()
        return position_result['size']

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