import sys
sys.path.append("..")
from logic.calc import Calc as calc
from api.bybit_api import Bybit_Api
from api.bybit_ws import Bybit_WS
from strategies.dca_db import DCA_DB
from strategies import dca_logic
import asyncio
import pprint


# TODO LIST:
# fixing databasing new orders

class Strategy_DCA:

    def __init__(self, api_key, api_secret, trade_id, strat_id, symbol, symbol_pair, key_input, \
        input_quantity, leverage, limit_price_difference, max_active_positions, entry_side):
        self.trade_id = trade_id
        self.strat_id = strat_id
        self.input_quantity = input_quantity
        self.max_active_positions = max_active_positions
        self.leverage = leverage
        self.key_input = key_input
        self.limit_price_difference = limit_price_difference
        self.entry_side = entry_side

        if (entry_side == 'Buy'): self.exit_side = 'Sell'
        else: self.exit_side = 'Buy'

        #TODO: Strat db settings, move to class arguments:
        strat_name = 'dcamp'
        instance = 1

        self.api = Bybit_Api(api_key, api_secret, symbol, symbol_pair, self.key_input)
        self.ws = Bybit_WS(api_key, api_secret, symbol_pair, True)
        self.db = DCA_DB(trade_id, strat_name, instance)

        self.api.set_leverage(self.leverage)
        
        self.filled_orders_list = []
        self.grids_dict = {}
        self.slipped_quantity = 0
        self.waiting_orders_list = []

        self.active_grid_pos = 0
        self.grid_range_price = 0

        # Set Trade Values
        self.profit_percent_1 = 0
        self.profit_percent_2 = 0

        print('... Strategy_DCA initialized ...')

    # TODO: Fix main pos quantity thats savedw
    async def main(self):
        global grids_dict
        # TODO: Testing, remove
        test_strat = False  
        # set initialize save state:
        initialize_save_state_tf = True
        # set reset all tables (will error if there is an active position!)
        reset_all_db_tables = False
        main_strat = None

        if test_strat: main_strat = False 
        else: main_strat = True
        
        #Set Trade Values
        total_secondary_orders_1 = 3

        secondary_orders_2 = 2
        total_secondary_orders_2 = total_secondary_orders_1 * secondary_orders_2

        total_exit_orders_1 = 1
        total_exit_orders_2 = secondary_orders_2

        profit_percent_1 = 0.0004
        profit_percent_2 = profit_percent_1 / (secondary_orders_2 + 1)

        total_entry_orders = total_secondary_orders_1 + total_secondary_orders_2
        total_exit_orders = total_exit_orders_1 + total_exit_orders_2

        total_entry_exit_orders = total_entry_orders + total_exit_orders

        percent_rollover = 0.0

        #TODO: add percent calculation: 
        main_pos_percent_of_total_quantity =  0.4
        secondary_pos_1_percent_of_total_quantity = 0.3
        secondary_pos_2_percent_of_total_quantity = 0.3

        position_trade_quantity = self.input_quantity / self.max_active_positions

        main_pos_input_quantity = round(position_trade_quantity * main_pos_percent_of_total_quantity, 0)
        secondary_pos_input_quantity_1 = round(position_trade_quantity * secondary_pos_1_percent_of_total_quantity, 0)
        secondary_pos_input_quantity_2 = round(position_trade_quantity * secondary_pos_2_percent_of_total_quantity, 0)

        secondary_entry_1_input_quantity = int(secondary_pos_input_quantity_1 / total_secondary_orders_1)
        secondary_exit_1_input_quantity = secondary_entry_1_input_quantity * (1 - percent_rollover)

        secondary_entry_2_input_quantity = int(secondary_pos_input_quantity_2 / total_secondary_orders_2)
        secondary_exit_2_input_quantity = secondary_entry_2_input_quantity * (1 - percent_rollover)

        # initialize grids dict:
        self.grids_dict[self.active_grid_pos] = dca_logic.initialize_grid(total_entry_exit_orders, 0, 0, 0, 0)

        if main_strat:
            print('in main_strat')
        # starting tasks

            if (reset_all_db_tables):
                self.db.initialize_all_tables(dlt_table_t_f=True, create_table_t_f=True)
                self.db.dcamp_create_new_grid_row(self.active_grid_pos)

            # initialize from saved state:
            if (initialize_save_state_tf):
                await self.initialize_saved_state(total_entry_exit_orders, profit_percent_1, profit_percent_2, total_exit_orders, 
                                        total_secondary_orders_1, secondary_orders_2, total_entry_orders, secondary_entry_1_input_quantity, 
                                            secondary_entry_2_input_quantity)
                # removes unused rows from DB (active / slipped / grid) / clears filled:

                if (reset_all_db_tables == False):
                    self.db.initialize_non_peristent_tables(True, True)
                    self.db.dcamp_remove_unused_active_orders_rows(self.active_grid_pos)
                    self.db.dcamp_remove_slipped_orders_rows(self.active_grid_pos)
                    self.db.dcamp_remove_unused_grids_rows(self.active_grid_pos)

            # start main tasks
            task_ping_timer = asyncio.create_task(self.ws.ping(0.5, 15))
            task_collect_orders = asyncio.create_task(self.collect_orders())
            task_process_waiting_orders = asyncio.create_task(self.store_new_changed_filled_orders(profit_percent_1, profit_percent_2))
            task_start_dca_multi_position = asyncio.create_task(self.dca_multi_position(total_secondary_orders_1, secondary_orders_2, profit_percent_1,
                                                                    profit_percent_2, total_entry_exit_orders, total_entry_orders, total_exit_orders,  
                                                                        main_pos_input_quantity, secondary_entry_1_input_quantity, secondary_entry_2_input_quantity))


            await task_ping_timer
            await task_collect_orders
            await task_process_waiting_orders   
            await task_start_dca_multi_position

        # # # # # # TEST # # # # # #
        if test_strat:
            
            print(" !!!!! TESTING !!!!")

            # self.grids_dict[1] = {'test'}
            # self.grids_dict[2] = {'test2'}
            # self.grids_dict[1] = dca_logic.initialize_grid(total_entry_exit_orders, 0, 0, 0, 0)
            # self.grids_dict[2] = dca_logic.initialize_grid(total_entry_exit_orders, 0, 0, 0, 0)

            # orders_list = self.api.get_orders()
            # num_active_orders = len(orders_list)
            # position_size = self.api.get_position_size()

            # grid_row_check = self.db.check_grid_row_exists(self.active_grid_pos)
            print(f'grid_pos: {self.active_grid_pos}')

            # print(f'\nactive position size: {position_size}')
            # print(f'num_active_orders: {num_active_orders}\n')
                # grid_range_price_check = value['range_price']
                # print(f'last_price: {last_price}, grid_range_price_check: {grid_range_price_check}')

            # for key, value in self.grids_dict.items():
            #     print(v)


                # for key in grid:
                #     print(f'grid_key: {key}' )
            # testing = self.grids_dict
            # print(testing)
            # self.active_grid_pos += 1
            # # print(f'\ngrid_pos: {self.active_grid_pos}\n')
            # self.db.initialize_active_orders_table(self.active_grid_pos, total_entry_exit_orders)

            # order = {'grid_pos': 1,
            #             'input_quantity': 10,
            #             'leaves_qty': 10,
            #             'link_name': 'main',
            #             'order_id': 'b06a9d22-1c9f-4767-a566-028f13648703',
            #             'order_link_id': 'main-1-3-3563423431620527220.584705',
            #             'order_pos': 1,
            #             'order_status': 'Cancelled',
            #             'price': 58571.0,
            #             'profit_percent': 0.0004,
            #             'side': 'Buy'}

            # order_2 = {'grid_pos': 1,
            #             'input_quantity': 10,
            #             'leaves_qty': 10,
            #             'link_name': 'main',
            #             'order_id': 'b06a9d22-1c9f-4767-a566-028f13648703',
            #             'order_link_id': 'main-1-1-3563423431620527220.584705',
            #             'order_pos': 1,
            #             'order_status': 'Cancelled',
            #             'price': 58571.0,
            #             'profit_percent': 0.0004,
            #             'side': 'Buy'}

            # # print(self.grids_dict[self.active_grid_pos])

            # self.db.dcamp_replace_active_order(order)



    async def test_func(self):
        await asyncio.sleep(2)
        # link_id = (f'main-{self.active_grid_pos}-1-356342343')
        self.api.place_order(self.api.last_price() - 400, 'Market', 'Buy', 10, 0, False, 'open-1-1-356342343')
        # link_id = (f'main-{self.active_grid_pos}-3-356342341')
        # self.api.place_order(self.api.last_price() - 500, 'Limit', 'Buy', 10, 0, False, 'main-1-3-356342343')

    async def collect_orders_test(self, profit_percent_1, profit_percent_2):
        global grids_dict
        print('collecting orders')
        await asyncio.sleep(0)
        order = await self.ws.get_order()

        order = dca_logic.get_updated_order_info(order, profit_percent_1, profit_percent_2)

        grid_pos = order['grid_pos']
        if (grid_pos != self.active_grid_pos):
            print('!! grid_pos: outside current grid !!')
        order_pos = order['order_pos']
        order_status = order['order_status']
        link_name = order['link_name']

        # new_order = dca_logic.get_updated_order_info(order, profit_percent_1, profit_percent_2)
        print(pprint.pprint(order))
        print(link_name)

    # initialize from saved state:
    async def initialize_saved_state(self, total_entry_exit_orders, profit_percent_1, profit_percent_2, total_exit_orders, 
                                        total_secondary_orders_1, secondary_orders_2, total_entry_orders, secondary_entry_1_input_quantity, 
                                            secondary_entry_2_input_quantity):
        global active_grid_pos
        global grids_dict
        global slipped_quantity

        print(' ... loading saved state ... ')

        orders_list = self.api.get_orders()
        
        num_active_orders = len(orders_list)
        position_size = self.api.get_position_size()

        print(f'\nactive position size: {position_size}')
        print(f'num_active_orders: {num_active_orders}\n')

        if (position_size == 0) and (num_active_orders == 0):

            print('no existing state \n')
        # elif (position_size > 0 and num_active_orders == 0):
        #     print('\nthis makes no sense\n')

        else:
            print('... processing ...')
            active_grid_pos = 0
            grid_row_check = True
            ttl_pos_size = 0

            total_exit_quantity = 0
            total_entry_quantity = 0

            # fill active orders lists from DB:
            while (grid_row_check):
                active_grid_pos += 1
                grid_row_check = self.db.check_grid_row_exists(active_grid_pos)
                print(f'\ngrid_pos_check: {active_grid_pos}')
                print(f'grid_row_check: {grid_row_check}')
                
                if (grid_row_check):
                    grid_info = self.db.get_grid_row_values(active_grid_pos)
                    grid_range_price = grid_info['grid_range_price']
                    pos_price = grid_info['pos_price']
                    grid_pos_size = grid_info['pos_size']
                    ttl_pos_size = grid_info['ttl_pos_size']

                    self.grids_dict[active_grid_pos] = dca_logic.initialize_grid(total_entry_exit_orders, pos_price, grid_range_price, grid_pos_size, ttl_pos_size)
                
                    grid_orders_list = dca_logic.get_orders_in_grid(active_grid_pos, orders_list)
                    grid_orders_list_len = len(grid_orders_list)
                    print(f'grids_orders_list_len: {grid_orders_list_len}')
                    if (grid_orders_list_len > 0):
                        for order in grid_orders_list:
                            updated_order = dca_logic.get_updated_order_info(order, profit_percent_1, profit_percent_2)
                            order_pos = updated_order['order_pos']
                            side = updated_order['side']
                            input_quantity = updated_order['input_quantity']
                            self.grids_dict[active_grid_pos]['active'][order_pos] = updated_order

                            if (side == self.entry_side):
                                total_entry_quantity += input_quantity
                            else:
                                total_exit_quantity += input_quantity  

            grid_range_price = 0
            last_price = self.api.last_price()

            # determine if last price in an existing grid:
            print(f'\ndetermining grid range:')

            for key in self.grids_dict:
                print(f'key: {key}')
                value = self.grids_dict[key]
                grid_range_price_check = value['range_price']
                print(f'last_price: {last_price}, grid_range_price_check: {grid_range_price_check}')

                if ((self.entry_side == 'Buy') and (last_price >= grid_range_price_check) and (grid_range_price_check > grid_range_price)) \
                    or ((self.entry_side == 'Sell') and (last_price <= grid_range_price) and (grid_range_price_check < grid_range_price)):
                    grid_range_price = grid_range_price_check
                    active_grid_pos = key

            print(f'determined grid_range_price: {grid_range_price}')
            print(f'determined active_grid_pos: {active_grid_pos}')

            self.active_grid_pos = active_grid_pos


            # TODO: Handle what to do with initialized slipped quantity
            # TODO: Handle exit quantity difference
            # TODO: Handle initializing / checking orders within grid

            # determine slipped quantity
            total_overall_pos_size = self.api.get_position_size()
            exit_quantity_difference = total_overall_pos_size - total_exit_quantity


            print(f'\ntotal_entry_quantity: {total_entry_quantity}')
            print(f'total_exit_quantity: {total_exit_quantity}')
            print(f'total_overall_pos_size: {total_overall_pos_size}')
            print(f'exit_quantity_difference: {exit_quantity_difference}')

            # place slipped exit quantity in closest exit order
            # TODO: fix updated orders using main input quantity to reposition order

            if (exit_quantity_difference > 0):
                orders_list = self.api.get_orders()
                grid_orders_list = dca_logic.get_orders_in_grid(self.active_grid_pos, orders_list)
                print('checking for exit order to place exit quantity difference:')

                pos_check = self.active_grid_pos
                fill_order_check = True

                while(fill_order_check):
                    print(f'\nchecking pos {pos_check} for exit order:')

                    #TODO: Check further:
                    if (pos_check == 0):
                        # TODO: Address active orders in DB pos check 0 
                        print(f'pos_check: {pos_check}, exiting fill order check unfilled')
                        exit_price = self.grids_dict[pos_check]['pos_price']
                        last_price = self.api.last_price()
                        print(f'placing exit order at grid_pos exit price')
                        print(f'last_price: {last_price}, exit_price: {exit_price}')
                        if ((self.entry_side == 'Buy') and last_price < exit_price) \
                            or ((self.entry_side == 'Sell') and last_price > exit_price):
                            self.api.place_order(exit_price, 'limit', self.exit_side, exit_quantity_difference, 0, True, 'main-0-1')
                            print(f'exit order updated at {exit_price}')
                            fill_order_check = False
                        else:
                            print(f'no valid exit order to update, creating new exit order:')
                            if (self.exit_side == 'Sell'):
                                exit_price = last_price + 50
                            else:
                                exit_price = last_price - 50
                            self.api.place_order(exit_price, 'limit', self.exit_side, exit_quantity_difference, 0, True, 'main-0-1')
                            fill_order_check = False

                    elif (pos_check > 0):
                        
                        grid_orders_dict = dca_logic.get_grid_orders_dict(self.active_grid_pos, self.entry_side, grid_orders_list)
                        entry_orders_list = grid_orders_dict[self.entry_side]
                        entry_orders_list_len = len(entry_orders_list)
                        exit_orders_list = grid_orders_dict[self.exit_side]
                        exit_orders_list_len = len(exit_orders_list)
                        total_entry_orders = (total_entry_orders - exit_orders_list_len)

                        for order in exit_orders_list:
                            updated_order = dca_logic.get_updated_order_info(order, profit_percent_1, profit_percent_2)
                            link_id = updated_order['order_link_id']
                            link_name = updated_order['link_name']
                            order_pos = updated_order['order_pos']
                            
                            print(f'\nlink_name: {link_name}, order_pos: {order_pos}')

                            if (link_name == 'main') and (order_pos == 1):
                                print(f'found exit order: {link_id}')
                                order_id = updated_order['order_id']
                                exit_price = updated_order['price']
                                exit_input_quantity = updated_order['input_quantity']
                                changed_input_quantity = exit_input_quantity + exit_quantity_difference
                                self.api.change_order_price_size(exit_price, changed_input_quantity, order_id)
                                fill_order_check = False
                                (f'exit order updated')

                        pos_check -= 1

                    else:
                        print(f'something . is fucking .. wrong.  in initialize')
                        fill_order_check = False


            orders_list = self.api.get_orders()
            grid_orders_dict = dca_logic.get_grid_orders_dict(self.active_grid_pos, self.entry_side, orders_list)
            exit_orders_list_len = len(grid_orders_dict[self.exit_side])
            entry_orders_list_len = len(grid_orders_dict[self.entry_side])
            total_entry_exit_orders_len = entry_orders_list_len + exit_orders_list_len

            # creates entry / exits to match grid
            print(f'exit_orders_list_len: {exit_orders_list_len}')
            print(f'self.active_grid_pos: {self.active_grid_pos}')

            if (exit_orders_list_len > 0):
                main_pos_entry = self.grids_dict[self.active_grid_pos]['pos_price']
                if (exit_orders_list_len < total_exit_orders):
                    await self.create_main_pos_entry_exit('Market', self.entry_side, input_quantity, exit_quantity_difference,
                                profit_percent_2, total_exit_orders, main_pos_entry, exit_orders_list_len)
                
                await asyncio.sleep(0)
                if (total_entry_exit_orders_len != total_entry_exit_orders):
                    total_entry_orders = (total_entry_orders - entry_orders_list_len)
                    await self.create_secondary_orders(main_pos_entry, total_secondary_orders_1, secondary_orders_2, 
                                total_entry_orders, profit_percent_1, profit_percent_2, secondary_entry_1_input_quantity, 
                                    secondary_entry_2_input_quantity)



    def initialize_secondary_orders(self):
        global filled_orders_list

        print('... initialize_secondary_orders ...')

        active_grid_pos = self.active_grid_pos
        for x in range(len(self.grids_dict[active_grid_pos]['active'])):
            x += 1
            order = self.grids_dict[active_grid_pos]['active'][x]
            if (order == None):
                order_id = str(active_grid_pos) + str(x)
                order_to_process = self.db.get_active_order_row_values(order_id)
                if order_to_process['input_quantity'] == 0:

                    new_order = {'grid_pos': active_grid_pos,
                                'order_pos': x,
                                'input_quantity': order_to_process['input_quantity'],
                                'profit_percent': order_to_process['profit_percent'],
                                'leaves_qty': order_to_process['leaves_qty'],
                                'link_name': order_to_process['link_name'],
                                'order_id': 'b06a9d22-1c9f-4767-a566-028f13648703',
                                'order_link_id': order_to_process['link_id'],
                                'order_status': order_to_process['status'],
                                'price': order_to_process['price'],
                                'side': order_to_process['side']}

                    self.filled_orders_list.append(new_order)



    # collect orders via ws
    async def collect_orders(self):
        global waiting_orders_list

        print('collecting orders')
        while True:
            order = await self.ws.get_order()
            self.waiting_orders_list.append(order[0])
            await asyncio.sleep(0)

    # TODO: Address 'PartiallyFilled' order status

    # TODO: Add checks for confirming active orders
    async def store_new_changed_filled_orders(self, profit_percent_1, profit_percent_2):
        print('in store orders')
        global filled_orders_list
        global grids_dict
        global waiting_orders_list

        try:
            while True:
                await asyncio.sleep(0.5)
                if (self.waiting_orders_list != []):
                    for waiting_order in self.waiting_orders_list:
                        order_link_id = waiting_order['order_link_id']
                        if (order_link_id == ''):
                            print(f'skip store oder: {order_link_id}')
                            await asyncio.sleep(0)

                        else:
                            order = dca_logic.get_updated_order_info(waiting_order, profit_percent_1, profit_percent_2)
                            self.waiting_orders_list.remove(waiting_order)

                            grid_pos = order['grid_pos']
                            if (grid_pos != self.active_grid_pos):
                                print('!! grid_pos: outside current grid !!')
                            
                            order_status = order['order_status']
                            link_name = order['link_name']
                            side = order['side']
                            print(f'\n order status: {order_status}\n')

                            if (link_name == 'open'):
                                print(f'skip store order: {link_name}')

                            else:
                                if (order_status == 'Filled') or (order_status == 'PartiallyFilled'):
                                    print('\nadding closed order to filled_orders_list')
                                    self.filled_orders_list.append(order)
                                    self.db.dcamp_create_new_order_row(order)

                                elif (order_status == 'New'):
                                    print('\nadding new or changed order to order list\n')

                                    # check timestamp to determine whether or not to store order:
                                    order_pos = order['order_pos']
                                    previous_stored_order = self.grids_dict[self.active_grid_pos]['active'][order_pos]

                                    store_order_check = False

                                    if (previous_stored_order == None):
                                        store_order_check = True
                                    else:
                                        ts = order['timestamp']
                                        order_converted_ts = dca_logic.convert_timestamp(ts)
                                        pre_ts = previous_stored_order['timestamp']
                                        stored_order_converted_ts = dca_logic.convert_timestamp(pre_ts)
                                        if (order_converted_ts > stored_order_converted_ts):
                                            store_order_check = True

                                    if (store_order_check):
                                        self.db.dcamp_replace_active_order(order)
                                        self.grids_dict[grid_pos]['active'][order_pos] = order
                                    
                                    
                                elif (order_status == 'Cancelled'):
                                    print('\nOrder was Cancelled, checking for slipped or intention... \n')
                                    cancelled_order_id = order['order_id']
                                    
                                    if (cancelled_order_id in self.grids_dict[grid_pos]['cancelled']) == False:
                                        print('confirmed slipped order, moving cancelled order to slipped list')
                                        self.grids_dict[grid_pos]['slipped'].append(order)
                                        self.db.dcamp_replace_slipped_order(order)

                                    else:
                                        print('confirmed cancelled order, removing order id from cancelled orders list')
                                        self.grids_dict[grid_pos]['cancelled'].remove(cancelled_order_id)
                                else:
                                    print('invalid order status')

                            await asyncio.sleep(0)

                    for order in self.grids_dict[self.active_grid_pos]['slipped']:
                        num_slipped_orders = len(self.grids_dict[self.active_grid_pos]['slipped'])
                        print(f'\n num slipped orders: {num_slipped_orders} \n')
                        side = order['side']
                        price = order['price']
                        last_price = self.api.last_price()
                        print(f'side: {side}, price: {price}, last_price: {last_price}')

                        if ((side == 'Buy') and (price < last_price)) \
                            or ((side == 'Sell') and (price > last_price)):

                            print('adding slipped_order to filled_orders_list')
                            self.filled_orders_list.append(order)
                            self.grids_dict[self.active_grid_pos]['slipped'].remove(order)

                            self.db.dcamp_replace_slipped_order_status(order)
                        else:
                            print(f'order still slipped: ')
                            print(pprint.pprint(order))
                            print('')
                        
                        await asyncio.sleep(0)

        except Exception as e:
            print("an exception occured - {}".format(e))
            sys.exit()
        

    #TODO: Add Trade Name to order / db
    async def create_trade_record(self, closed_trade):
        print('\ncreating trade record: ')

        profit_percent = round(closed_trade['profit_percent'], 8)
        exit_price = closed_trade['price']
        entry_price = exit_price * (1 - profit_percent)
        input_quantity = closed_trade['input_quantity']
        last_price = self.api.last_price()
        dollar_gain = round(input_quantity * profit_percent, 8)
        coin_gain =  round(dollar_gain / last_price, 8)
        await asyncio.sleep(0)

        self.db.commit_trade_record(coin_gain, dollar_gain, entry_price, exit_price, profit_percent, \
            input_quantity)

    async def dca_multi_position(self, total_secondary_orders_1, secondary_orders_2, profit_percent_1, profit_percent_2, total_entry_exit_orders, 
                                                        total_entry_orders, total_exit_orders, main_pos_input_quantity, secondary_entry_1_input_quantity,
                                                                 secondary_entry_2_input_quantity):

        global filled_orders_list
        global grids_dict
        global active_grid_pos


        # determine_grid_size, currently by largest set profit * orders:
        #TODO: optimize grid_range_margin margin
        grid_range_margin = 0.01
        grid_percent_range = (profit_percent_1 * total_secondary_orders_1) + grid_range_margin
        grid_range_price = self.grid_range_price
        grid_pos_size = 0

        total_previous_pos_size = 0

        #TODO: Testing, remove:
        new_trend = True

        #TODO: Change waiting_for_trend to True when running, False for test purposes
        init_existing_grid = False

        while (True):

            #TODO: Remove set new_trend for testing:
            # new_trend = await self.determine_grid_and_trend(self.active_grid_pos, grid_range_price)
            if (new_trend):
                print('init new grid: ')
                # initialize new grid:

                #TODO: Only use with new tables for testing:

                grid_pos_size = 0

                if (self.api.get_position_size() == 0):
                    print(f'pos_size = 0')
                    self.active_grid_pos += 1
                    total_previous_pos_size = self.grids_dict[self.active_grid_pos - 1]['ttl_pos_size']
                    
                    self.grids_dict[self.active_grid_pos] = dca_logic.initialize_grid(total_entry_exit_orders, 0, 0, 0, 0)
                    
                    # initialize db table rows
                    if (self.db.check_grid_row_exists(self.active_grid_pos) == False):
                        self.db.dcamp_create_new_grid_row(self.active_grid_pos)
                    if (self.db.check_active_orders_row_exists(self.active_grid_pos) == False):
                        self.db.initialize_active_orders_table(self.active_grid_pos, total_entry_exit_orders)
                    if (self.db.check_slipped_orders_row_exists(self.active_grid_pos) == False):
                        self.db.initialize_slipped_orders_table(self.active_grid_pos, total_entry_exit_orders)

                    print(f'\n !!!!!  Active Grid Pos: {self.active_grid_pos}  !!!!! \n')

                #TODO: Testing, remove:
                new_trend = False

            elif (init_existing_grid):
                print('init existing grid')
                self.active_grid_pos -= 1
                total_previous_pos_size = self.grids_dict[self.active_grid_pos - 1]['ttl_pos_size']
                grid = self.grids_dict[self.active_grid_pos]
                orders = grid['orders']
                grid_range_price = grid['range_price']
                grid_pos_size = grid['pos_size']
                init_existing_grid = False

            else:
                # TODO: Testing below grid price:
                last_price = self.api.last_price()
                if last_price < grid_range_price:
                    print('\nrange_price check: ')
                    print(f'range_price: {grid_range_price}')
                    print(f'last_price: {last_price}\n')
                    await asyncio.sleep(3)


                


                ttl_pos_size = self.api.get_position_size()
                grid_pos_size = self.determine_grid_pos_size(total_previous_pos_size, ttl_pos_size)

                await asyncio.sleep(0)
                # if filled orders, process:
                await self.update_secondary_orders(total_entry_exit_orders, secondary_entry_1_input_quantity, secondary_entry_2_input_quantity)

                await self.handle_initial_entry_exit_orders(profit_percent_1, profit_percent_2, grid_percent_range, main_pos_input_quantity, 
                                                                total_entry_exit_orders, total_exit_orders, total_entry_orders, 
                                                                    total_secondary_orders_1, secondary_orders_2, secondary_entry_1_input_quantity, 
                                                                        secondary_entry_2_input_quantity, grid_pos_size, ttl_pos_size)

    # update grid_pos_size in dict & db: 
    def determine_grid_pos_size(self, total_previous_pos_size, ttl_pos_size):
        global active_grid_pos
        global grids_dict

        stored_ttl_pos_size = self.grids_dict[self.active_grid_pos]['ttl_pos_size']
        if ttl_pos_size != stored_ttl_pos_size:
            self.grids_dict[self.active_grid_pos]['ttl_pos_size'] = ttl_pos_size
            self.db.replace_grid_row_value(self.active_grid_pos, 'ttl_pos_size', ttl_pos_size)
        
        grid_pos_size = ttl_pos_size - total_previous_pos_size
        pre_grid_pos_size = self.grids_dict[self.active_grid_pos]['pos_size']
        
        if (grid_pos_size != pre_grid_pos_size):
            self.grids_dict[self.active_grid_pos]['pos_size'] = grid_pos_size
            self.db.replace_grid_row_value(self.active_grid_pos, 'pos_size', grid_pos_size)

        return grid_pos_size

    # handle initial entry & exit orders: 
    async def handle_initial_entry_exit_orders (self, profit_percent_1, profit_percent_2, grid_percent_range, 
                                                main_pos_input_quantity, total_entry_exit_orders, total_exit_orders, total_entry_orders,
                                                     total_secondary_orders_1, secondary_orders_2, secondary_entry_1_input_quantity, 
                                                            secondary_entry_2_input_quantity, grid_pos_size, ttl_pos_size):
        global grids_dict
        global filled_orders_list

        # handle pos size
        grid_orders_list = dca_logic.get_orders_in_grid(self.active_grid_pos, self.api.get_orders())
        ids_and_quantity_dict = dca_logic.get_total_quantity_and_ids_dict(grid_orders_list, self.entry_side)
        total_exit_quantity = ids_and_quantity_dict['total_exit_quantity']

        if (total_exit_quantity == 0):
            print('\nclearing all order lists: \n')
            self.grids_dict[self.active_grid_pos] = dca_logic.initialize_grid(total_entry_exit_orders, 0, 0, grid_pos_size, ttl_pos_size)
            self.filled_orders_list = []

            previous_grid_pos_position = self.active_grid_pos - 1
            previous_grid_slipped_quantity = self.grids_dict[previous_grid_pos_position]['slipped_qty']

            slipped_quantity = grid_pos_size + previous_grid_slipped_quantity
            input_quantity = main_pos_input_quantity - slipped_quantity

            #TODO: Fix Input Quantity to handle leftover quantity from initializing without 0 grid_pos_size

            await self.create_main_pos_entry_exit('Market', self.entry_side, input_quantity, slipped_quantity,
                        profit_percent_2, total_exit_orders, 0, 0)
            await asyncio.sleep(0)

            main_pos_entry = self.grids_dict[self.active_grid_pos]['pos_price']

            # calculate and create open orders below Main pos:
            await self.create_secondary_orders(main_pos_entry, total_secondary_orders_1, secondary_orders_2, 
                        total_entry_orders, profit_percent_1, profit_percent_2, secondary_entry_1_input_quantity, 
                            secondary_entry_2_input_quantity)

            grid_range_price = calc().calc_percent_difference(self.entry_side, 'entry', main_pos_entry, grid_percent_range)
            self.db.replace_grid_row_value(self.active_grid_pos, 'grid_range_price', grid_range_price)

    async def determine_grid_and_trend(self, active_grid_pos: int, grid_range_price: float):
        determining_grid = True
        new_trend = False

        print('in determining_trend...')

        while(determining_grid):
            await asyncio.sleep(0)
            
            if (len(self.filled_orders_list) != 0):
                print('new filled order, breaking out of determine_grid')
                determining_grid = False

            else:
                last_price = await self.ws.get_last_price()
                print(f'last_price: {last_price}')
                if (active_grid_pos == 0) \
                    or (self.entry_side == 'Buy') and (last_price < grid_range_price) \
                    or ((self.entry_side == 'Sell') and (last_price > grid_range_price)):
                        print('price is outside grid')
                        print(f'last_price: {last_price} ---> grid_range: {grid_range_price}') 
                        new_trend = self.determine_new_trend()
                        determining_grid = False

        return new_trend

    def determine_new_trend(self) -> bool:
        #TODO: Implement
        new_trend = False
        print('determining new trend')
        return new_trend

    async def create_main_pos_entry_exit(self, order_type, entry_side, input_quantity, slipped_quantity, 
                                            profit_percent_2, total_exit_orders, main_pos_entry, active_exit_orders_len):
        global grids_dict
        entry_link_id = 'open'
        exit_link_id = 'main'

        if (input_quantity > 0):
            if (order_type == 'Market'):
                link_id = dca_logic.create_link_id(entry_link_id, self.active_grid_pos, 1)
                print('\ncreating Market main_pos entry: ')
                if (main_pos_entry != 0):
                    price = self.api.last_price()
                else:
                    price = main_pos_entry
                main_pos_order_link_id = self.api.place_order(price, 'Market', entry_side, input_quantity, 0, False, link_id)
                main_pos_exec_price = self.api.get_last_trade_price_record(main_pos_order_link_id)
                self.db.replace_grid_row_value(self.active_grid_pos, 'pos_price', main_pos_exec_price)
                self.grids_dict[self.active_grid_pos]['pos_price'] = main_pos_exec_price

                await asyncio.sleep(0.05)

                print('\ncreating main_pos exit: ')
            else:
                # force initial Main Pos limit close order
                print('\nforcing Limit main_pos entry: ')
                #TODO: Capture entry price for chasing limit in ws orders
                limit_price_difference = self.limit_price_difference
                await self.api.force_limit_order(entry_side, input_quantity, limit_price_difference, 0, False, entry_link_id)
        else:
            input_quantity = 0
        
        exit_input_quantity = input_quantity + slipped_quantity

        main_pos_price = self.grids_dict[self.active_grid_pos]['pos_price']

        print('\ncreating main pos exits: ')
        main_pos_entry = round(main_pos_price, 0)                
        total_num_orders = total_exit_orders
        input_quantity = exit_input_quantity
        input_quantity_2 = round(exit_input_quantity / total_num_orders, 0)
        start_price = main_pos_entry
        num_order = total_num_orders
        
        for x in range(total_num_orders):
            profit_percent = profit_percent_2 * num_order
            print(x)
            link_id = dca_logic.create_link_id(exit_link_id, self.active_grid_pos, x + 1)
            profit_percent = profit_percent_2 * num_order
            print(f'profit_percent {profit_percent}')
            print(f'num_order {num_order}')
            price = calc().calc_percent_difference(self.entry_side, 'exit', start_price, profit_percent)
            print(f'price: {price}')

            print(f'active_exit_orders: {active_exit_orders_len}, total_exit_orders: {total_exit_orders}')
            if (active_exit_orders_len < total_num_orders):
                print('adding exit order')
                self.api.place_order(price, 'Limit', self.exit_side, input_quantity, 0, True, link_id)
            else:
                print(f'exit_orders full: skipping')

            num_order -= 1
            active_exit_orders_len += 1
            input_quantity = input_quantity_2
            await asyncio.sleep(0)

    async def create_secondary_orders(self, initial_price, total_secondary_orders_1, \
        secondary_orders_2, total_entry_orders, profit_percent_1, profit_percent_2, \
            secondary_entry_1_input_quantity, secondary_entry_2_input_quantity):

        global grids_dict

        # create buy/sell orders dict: 
        orders_dict = dca_logic.get_grid_orders_dict(self.active_grid_pos, self.entry_side, self.api.get_orders())
        print('\n in create secondary orders \n')

        active_entry_orders_list = orders_dict[self.entry_side]
        active_entry_orders_len = len(active_entry_orders_list)

        # determine active & available entry orders
        available_entry_orders = total_entry_orders - active_entry_orders_len
        orders_to_cancel = active_entry_orders_len - total_entry_orders

        secondary_1_entry_price = initial_price
        secondary_2_entry_price = initial_price

        print(f'\ncurrent active entry orders: {active_entry_orders_len}')
        print(f'\navailable_entry_orders {available_entry_orders}')

        link_id_index = secondary_orders_2 + 1
        num_check = total_secondary_orders_1
        print('\nchecking for available entries: ')

        for x in range(orders_to_cancel):
            print(f"cancelling orders: {orders_to_cancel} ")
            order = active_entry_orders_list[0]
            order_id = order['order_id']
            self.grids_dict[self.active_grid_pos]['cancelled'].append(order_id)
            self.api.cancel_order(order_id)
            active_entry_orders_list.remove(order)

        active_orders_index = 0
        
        last_price = self.api.last_price()
        for x in range(total_entry_orders):
            x += 1

            side = self.entry_side
            if (x == num_check):
                num_check += total_secondary_orders_1
                input_quantity = secondary_entry_1_input_quantity
                link_name = 'pp_1'
                profit_percent = profit_percent_1
                entry_price = calc().calc_percent_difference(side, 'entry', secondary_1_entry_price, profit_percent)
                secondary_1_entry_price = entry_price
                secondary_2_entry_price = entry_price
            else: 
                input_quantity = secondary_entry_2_input_quantity
                link_name = 'pp_2'
                profit_percent = profit_percent_2
                entry_price = calc().calc_percent_difference(side, 'entry', secondary_2_entry_price, profit_percent)
                secondary_2_entry_price = entry_price

            if (side == 'Buy') and (last_price < entry_price):
                side = 'Sell'
            elif (side == 'Sell') and (last_price > entry_price):
                side = 'Buy'

            if (x <= available_entry_orders):
                print(f'\navailable_entry_orders: {available_entry_orders}\n')
                print(f'in fill available entry orders: x = {x}')
                link_id_index += 1
                link_id = dca_logic.create_link_id(link_name, self.active_grid_pos, link_id_index)
                self.api.place_order(entry_price, 'Limit', side, input_quantity, 0, False, link_id)
                await asyncio.sleep(0)

            else:
                print(f'\nactive_entry_orders len: {len(active_entry_orders_list)}')
                print(f'active_orders_index: {active_orders_index}')
                print(f'in update existing entry orders: x = {x}')
                order_id = orders_dict[side][active_orders_index]['order_id']
                self.api.change_order_price_size(entry_price, input_quantity, order_id)
                await asyncio.sleep(0)
                active_orders_index +=1


    #TODO: Address blank link order ID when manually closing order
    async def update_secondary_orders(self, total_entry_exit_orders, secondary_entry_1_input_quantity, 
                            secondary_entry_2_input_quantity):
        global filled_orders_list

        while (len(self.filled_orders_list) > 0):

            closed_order = self.filled_orders_list[0]
            self.filled_orders_list.remove(self.filled_orders_list[0])

            current_num_orders = len(self.api.get_orders())
            print(f'current_num_orders: {current_num_orders}\n')
            print(f'total_entry_exit_orders: {total_entry_exit_orders}')
            print('processing waiting available order: \n')

            # grid_pos = closed_order['grid_pos']
            order_pos = closed_order['order_pos']
            input_quantity = closed_order['input_quantity']
            profit_percent = closed_order['profit_percent']
            order_status = closed_order['order_status']
            price = closed_order['price']
            side = closed_order['side']
            # link_id = closed_order['order_link_id']
            link_name = closed_order['link_name']
            # leaves_qty = closed_order['leaves_qty']
            new_link_id = dca_logic.create_link_id(link_name, self.active_grid_pos, order_pos)


            # if (leaves_qty == 0):
            if (order_pos == 1):
                print('\n order_pos = 1 ... create trade record break:')
                await self.create_trade_record(closed_order)

            elif (current_num_orders == total_entry_exit_orders):
                print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                print('Too many orders, Skipping: ')
                print(f'current_num_orders: {current_num_orders}\n')
                print('')

            elif (order_status == 'PartiallyFilled'):
                print(f'processing partially filled, adding quantity to side: {side}')
                orders_list = self.api.get_orders()
                orders_dict = dca_logic.get_grid_orders_dict(self.active_grid_pos, self.entry_side, orders_list)
                if (side == self.entry_side):
                    order_to_update = orders_dict[self.exit_side][0]
                else:
                    order_to_update = orders_dict[self.entry_side][0]

                current_input_size = order_to_update['qty']
                new_input_quantity = current_input_size + input_quantity
                price = order_to_update['price']
                order_id = order_to_update['order_id']
                self.api.change_order_price_size(price, new_input_quantity, order_id)

            else:

                if (link_name == 'pp_1'):
                    input_quantity = secondary_entry_1_input_quantity
                elif (link_name == 'pp_2'):
                    input_quantity = secondary_entry_2_input_quantity
                else: 
                    # TODO: Confirm 'main' link name reposition order input quantity:
                    input_quantity = secondary_entry_2_input_quantity

                if (order_status == 'Cancelled'):
                    if (side == self.entry_side):
                        reduce_only = False
                    else:
                        reduce_only = True

                elif (side == self.entry_side):
                    #create new exit order upon entry close
                    print("\ncreating new exit order")
                    side = self.exit_side
                    price = calc().calc_percent_difference(self.entry_side, 'exit', price, profit_percent)
                    reduce_only = True

                elif (side == self.exit_side):
                    print("\nCreating Trade Record")
                    await self.create_trade_record(closed_order)            
                    #create new entry order upon exit close
                    print('creating new entry order')
                    side = self.entry_side
                    price = calc().calc_percent_difference(self.entry_side, 'entry', price, profit_percent)
                    reduce_only = False
                else:
                    print('something is wrong in update_secondary_orders')
                    print(pprint.pprint(closed_order))
                    sys.exit()

                self.api.place_order(price, 'Limit', side, input_quantity, 0, reduce_only, new_link_id)
                await asyncio.sleep(0)

            await asyncio.sleep(0)
            
            print(f'num filled_orders: {len(self.filled_orders_list)}')
            if (len(self.filled_orders_list) == 0):
                print('\n emptied orders list in update secondary orders\n')

    # async def get_last_price(self):
    #     last_price = self.api.last_price()

    #     while True:
    #         await asyncio.sleep(0)
    #         last_price = await self.ws.get_last_price()
    #         print(f'last_price: {last_price}')