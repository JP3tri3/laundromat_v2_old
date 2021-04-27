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

        print('... Strategy_DCA initialized ...')


    async def main(self):
        order_list = []
        ping_timer = asyncio.create_task(self.ws.ping(0.05, 15))
        start_dca_multi_position = asyncio.create_task(self.dca_multi_position())
        # # execution = asyncio.create_task(self.ws.get_execution())
        # order_status_test = asyncio.create_task(self.ws.update_order_list(3, order_list, 10, 0.5, 0.2))


        await ping_timer
        # await order_status_test

        await start_dca_multi_position



    # async def test_1(self):
    #     pos_size = None
        

        # while True:



            
        #     print('testing')
        #     await asyncio.sleep(0.005)

        #     pos_size = await self.ws.get_pos_info()

        #     if pos_size[0]['size'] == 0:

        #     pos_size = None




        

    #Create Trade Record
    async def create_trade_record(self, profit_percent, closed_trade):
        global trade_record_id
        global open_equity

        self.trade_record_id = self.trade_record_id + 1
        print('trade_record_id: ' + str(self.trade_record_id))

        print('')
        print('creating trade record: ')
        print(closed_trade)
        trade = Trade(self.trade_id, self.trade_record_id)
        exit_price = closed_trade['price']
        entry_price = exit_price * (1 - profit_percent)
        percent_gain = profit_percent
        input_quantity = closed_trade['input_quantity']
        current_last_price = self.api.last_price()
        current_equity = self.api.wallet_equity()
        dollar_gain = input_quantity * (1 - profit_percent)
        coin_gain = self.api.last_price() / dollar_gain
            
        trade.commit_trade_record(coin_gain, dollar_gain, entry_price, exit_price, percent_gain, \
            input_quantity)


    async def dca_multi_position(self):
         
        #Set Trade Values

        # TODO: Calculate initial exit orders, the first loop updates main pos exit incorrectly
        # TODO: In line 294, in update_secondary_orders order_waiting = orders_waiting[x] KeyError: 0

        total_secondary_orders_1 = 4 - 1
        total_secondary_orders_2 = 2
        profit_percent_1 = 0.0025
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

        #### TEST ####

        # test_flag = True

        # while(test_flag == True):
        #     print("!! IN MAIN LOOP !!")
        # while(used_input_quantity <= (self.input_quantity - position_trade_quantity)):

        while True:

            position_size_check = self.api.get_position_size()
            if position_size_check == 0:
                orders_list = []

                # # force initial Main Pos limit close order
                # print('')
                # print('creating main_pos entry: ')
                # limit_price_difference = self.limit_price_difference
                # await self.api.force_limit_order(self.entry_side, main_pos_input_quantity, limit_price_difference, 0, False)

                # TEST W/ MARKET Order:
                print('')
                print('creating main_pos entry: ')
                self.api.place_order(self.api.last_price(), 'Market', self.entry_side, main_pos_input_quantity, 0, False)
                
                main_pos_entry = round(self.api.get_active_position_entry_price(), 0)

                # create initial Main Pos limit exit order:
                print('')
                print('creating main_pos exit: ')
                main_pos_exit_price = calc().calc_percent_difference('long', 'exit', main_pos_entry, profit_percent_1)

                main_pos_exit_order_id = self.api.create_limit_order(main_pos_exit_price, self.exit_side, \
                    main_pos_input_quantity, 0, True)
                print('main_pos_exit_order_id: ' + str(main_pos_exit_order_id))

                # create initial orders dict: 
                orders_dict = dca_logic.get_orders_dict(self.entry_side, self.api.get_orders_info(), \
                    secondary_entry_2_input_quantity, profit_percent_1, profit_percent_2)
                if (orders_dict[self.exit_side] == []):
                    main_pos_exit_order_id = 'null'
                else:
                    main_pos_exit_order_info = orders_dict[self.exit_side][0]

                # update orders list
                num_of_orders = (total_entry_orders + total_secondary_orders_2)
                task_update_order_list = asyncio.create_task(self.ws.update_order_list(num_of_orders, \
                    orders_list, secondary_entry_1_input_quantity, profit_percent_1, profit_percent_2))

                # create initial secondary main pos limit exit orders:
                input_quantity = secondary_exit_2_input_quantity/total_secondary_orders_2
                task_create_secondary_main_pos_exit_orders = asyncio.create_task(self.api.create_multiple_limit_orders(\
                    total_secondary_orders_2, main_pos_entry, 'long', self.exit_side, input_quantity, profit_percent_2, True))

                # calculate and create open orders below Main pos:
                task_create_secondary_orders = asyncio.create_task(self.create_secondary_orders(main_pos_entry, orders_dict, total_secondary_orders_1, \
                    total_secondary_orders_2, total_entry_orders, profit_percent_1, profit_percent_2, \
                        secondary_entry_1_input_quantity, secondary_entry_2_input_quantity))

                order_list = await task_update_order_list
                await task_create_secondary_main_pos_exit_orders
                await task_create_secondary_orders

            else:
                # update main pos exit order:
                self.api.update_main_pos_exit_order(profit_percent, main_pos_exit_order_id, self.entry_side)

                # check for order changes
                print('Waiting on order changes: ')
                await asyncio.sleep(0)
                order_id = await self.ws.get_filled_order_id()

                for x in order_list:
                    if (order_list[x]['order_id'] == order_id):
                        order_waiting = order_list[x]
                        order_list.remove(order_waiting)

                self.update_secondary_orders(order_waiting)


    async def create_main_pos_entry_exit(self)       

    async def create_secondary_orders(self, main_pos_entry, orders_dict, total_secondary_orders_1, \
        total_secondary_orders_2, total_entry_orders, profit_percent_1, profit_percent_2, \
            secondary_entry_1_input_quantity, secondary_entry_2_input_quantity):


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

        print('processing waiting available order: ')

        input_quantity = order_waiting['input_quantity']
        profit_percent = order_waiting['profit_percent']
        price = order_waiting['price']
        side = order_waiting['side']

        if (order_waiting['side'] == self.entry_side):
            #create new exit order upon entry close
            print("creating new exit order")
            price = str(calc().calc_percent_difference('long', 'exit', price, profit_percent))
            self.api.place_order(price, 'Limit', self.exit_side, input_quantity, 0, False)

        elif (order_waiting['side'] == self.exit_side):
            print("Creating Trade Record")
            self.create_trade_record(profit_percent, order_waiting)            
            #create new entry order upon exit close
            print('creating new entry order')
            price = calc().calc_percent_difference('long', 'entry', price, profit_percent)
            self.api.place_order(price, 'Limit', self.entry_side, input_quantity, 0, True)
        
        