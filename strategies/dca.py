import sys
sys.path.append("..")
from logic.calc import Calc as calc
from api.bybit_api import Bybit_Api
from api.bybit_ws import Bybit_WS
from database.database import Database as db
from model.trades import Trade
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

        self.api = Bybit_Api(api_key, api_secret, symbol, symbol_pair, self.key_input)
        self.ws = Bybit_WS(api_key, api_secret, symbol_pair, True)

        self.api.set_leverage(self.leverage)
        
        self.test_active_orders = 0
        self.closed_orders_list = []
        self.orders_list = []
        self.toggle_main = True
        print('... Strategy_DCA initialized ...')


    async def main(self):

        ping_timer = asyncio.create_task(self.ws.ping(0.5, 15))
        start_dca_multi_position = asyncio.create_task(self.dca_multi_position())
        task_store_closed_orders = asyncio.create_task(self.store_closed_orders())

        await ping_timer
        await start_dca_multi_position
        await task_store_closed_orders        


    # Store closed orders in global list
    async def store_closed_orders(self):
        global closed_orders_list

        while True:
            await asyncio.sleep(0)
            closed_order = await self.ws.get_filled_order()
            print('adding closed order to closed_orders_list')
            self.closed_orders_list.append(closed_order)
            print(pprint.pprint(closed_order))

    #TODO: Add Trade Name to order / db
    async def create_trade_record(self, closed_trade):
        global trade_record_id

        self.trade_record_id = self.trade_record_id + 1
        print('trade_record_id: ' + str(self.trade_record_id))

        print('\ncreating trade record: ')

        trade = Trade(self.trade_id, self.trade_record_id)
        profit_percent = round(closed_trade['profit_percent'], 8)
        exit_price = closed_trade['price']
        entry_price = exit_price * (1 - profit_percent)
        input_quantity = closed_trade['input_quantity']
        last_price = self.api.last_price()
        dollar_gain = round(input_quantity * profit_percent, 8)
        coin_gain =  round(dollar_gain / last_price, 8)
        await asyncio.sleep(0)

        trade.commit_trade_record(coin_gain, dollar_gain, entry_price, exit_price, profit_percent, \
            input_quantity)


    async def dca_multi_position(self):
        global orders_list
        global toggle_main
        global test_active_orders

        #Set Trade Values
        total_secondary_orders_1 = 4 - 1
        total_secondary_orders_2 = 2
        profit_percent_1 = 0.0005
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

        print("!! CHECKS: !!!!\n")
        print('full orders list: ')
        print(pprint.pprint(self.orders_list))
        print('')
        print('closed orders list: ')
        print(pprint.pprint(self.closed_orders_list))
        print('')

        #TODO: create startup checks for active
        while True:
            print(f'first loop position check: {self.api.get_position_size()}')
            if self.api.get_position_size() == 0:
                print('\nin first loop\n')
                print('clearing orders list')
                self.orders_list = []

                # create initial main_pos entry pos & exit orders:
                await self.create_main_pos_entry_exit('Market', self.entry_side, main_pos_input_quantity, profit_percent_2, total_secondary_orders_2)
                self.orders_list = dca_logic.get_updated_orders_list(self.api.get_orders(), profit_percent_1, profit_percent_2)

                main_pos_entry = self.api.get_active_position_entry_price()

                await asyncio.sleep(0)

                # calculate and create open orders below Main pos:
                await asyncio.create_task(self.create_secondary_orders(main_pos_entry, \
                    total_secondary_orders_1, total_secondary_orders_2, total_entry_orders, profit_percent_1, \
                        profit_percent_2, secondary_entry_1_input_quantity, secondary_entry_2_input_quantity))

                # await task_create_secondary_orders
                print('\nout first loop\n')
            else:
                await asyncio.sleep(0.5)

                await self.update_secondary_orders(profit_percent_1, profit_percent_2)

                # create new updated current orders list:
                self.orders_list = dca_logic.get_updated_orders_list(self.api.get_orders(), profit_percent_1, profit_percent_2)
                print('updated full orders list')
                print(self.orders_list)
                print('main loop else exit')


    async def create_main_pos_entry_exit(self, order_type, entry_side, main_pos_input_quantity, profit_percent_2, total_secondary_orders_2):

                entry_link_id = 'open'
                exit_link_id = 'main'

                if entry_side == 'Buy':
                    long_short = 'long'
                    exit_side = "Sell"
                else:
                    long_short = 'short'
                    exit_side = 'Buy'

                if (order_type == 'Market'):
                    print('\ncreating Market main_pos entry: ')
                    self.api.place_order(self.api.last_price(), 'Market', entry_side, main_pos_input_quantity, 0, False, entry_link_id)
                    print('\ncreating main_pos exit: ')
                else:
                    # force initial Main Pos limit close order
                    print('\nforcing Limit main_pos entry: ')
                    limit_price_difference = self.limit_price_difference
                    await self.api.force_limit_order(entry_side, main_pos_input_quantity, limit_price_difference, 0, False, entry_link_id)

                main_pos_entry = round(self.api.get_active_position_entry_price(), 0)
                # link_id = dca_logic.create_link_id(exit_link_id, 1)
                # main_pos_exit_price = calc().calc_percent_difference(long_short, 'exit', main_pos_entry, profit_percent_1)
                # self.api.create_limit_order(main_pos_exit_price, exit_side, main_pos_input_quantity, 0, True, link_id)
                # self.api.create_multiple_limit_orders(total_secondary_orders_2, main_pos_entry, long_short, exit_side, input_quantity, profit_percent_2, True, 'pp_2')

                print('\ncreating main pos exits: ')
                total_num_orders = total_secondary_orders_2 + 1
                input_quantity = main_pos_input_quantity
                input_quantity_2 = round(main_pos_input_quantity / total_num_orders, 0)
                start_price = main_pos_entry
                num_order = total_num_orders
                for x in range(total_num_orders):
                    profit_percent = profit_percent_2 * num_order
                    await asyncio.sleep(0)
                    print(x)
                    link_id = dca_logic.create_link_id(exit_link_id, x + 1)
                    profit_percent = profit_percent_2 * num_order
                    print(f'profit_percent {profit_percent}')
                    print(f'num_order {num_order}')
                    price = calc().calc_percent_difference(long_short, 'exit', start_price, profit_percent)
                    print(f'price: {price}')
                    self.api.place_order(price, 'Limit', exit_side, input_quantity, 0, True, link_id)
                    num_order -= 1
                    input_quantity = input_quantity_2
                    
                



    async def create_secondary_orders(self, main_pos_entry, total_secondary_orders_1, \
        total_secondary_orders_2, total_entry_orders, profit_percent_1, profit_percent_2, \
            secondary_entry_1_input_quantity, secondary_entry_2_input_quantity):
            global test_active_orders

            if self.entry_side == 'Buy':
                long_short = 'long'
            else:
                long_short = 'short'

            # create buy/sell orders dict: 
            orders_dict = dca_logic.get_orders_dict(self.entry_side, self.api.get_orders())
            print('\n in create secondary orders \n')
            #determine active & available orders
            active_entry_orders = len(orders_dict[self.entry_side])
            active_exit_orders = len(orders_dict[self.exit_side]) - 1
            # total_active_orders = active_exit_orders + active_entry_orders
            available_entry_orders = total_entry_orders - active_entry_orders
            secondary_1_entry_price = main_pos_entry
            secondary_2_entry_price = main_pos_entry

            x = 0
            active_orders_index = 0
            num_check = total_secondary_orders_1
            print('checking for available entries: ')
            while(x < total_entry_orders):
                
                if (x == num_check):
                    num_check += total_secondary_orders_1
                    input_quantity = secondary_entry_1_input_quantity
                    link_id = 'pp_1'
                    profit_percent = profit_percent_1
                    entry_price = calc().calc_percent_difference(long_short, 'entry', secondary_1_entry_price, profit_percent)
                    secondary_1_entry_price = entry_price
                    secondary_2_entry_price = entry_price
                else: 
                    input_quantity = secondary_entry_2_input_quantity
                    link_id = 'pp_2'
                    profit_percent = profit_percent_2
                    entry_price = calc().calc_percent_difference(long_short, 'entry', secondary_2_entry_price, profit_percent)
                    secondary_2_entry_price = entry_price               

                if (x < available_entry_orders):
                    print(f'available_entry_orders: {available_entry_orders}')
                    print(f'in fill available entry orders: x = {x}\n')
                    await asyncio.sleep(0)
                    self.api.place_order(entry_price, 'Limit', self.entry_side, input_quantity, 0, False, link_id)

                elif (active_orders_index <= total_entry_orders):
                    print(f'active_entry_orders: {active_entry_orders}')
                    print(f'in update existing entry orders: x = {x}\n')
                    order_id = orders_dict[self.entry_side][active_orders_index]['order_id']
                    print(f'order_id for change order: {order_id}')
                    await asyncio.sleep(0)
                    self.api.change_order_price_size(entry_price, input_quantity, order_id)
                    active_orders_index +=1
                    
                else:
                    print('')
                    print('x index is out of range')
                    print('x: ' + str(x))
                    break

                x += 1

    async def update_secondary_orders(self, profit_percent_1, profit_percent_2):
        global orders_list
        global toggle_main
        global test_active_orders
        global closed_orders_list

        # try:
        order_flag = True
        print('in update_secondary_orders')
        while order_flag == True:
            # TODO: Update for partial fill checks
            await asyncio.sleep(0.5)
            while (len(self.closed_orders_list) > 0):
                updated_closed_orders_list = dca_logic.get_updated_orders_list(self.closed_orders_list, profit_percent_1, profit_percent_2)
                closed_order = updated_closed_orders_list[0]
                self.closed_orders_list.remove(self.closed_orders_list[0])

                print('processing waiting available order: \n')
                print(pprint.pprint(closed_order))

                input_quantity = closed_order['input_quantity']
                profit_percent = closed_order['profit_percent']
                price = closed_order['price']
                side = closed_order['side']
                link_id = closed_order['link_id']

                await asyncio.sleep(0)
                if (side == self.entry_side):
                    
                    #create new exit order upon entry close
                    print("creating new exit order")
                    price = calc().calc_percent_difference('long', 'exit', price, profit_percent)
                    self.api.place_order(price, 'Limit', self.exit_side, input_quantity, 0, True, link_id)

                elif (side == self.exit_side):
                    print("Creating Trade Record")
                    await self.create_trade_record(closed_order)            
                    #create new entry order upon exit close
                    print('creating new entry order')
                    price = calc().calc_percent_difference('long', 'entry', price, profit_percent)
                    self.api.place_order(price, 'Limit', self.entry_side, input_quantity, 0, False, link_id)

                print('\nclosed orders list len: ')
                print(len(self.closed_orders_list))
                if (len(self.closed_orders_list) == 0):
                    print('\n emptied orders list in update secondary orders')
                    print('closed orders list: ')
                    print(self.closed_orders_list)
                    print('')
                    order_flag = False

        # except Exception as e:
        #     print("an exception occured - {}".format(e))

    # def confirm_secondary_orders(self, total_orders):
    #     current_order_amount = len(self.api.get_orders())
        
        # if (current_order_amount != total_orders):


