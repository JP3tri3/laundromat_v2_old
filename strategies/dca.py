import sys
sys.path.append("..")
from logic.trade_logic import Trade_Logic
from logic.stop_loss import Stop_Loss
from logic.calc import Calc as calc
from api.bybit_api import Bybit_Api
from api.bybit_ws import Bybit_WS
from database.database import Database as db
from model.trades import Trade
import time
from strategies import dca_logic
import asyncio
import pprint

class Strategy_DCA:

    def __init__(self, api_key, api_secret, trade_id, strat_id, symbol, symbol_pair, key_input, \
        input_quantity, leverage, limit_price_difference, max_active_positions, entry_side):
        self.trade_id = trade_id
        self.strat_id = strat_id
        self.input_quantity = input_quantity
        self.max_active_positions = max_active_positions
        self.leverage = leverage
        self.key_input = key_input
        self.trade_record_id = 0
        self.limit_price_difference = limit_price_difference
        self.trade_record_id = 0
        self.entry_side = entry_side

        if (entry_side == 'Buy'):
            self.exit_side = 'Sell'
        else:
            self.exit_side = 'Buy'

        self.tl = Trade_Logic(api_key, api_secret, symbol, symbol_pair, key_input, leverage, \
            limit_price_difference)
        self.api = Bybit_Api(api_key, api_secret, symbol, symbol_pair, self.key_input)
        self.ws = Bybit_WS(api_key, api_secret, symbol_pair, True)

        self.api.set_leverage(self.leverage)
        
        self.orders_list = []
        print('... Strategy_DCA initialized ...')


    async def main(self):
        # # orders_list = []
        ping_timer = asyncio.create_task(self.ws.ping(0.5, 15))
        start_dca_multi_position = asyncio.create_task(self.dca_multi_position())
        # # # execution = asyncio.create_task(self.ws.get_execution())
        # # order_status_test = asyncio.create_task(self.ws.update_orders_list(1, self.orders_list, 10, 0.5, 0.2))

        await ping_timer
        await start_dca_multi_position

        # while True:
        #     await asyncio.sleep(2)
        #     print(pprint.pprint(self.api.get_position_result()))
 


    # async def test_1(self):
    #     pos_size = None
        

        # while True:
 

    #Create Trade Record

    #TODO: Add Trade Name
    async def create_trade_record(self, closed_trade):
        global trade_record_id

        self.trade_record_id = self.trade_record_id + 1
        print('trade_record_id: ' + str(self.trade_record_id))

        print('\ncreating trade record: ')
        print(closed_trade)
        trade = Trade(self.trade_id, self.trade_record_id)
        profit_percent = closed_trade['profit_percent']
        exit_price = closed_trade['price']
        entry_price = exit_price * (1 - profit_percent)
        input_quantity = closed_trade['input_quantity']
        current_last_price = self.api.last_price()
        dollar_gain = input_quantity * (1 - profit_percent)
        coin_gain = self.api.last_price() / dollar_gain
        await asyncio.sleep(0)

        trade.commit_trade_record(coin_gain, dollar_gain, entry_price, exit_price, profit_percent, \
            input_quantity)


    async def dca_multi_position(self):
        global orders_list
        #Set Trade Values
        total_secondary_orders_1 = 4 - 1
        total_secondary_orders_2 = 2
        profit_percent_1 = 0.001
        profit_percent_2 = profit_percent_1 / (total_secondary_orders_2 + 1)

        percent_rollover = 0.0
        max_active_positions = self.max_active_positions

        total_entry_orders = total_secondary_orders_1 + (total_secondary_orders_1 * total_secondary_orders_2)

        available_positions = max_active_positions
        available_input_quantity = self.input_quantity
        position_trade_quantity = self.input_quantity / max_active_positions

        #TODO: add percent calculation: 
        main_pos_percent_of_total_quantity =  0.3
        secondary_pos_input_quantity_1_percent_of_total_quantity = 0.4
        secondary_pos_input_quantity_2_percent_of_total_quantity = 0.3

        main_pos_input_quantity = round(position_trade_quantity * main_pos_percent_of_total_quantity, 0)
        secondary_pos_input_quantity_1 = round(position_trade_quantity \
            * secondary_pos_input_quantity_1_percent_of_total_quantity, 0)
        secondary_pos_input_quantity_2 = round(position_trade_quantity \
            * secondary_pos_input_quantity_2_percent_of_total_quantity, 0)

        secondary_entry_1_input_quantity = int(secondary_pos_input_quantity_1 / total_secondary_orders_1)
        secondary_exit_1_input_quantity = secondary_entry_1_input_quantity * (1 - percent_rollover)

        secondary_entry_2_input_quantity = int(secondary_pos_input_quantity_2 / total_secondary_orders_2)
        secondary_exit_2_input_quantity = secondary_entry_2_input_quantity * (1 - percent_rollover)

        # test_flag = True

        # while(test_flag == True):
        # while(used_input_quantity <= (self.input_quantity - position_trade_quantity)):

        #TODO: create startup checks for active
        while True:

            position_size_check = self.api.get_position_size()
            if position_size_check == 0:
                if (len(self.orders_list) > 0): 
                    for order in self.orders_list:
                        if (order['side'] == self.exit_side):
                            await self.create_trade_record(order)
                else:
                    self.orders_list = []

                    #  update orders list for main pos entry & exit, using profit_percent_1 as default:
                    num_of_orders = 1
                    task_update_orders_list_main_pos_exit = asyncio.create_task(self.ws.update_orders_list_main_pos_exit(\
                        self.orders_list, self.exit_side, profit_percent_1))        

                    # create initial main_pos entry pos & exit order:
                    task_create_main_pos_entry_exit = asyncio.create_task(self.create_main_pos_entry_exit('Market', self.entry_side, \
                        main_pos_input_quantity, profit_percent_1))
                    
                    main_pos_exit_order_id = await task_create_main_pos_entry_exit
                    self.orders_list = await task_update_orders_list_main_pos_exit

                    main_pos_entry = self.api.get_active_position_entry_price()

                    # update orders list
                    num_of_orders = (total_entry_orders + total_secondary_orders_2)
                    task_update_orders_list = asyncio.create_task(self.ws.update_orders_list(num_of_orders, \
                        self.orders_list, secondary_entry_1_input_quantity, profit_percent_1, profit_percent_2))

                    #TODO: Update exit prices to stretch percentage across all exit orders including main
                    # create initial secondary main pos limit exit orders:
                    input_quantity = secondary_exit_2_input_quantity/total_secondary_orders_2
                    task_create_secondary_main_pos_exit_orders = asyncio.create_task(self.api.create_multiple_limit_orders(\
                        total_secondary_orders_2, main_pos_entry, 'long', self.exit_side, input_quantity, profit_percent_2, True))

                    # calculate and create open orders below Main pos:
                    task_create_secondary_orders = asyncio.create_task(self.create_secondary_orders(main_pos_entry, \
                        total_secondary_orders_1, total_secondary_orders_2, total_entry_orders, profit_percent_1, \
                            profit_percent_2, secondary_entry_1_input_quantity, secondary_entry_2_input_quantity))

                    self.orders_list = await task_update_orders_list
                    await task_create_secondary_main_pos_exit_orders
                    await task_create_secondary_orders

            else:
                # update main pos exit order:
                self.api.update_main_pos_exit_order(profit_percent_1, main_pos_exit_order_id, self.entry_side)

                # check for order changes
                print('Waiting on order changes: ')
                await asyncio.sleep(0)
                order_id = await self.ws.get_filled_order_id()

                for order in self.orders_list:
                    if (order['order_id'] == order_id):
                        order_waiting = order
                        self.orders_list.remove(order_waiting)
                        print('\n !!! TEST REMOVE FROM ORDER !!!')
                        print('order removed: ')
                        print(pprint.pprint(order_waiting))
                        print(f'\norder_list length: {len(self.orders_list)}\n')

                        num_of_orders = 1
                        task_update_orders_list = asyncio.create_task(self.ws.update_orders_list(num_of_orders, \
                            self.orders_list, secondary_entry_1_input_quantity, profit_percent_1, profit_percent_2))                        
                        task_update_secondary_orders = await self.update_secondary_orders(order_waiting)

                        self.orders_list = await task_update_orders_list
                        await task_update_secondary_orders
                        #TODO: Add order list compare for slippage
                        break

                    else:
                        print('order id not in list')
                        


    async def create_main_pos_entry_exit(self, order_type, entry_side, main_pos_input_quantity, profit_percent):

                if entry_side == 'Buy':
                    entry_exit = 'long'
                    exit_side = "Sell"
                else:
                    entry_exit = 'short'
                    exit_side = 'Buy'

                if (order_type == 'Market'):
                    print('\ncreating Market main_pos entry: ')
                    self.api.place_order(self.api.last_price(), 'Market', entry_side, main_pos_input_quantity, 0, False)
                    print('\ncreating main_pos exit: ')
                else:
                    # force initial Main Pos limit close order
                    print('\nforcing Limit main_pos entry: ')
                    limit_price_difference = self.limit_price_difference
                    await self.api.force_limit_order(entry_side, main_pos_input_quantity, limit_price_difference, 0, False)

                main_pos_entry = round(self.api.get_active_position_entry_price(), 0)
                main_pos_exit_price = calc().calc_percent_difference(entry_exit, 'exit', main_pos_entry, profit_percent)

                main_pos_exit_order_id = self.api.create_limit_order(main_pos_exit_price, exit_side, \
                    main_pos_input_quantity, 0, True)
                print('main_pos_exit_order_id: ' + str(main_pos_exit_order_id))
                await asyncio.sleep(0)
                return main_pos_exit_order_id

    async def create_secondary_orders(self, main_pos_entry, total_secondary_orders_1, \
        total_secondary_orders_2, total_entry_orders, profit_percent_1, profit_percent_2, \
            secondary_entry_1_input_quantity, secondary_entry_2_input_quantity):

            # create buy/sell orders dict: 
            orders_dict = dca_logic.get_orders_dict(self.entry_side, self.api.get_orders_info())

            print('\n in create secondary orders \n')
            #determine active & available orders
            active_entry_orders = len(orders_dict[self.entry_side])
            active_exit_orders = len(orders_dict[self.exit_side]) - 1
            # total_active_orders = active_exit_orders + active_entry_orders
            available_entry_orders = total_entry_orders - active_entry_orders
            secondary_1_entry_price = main_pos_entry
            secondary_2_entry_price = main_pos_entry

            x = 1
            active_orders_index = 0
            num_check = total_secondary_orders_1
            print('checking for available entries: ')
            while(x <= total_entry_orders):
                
                if (x == num_check):
                    num_check += total_secondary_orders_1
                    input_quantity = secondary_entry_1_input_quantity
                    profit_percent = profit_percent_1
                    entry_price = calc().calc_percent_difference('long', 'entry', secondary_1_entry_price, profit_percent)
                    secondary_1_entry_price = entry_price
                    secondary_2_entry_price = entry_price
                else: 
                    input_quantity = secondary_entry_2_input_quantity
                    profit_percent = profit_percent_2
                    entry_price = calc().calc_percent_difference('long', 'entry', secondary_2_entry_price, profit_percent)
                    secondary_2_entry_price = entry_price               

                if (x <= available_entry_orders):
                    self.api.place_order(entry_price, 'Limit', self.entry_side, input_quantity, 0, False)
                    await asyncio.sleep(0)
                elif (active_orders_index < active_entry_orders):
                    order_id = orders_dict[self.entry_side][active_orders_index]['order_id']
                    self.api.change_order_price_size(entry_price, secondary_entry_1_input_quantity, order_id)
                    active_orders_index +=1
                    await asyncio.sleep(0)
                else:
                    print('')
                    print('x index is out of range')
                    print('x: ' + str(x))
                    break

                x += 1

    async def update_secondary_orders(self, order_waiting):
        try:
            print('processing waiting available order: ')

            input_quantity = order_waiting['input_quantity']
            profit_percent = order_waiting['profit_percent']
            price = order_waiting['price']
            side = order_waiting['side']

            if (side == self.entry_side):
                #create new exit order upon entry close
                print("creating new exit order")
                price = calc().calc_percent_difference('long', 'exit', price, profit_percent)
                self.api.place_order(price, 'Limit', self.exit_side, input_quantity, 0, True)
                print('\n!!! Update Order TEST: ')
                print(f'price: {price}')
                print(type(price))
                print(f'input_quantity: {input_quantity}\n')

            elif (side == self.exit_side):
                print("Creating Trade Record")
                await self.create_trade_record(order_waiting)            
                #create new entry order upon exit close
                print('creating new entry order')
                price = calc().calc_percent_difference('long', 'entry', price, profit_percent)
                print('\n!!! Update Order TEST: ')
                print(f'price: {price}')
                print(type(price))
                print(f'input_quantity: {input_quantity}\n')
                self.api.place_order(price, 'Limit', self.entry_side, input_quantity, 0, False)

            await asyncio.sleep(0)
        except Exception as e:
            print("an exception occured - {}".format(e))