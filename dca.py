import sys
sys.path.append("..")
from logic.calc import Calc as calc # type: ignore
from api.bybit_api import Bybit_Api # type: ignore
from api.bybit_ws import Bybit_WS # type: ignore
from strategies.dca_db import DCA_DB # type: ignore
from strategies import dca_logic # type: ignore
from strategies import trend # type: ignore
import asyncio
import pprint


# TODO LIST:
# fixing databasing new orders

class Strategy_DCA:

    def __init__(self, instance, api_key, api_secret, trade_id, strat_id, symbol, symbol_pair, key_input, \
        input_quantity, leverage, limit_price_difference, max_active_positions, entry_side):
        self.trade_id = trade_id
        self.strat_id = strat_id
        self.input_quantity = input_quantity
        self.max_active_positions = max_active_positions
        self.leverage = leverage
        self.key_input = key_input
        self.limit_price_difference = limit_price_difference
        self.entry_side = entry_side
        self.symbol = symbol

        if (entry_side == 'Buy'): self.exit_side = 'Sell'
        else: self.exit_side = 'Buy'

        #TODO: Strat db settings, move to class arguments:
        strat_name = 'dcamp'

        self.api = Bybit_Api(api_key, api_secret, symbol, symbol_pair, self.key_input)
        self.ws = Bybit_WS(api_key, api_secret, symbol_pair, True)
        self.db = DCA_DB(trade_id, strat_name, instance)

        self.api.set_leverage(self.leverage)
        
        self.filled_orders_list = []
        self.grids_dict = {}
        self.slipped_quantity = 0
        self.waiting_orders_list = []

        self.active_grid_pos = 0

        print('... Strategy_DCA initialized ...')

    # TODO: Fix main pos quantity thats savedw
    async def main(self):
        global grids_dict
        global active_grid_pos
        # TODO: Testing, remove
        test_strat = False
        # set initialize save state:
        initialize_save_state_tf = True
        # set reset all tables (will error if there is an active position!)
        reset_all_db_tables = False
        main_strat = None

        if test_strat: 
            main_strat = False
            initialize_save_state_tf = False
        else: 
            main_strat = True
        
        #Set Trade Values
        num_initial_entry_orders = 2
        num_initial_exit_orders = 2
        num_secondary_orders = 1

        num_initial_secondary_entry_orders = num_initial_entry_orders * num_secondary_orders
        num_initial_secondary_exit_orders = num_initial_exit_orders * num_secondary_orders
        print(f'num_initial_secondary_entry_orders: {num_initial_secondary_entry_orders}')
        print(f'num_initial_secondary_exit_orders: {num_initial_secondary_exit_orders}')
        profit_percent_1 = 0.0025
        profit_percent_2 = (profit_percent_1 / (num_secondary_orders + 2))
        print(f'profit_percent_1: {profit_percent_1}')
        print(f'profit_percent_2: {profit_percent_2}')

        num_total_entry_orders = num_initial_entry_orders + (num_initial_entry_orders * num_secondary_orders)
        num_total_exit_orders = num_initial_exit_orders + (num_initial_exit_orders * num_secondary_orders)
        print(f'num_total_entry_orders: {num_total_entry_orders}')
        print(f'num_total_exit_orders: {num_total_exit_orders}')
        total_entry_exit_orders = num_total_entry_orders + num_total_exit_orders
        print(f'total_entry_exit_orders: {total_entry_exit_orders}')
        # percent_rollover = 0.0

        #TODO: add percent calculation: 
        secondary_pos_1_percent_of_total_quantity = 0.5
        secondary_pos_2_percent_of_total_quantity = 0.5

        position_trade_quantity = self.input_quantity / self.max_active_positions
        print(f'position_trade_quantity: {position_trade_quantity}')

        secondary_pos_input_quantity_1 = round(position_trade_quantity * secondary_pos_1_percent_of_total_quantity, 0)
        secondary_pos_input_quantity_2 = round(position_trade_quantity * secondary_pos_2_percent_of_total_quantity, 0)
        
        print(f'secondary_pos_input_quantity_1: {secondary_pos_input_quantity_1}')
        print(f'secondary_pos_input_quantity_2: {secondary_pos_input_quantity_2}')

        num_input_quantity_1__orders = num_initial_entry_orders + num_initial_exit_orders
        num_input_quantity_2__orders = num_initial_secondary_entry_orders + num_initial_secondary_exit_orders

        input_quantity_1 = int(secondary_pos_input_quantity_1 / (num_input_quantity_1__orders))
        input_quantity_2 = int(secondary_pos_input_quantity_2 / (num_input_quantity_2__orders))
        print(f'input_quantity_1: {input_quantity_1}')
        print(f'input_quantity_2: {input_quantity_2}')

        main_pos_input_quantity = (num_initial_exit_orders * input_quantity_1) + \
                                    (num_initial_secondary_exit_orders * input_quantity_2)
        print(f'main_pos_input_quantity: {main_pos_input_quantity}')

        input_quantity_1_trade_quantity = input_quantity_1 * num_input_quantity_1__orders
        input_quantity_2_trade_quantity = input_quantity_2 * num_input_quantity_2__orders

        grid_pos_ttl_trade_qty = input_quantity_1_trade_quantity + input_quantity_2_trade_quantity
        print(f'grid_pos_ttl_trade_qty: {grid_pos_ttl_trade_qty}')

        # initialize grids dict:
        self.grids_dict[self.active_grid_pos] = dca_logic.initialize_grid(total_entry_exit_orders, 0, 0, 0, 0)

        if (reset_all_db_tables):
            self.db.initialize_all_tables(dlt_table_t_f=True, create_table_t_f=True, 
                                            total_entry_exit_orders=total_entry_exit_orders)

        if main_strat:
            print(f'\nin main_strat\n')

            self.db.dcamp_create_new_grids_table(total_entry_exit_orders)

            # initialize from saved state:
            if (initialize_save_state_tf):
                await self.initialize_saved_state(total_entry_exit_orders, profit_percent_1, profit_percent_2, grid_pos_ttl_trade_qty)

                # removes unused rows from DB (active / slipped / grid) / clears filled:
                if (reset_all_db_tables == False):
                    self.db.initialize_non_peristent_tables(True, True)
                    self.db.dcamp_remove_unused_active_orders_rows(self.active_grid_pos)
                    self.db.dcamp_remove_slipped_orders_rows(self.active_grid_pos)
                    self.db.dcamp_remove_unused_grids_rows(self.active_grid_pos)

            # start main tasks
            task_ping_timer = asyncio.create_task(self.ws.ping(0.5, 15))
            # task_pos_info = asyncio.create_task(self.get_pos_size())
            task_collect_orders = asyncio.create_task(self.collect_orders())
            task_process_waiting_orders = asyncio.create_task(self.store_new_changed_filled_orders(profit_percent_1, profit_percent_2, total_entry_exit_orders))
            task_start_dca_multi_position = asyncio.create_task(self.dca_multi_position(num_initial_entry_orders, num_initial_exit_orders, num_total_entry_orders, 
                                                                num_secondary_orders, profit_percent_1, profit_percent_2, total_entry_exit_orders, 
                                                                main_pos_input_quantity, input_quantity_1, input_quantity_2))


            await task_ping_timer
            # await task_pos_info
            await task_collect_orders
            await task_process_waiting_orders   
            await task_start_dca_multi_position

        # # # # # # TEST # # # # # #
        if test_strat:
            
            print(" !!!!! TESTING !!!!")


            # await self.initialize_saved_state(total_entry_exit_orders, profit_percent_1, profit_percent_2, num_total_entry_orders)

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

    # initialize from saved state:
    async def initialize_saved_state(self, total_entry_exit_orders, profit_percent_1, profit_percent_2, grid_pos_ttl_trade_qty):
        global active_grid_pos
        global grids_dict
        global slipped_quantity

        print(' ... loading saved state ... ')

        orders_list = self.api.get_orders()
        
        num_active_orders = len(orders_list)
        position_size = self.api.get_position_size()

        print(f'\nactive position size: {position_size}')
        print(f'num_active_orders: {num_active_orders}\n')

        if (position_size == 0):
            print('no existing state \n')

        else:
            print('... processing ...')
            active_grid_pos = 0
            grid_row_check = True
            ttl_pos_size = 0

            previous_grid_range_price = 0
            grid_range_price = 0
            active_grid_range_price = 0
            
            last_price = self.api.last_price()
            
            # fill active orders lists & price_list from DB:
            while (grid_row_check):
                active_grid_pos += 1
                grid_row_check = self.db.check_grid_row_exists(active_grid_pos)
                print(f'\ngrid_pos_check: {active_grid_pos}')
                print(f'grid_row_check: {grid_row_check}')
                
                ttl_pos_size = self.api.get_position_size()
                
                if (grid_row_check):
                    orders_list = self.api.get_orders()
                    previous_grid_range_price = grid_range_price
                    grid_info = self.db.get_grid_row_dict(active_grid_pos, total_entry_exit_orders)
                    price_list = grid_info['price_list']
                    grid_range_price = grid_info['grid_range_price']
                    pos_price = grid_info['pos_price']

                    main_exit_order_link_id = grid_info['main_exit_order_link_id']

                    self.grids_dict[active_grid_pos] = dca_logic.initialize_grid(total_entry_exit_orders, pos_price, grid_range_price, 0, 0)
                    self.grids_dict[active_grid_pos]['grid_prices'] = price_list
                    self.grids_dict[active_grid_pos]['main_exit_order_link_id'] = main_exit_order_link_id

                    grid_orders_list = dca_logic.get_orders_in_grid(active_grid_pos, orders_list)

                    grid_orders_list_len = len(grid_orders_list)


                    print(f'grids_orders_list_len: {grid_orders_list_len}')

                    if (grid_orders_list_len > 0):
                        for order in grid_orders_list:
                            updated_order = dca_logic.get_updated_order_info(order, profit_percent_1, profit_percent_2)
                            order_pos = updated_order['order_pos']
                            self.grids_dict[active_grid_pos]['active'][order_pos] = updated_order
                            self.db.dcamp_replace_active_order(updated_order)
                    
                    if (previous_grid_range_price == 0):
                        self.active_grid_pos = 1
                        active_grid_range_price = grid_range_price
                    elif ((self.entry_side == 'Buy') and (last_price < previous_grid_range_price)) \
                        or (self.entry_side == 'Sell') and (last_price > previous_grid_range_price):
                        self.active_grid_pos = active_grid_pos
                        active_grid_range_price = grid_range_price


            print(f'determined grid_range_price: {active_grid_range_price}')
            print(f'determined active_grid_pos: {self.active_grid_pos}')

            # calc/update ttl_exit_qty & grid_pos_size
            grid_pos_check = 0
            ttl_pos_size = self.api.get_position_size()
            ttl_previous_pos_size = 0
            grid_pos_size = 0
            total_exit_qty = 0
            print(f'\nupdating grid_pos_size:')
            if (self.active_grid_pos > 0):
                while (grid_pos_check < self.active_grid_pos):
                    grid_pos_check += 1
                    print(f'grid: {grid_pos_check}')
                    if (ttl_pos_size > grid_pos_ttl_trade_qty):
                        grid_pos_size = grid_pos_ttl_trade_qty
                    else:
                        grid_pos_size = ttl_pos_size

                    self.grids_dict[grid_pos_check]['pos_size'] = grid_pos_size
                    self.db.replace_grid_row_value(grid_pos_check, 'pos_size', grid_pos_size)
                    ttl_previous_pos_size += grid_pos_size
                    self.db.replace_grid_row_value(grid_pos_check, 'ttl_pos_size', ttl_previous_pos_size)
                    self.grids_dict[grid_pos_check]['ttl_pos_size'] = ttl_previous_pos_size
                    ttl_pos_size -= grid_pos_size


                    grid_orders_list = dca_logic.get_orders_in_grid(grid_pos_check, orders_list)
                    grid_orders_dict = dca_logic.get_sorted_orders_dict(self.entry_side, grid_orders_list)
                    grid_exit_qty = grid_orders_dict['total_exit_quantity']
                    total_exit_qty += grid_exit_qty
                    self.db.replace_grid_row_value(grid_pos_check, 'ttl_exit_qty', total_exit_qty)
                            
            ttl_pos_size = ttl_previous_pos_size

            # place slipped exit quantity in closest exit order
            await self.check_grid_orders(self.active_grid_pos, grid_range_price, total_entry_exit_orders, 
                                    ttl_pos_size, profit_percent_1)

        self.move_orders_below_grids(self.active_grid_pos)
        self.update_slipped_exit_qty(self.api.get_position_size(), profit_percent_1)
           


    #TODO: Add Trade Name to order / db
    def create_trade_record(self, closed_trade):
        print('\ncreating trade record: ')

        profit_percent = round(closed_trade['profit_percent'], 8)
        exit_price = closed_trade['price']
        entry_price = exit_price * (1 - profit_percent)
        input_quantity = closed_trade['input_quantity']
        last_price = self.api.last_price()
        dollar_gain = round(input_quantity * profit_percent, 8)
        coin_gain =  round(dollar_gain / last_price, 8)

        self.db.commit_trade_record(coin_gain, dollar_gain, entry_price, exit_price, profit_percent, \
            input_quantity)

    async def dca_multi_position(self, num_initial_entry_orders, num_initial_exit_orders, num_total_entry_orders, num_secondary_orders, profit_percent_1, 
                                    profit_percent_2, total_entry_exit_orders, main_pos_input_quantity, input_quantity_1, input_quantity_2):

        global filled_orders_list
        global grids_dict
        global active_grid_pos

        # determine_grid_size, currently by largest set profit * orders:
        #TODO: optimize grid_range_margin margin

        grid_range_margin = profit_percent_1
        grid_percent_range = (profit_percent_1 * num_total_entry_orders) + grid_range_margin

        grid_row_dict = self.db.get_grid_row_dict(self.active_grid_pos, total_entry_exit_orders)
        grid_range_price = grid_row_dict['grid_range_price']

        previous_grid_row_dict = self.db.get_grid_row_dict(self.active_grid_pos - 1, total_entry_exit_orders)
        previous_grid_range_price = previous_grid_row_dict['grid_range_price']
        total_previous_pos_size = previous_grid_row_dict['ttl_pos_size']

        ttl_pos_size = self.api.get_position_size()
        grid_pos_size = self.determine_grid_pos_size(total_previous_pos_size, ttl_pos_size)

        print(f'\nprevious_grid_range_price: {previous_grid_range_price}')
        print(f'total_previous_pos_size: {total_previous_pos_size}\n')

        waiting_state = True
        outside_existing_grid = False
        confirmed_trend = False

        #TODO: Handle secondary grids immediately below active grid to avoid waiting states, or move secondary orders

        last_price = self.api.last_price()

        if ((grid_range_price != 0) and (self.entry_side == 'Buy') and (last_price > grid_range_price)) \
            or ((grid_range_price != 0) and (self.entry_side == 'Sell') and  (last_price < grid_range_price)):
            waiting_state = False

        if ((grid_range_price != 0) and (self.entry_side == 'Buy') and (last_price < grid_range_price)) \
            or ((grid_range_price != 0) and (self.entry_side == 'Sell') and  (last_price > grid_range_price)):
            outside_existing_grid = True

        while (True):
            grid_range_price = self.grids_dict[self.active_grid_pos]['range_price']
            print(f'waiting_state: {waiting_state}\n')

            print(f'\nactive_grid_pos: {self.active_grid_pos}')
            print(f'waiting for price update:')
            last_price = self.api.last_price()
            print(f'last_price: {last_price}')
            print(f'outside_existing_grid: {outside_existing_grid}')
            print(f'previous_grid_range_price: {previous_grid_range_price}')
            print(f'grid_range_price: {grid_range_price}')

            if (waiting_state):
                print(f'\nin waiting_state')
                
                # determine trend
                last_price = await self.ws.get_last_price()
                confirmed_trend = trend.determine_new_trend(self.symbol, self.entry_side, self.max_active_positions, self.active_grid_pos)
                print(f'confirmed_trend: {confirmed_trend}')

                if (confirmed_trend):
                    print('initializing new grid: ')
                    confirmed_trend = False

                    # initialize new grid:
                    previous_grid_range_price = self.grids_dict[self.active_grid_pos]['range_price']
                    total_previous_pos_size = self.grids_dict[self.active_grid_pos]['ttl_pos_size']
                    self.active_grid_pos += 1
                    print(f'\nupdated active_grid_pos: {self.active_grid_pos} \n')
                    
                    grid_range_price = 0
                    self.grids_dict[self.active_grid_pos] = dca_logic.initialize_grid(total_entry_exit_orders, 0, grid_range_price, 0, 0)
                    
                    # initialize db table rows
                    if (self.db.check_grid_row_exists(self.active_grid_pos) == False):
                        self.db.dcamp_create_new_grid_row(self.active_grid_pos, total_entry_exit_orders)
                    if (self.db.check_active_orders_row_exists(self.active_grid_pos) == False):
                        self.db.initialize_active_orders_table(self.active_grid_pos, total_entry_exit_orders)
                    if (self.db.check_slipped_orders_row_exists(self.active_grid_pos) == False):
                        self.db.initialize_slipped_orders_table(self.active_grid_pos, total_entry_exit_orders)

                    waiting_state = False

                elif ((outside_existing_grid) and (self.entry_side == 'Buy') and (last_price > grid_range_price)) \
                    or ((outside_existing_grid) and (self.entry_side == 'Sell') and (last_price < grid_range_price)):
                    # init_existing_grid:
                    print(f'\nreturning to grid')
                    print(f'active_grid_pos from {self.active_grid_pos}\n')
                    outside_existing_grid = False
                    waiting_state = False

            if (waiting_state == False):

                if ((grid_range_price != 0) and (self.entry_side == 'Buy') and (last_price < grid_range_price)) \
                    or ((grid_range_price != 0) and (self.entry_side == 'Sell') and (last_price > grid_range_price)):
                    # outside grid determined: 
                    print(f'\noutside of grid_range_price: ')
                    print(f'range_price: {grid_range_price}')
                    print(f'last_price: {last_price}\n')
                    if (self.entry_side == 'Buy'):
                        range_price_difference = grid_range_price - last_price
                    else:
                        range_price_difference = last_price - grid_range_price
                    print(f'range_price_difference: {range_price_difference}')
                    waiting_state = True
                    outside_existing_grid = True

                    ttl_pos_size = self.api.get_position_size()
                    grid_pos_size = self.determine_grid_pos_size(total_previous_pos_size, ttl_pos_size)
                    await self.check_grid_orders(self.active_grid_pos, grid_range_price, total_entry_exit_orders, ttl_pos_size, 
                                                profit_percent_1)
                    

                elif (self.entry_side == 'Buy') and (last_price > previous_grid_range_price) and (previous_grid_range_price != 0) \
                    or (self.entry_side == 'Sell') and (last_price < previous_grid_range_price):
                    # init_existing_grid:
                    print(f'\n\n\n\nentering previous grid...')
                    print(f'init existing grid')
                    self.active_grid_pos -= 1
                    print(f'changed active_grid_pos to: {self.active_grid_pos}')
                    if (self.active_grid_pos > 0):
                        previous_grid_range_price = self.grids_dict[self.active_grid_pos - 1]['range_price']
                        total_previous_pos_size = self.grids_dict[self.active_grid_pos - 1]['ttl_pos_size'] 
                    else:
                        previous_grid_range_price = 0
                        total_previous_pos_size = 0

                    grid = self.grids_dict[self.active_grid_pos]
                    grid_range_price = grid['range_price']
                    grid_pos_size = grid['pos_size']
                    outside_existing_grid = False
                    self.move_orders_below_grids(self.active_grid_pos)
                    self.db.dcamp_remove_unused_grids_rows(self.active_grid_pos)
                    ttl_pos_size = self.api.get_position_size()
                    self.update_slipped_exit_qty(ttl_pos_size, profit_percent_1)

                else:
                    # inside grid determined: 
                    waiting_state = False

                    orders_list = self.api.get_orders()
                    grid_orders_list = dca_logic.get_orders_in_grid(self.active_grid_pos, orders_list)
                    ids_and_quantity_dict = dca_logic.get_sorted_orders_dict(self.entry_side, grid_orders_list)
                    grid_exit_quantity = ids_and_quantity_dict['total_exit_quantity']
                    grid_entry_quantity = ids_and_quantity_dict['total_entry_quantity']

                    grid_pos_size = self.determine_grid_pos_size(total_previous_pos_size, ttl_pos_size)

                    if (grid_exit_quantity == 0):
                        print(f'\ntotal_exit_quantity == 0\n')
                        self.move_orders_below_grids(self.active_grid_pos - 1)
                        await self.handle_initial_entry_exit_orders(profit_percent_1, profit_percent_2, grid_percent_range, main_pos_input_quantity, 
                                                                    total_entry_exit_orders, num_total_entry_orders, num_secondary_orders, 
                                                                        input_quantity_1, input_quantity_2, grid_pos_size, ttl_pos_size, 
                                                                            num_initial_entry_orders, num_initial_exit_orders, 
                                                                                previous_grid_range_price)
                        ttl_pos_size = self.api.get_position_size()
                        self.update_slipped_exit_qty(ttl_pos_size, profit_percent_1)

                    elif (grid_entry_quantity == 0):
                        print(f'\ntotal_entry_quantity == 0\n')
                        await asyncio.sleep(6)


                    else:
                        await asyncio.sleep(2)
                        ttl_pos_size = self.api.get_position_size()
                        # ttl_pos_size = await self.ws.get_pos_size()

                    await self.handle_slipped_orders(self.active_grid_pos)
                    #TODO: CHECK check_grid_orders
                    # await self.check_grid_orders(self.active_grid_pos, grid_pos_size, grid_range_price, total_entry_exit_orders, ttl_pos_size, profit_percent_1)

                await asyncio.sleep(0)
                    

    def move_orders_below_grids(self, grid_pos):
        last_price = self.api.last_price()
        orders_list = self.api.get_orders()
        check_price = round(calc().calc_percent_difference(self.entry_side, 'entry', last_price, 0.70), 2)
        new_price = round(calc().calc_percent_difference(self.entry_side, 'entry', last_price, 0.75), 2)
        print(f'new_price: {new_price}')
        print(f'check_price: {check_price}')
        for order in orders_list:
            order_link_id = order['order_link_id']
            order_price = float(order['price'])
            extracted_link_id = dca_logic.extract_link_id(order_link_id)
            order_grid_pos = extracted_link_id['grid_pos']
            print(f'order_price: {order_price}')
            print(f'order_grid_pos: {order_grid_pos}')
            print(f'order_link_id: {order_link_id}')
            if (order_grid_pos > grid_pos):
                if ((self.entry_side == 'Buy') and (order_price > check_price)) \
                    or ((self.entry_side == 'Sell') and (order_price < check_price)):
                    print(f'\nchanging order price for order_grid_pos: {order_grid_pos}')
                    self.api.change_order_price(new_price, order_link_id)

    # update grid_pos_size in dict & db: 
    def determine_grid_pos_size(self, total_previous_pos_size, ttl_pos_size):
        global active_grid_pos
        global grids_dict

        if (total_previous_pos_size != None) and (ttl_pos_size != None):
            print(f'\nactive_grid_pos: {self.active_grid_pos}')
            stored_ttl_pos_size = self.grids_dict[self.active_grid_pos]['ttl_pos_size']
            if ttl_pos_size != stored_ttl_pos_size:
                self.grids_dict[self.active_grid_pos]['ttl_pos_size'] = ttl_pos_size
                self.db.replace_grid_row_value(self.active_grid_pos, 'ttl_pos_size', ttl_pos_size)
            
            pre_grid_pos_size = self.grids_dict[self.active_grid_pos]['pos_size']
            grid_pos_size = ttl_pos_size - total_previous_pos_size
            
            if (grid_pos_size != pre_grid_pos_size):
                self.grids_dict[self.active_grid_pos]['pos_size'] = grid_pos_size
                self.db.replace_grid_row_value(self.active_grid_pos, 'pos_size', grid_pos_size)

            return grid_pos_size

        else:
            return total_previous_pos_size

    # handle initial entry & exit orders: 
    async def handle_initial_entry_exit_orders (self, profit_percent_1, profit_percent_2, grid_percent_range, main_pos_input_quantity, 
                                                    total_entry_exit_orders, num_total_entry_orders, num_secondary_orders, input_quantity_1, 
                                                        input_quantity_2, grid_pos_size, ttl_pos_size, num_initial_entry_orders, 
                                                            num_initial_exit_orders, previous_grid_range_price):
        global grids_dict
        global filled_orders_list



        # determine if exit above previous_grid_range_price
        # TODO: Determine if exit price will go above previous grid_range entry using force limit entries
        exit_order_range_percent = (profit_percent_1 * num_initial_exit_orders)
        exit_order_range_price = calc().calc_percent_difference(self.entry_side, 'exit', self.api.last_price(), exit_order_range_percent)

        if ((self.entry_side == 'Buy') and (previous_grid_range_price != 0) and (exit_order_range_price >= previous_grid_range_price)) \
            or (self.entry_side == 'Sell') and (previous_grid_range_price != 0) and (exit_order_range_price <= previous_grid_range_price):
            print(f'\nskipping create order due to previous_grid_range_price conflict')
            print(f'exit_order_range_price: {exit_order_range_price}')
            print(f'previous_grid_range_price: {previous_grid_range_price}\n')
            await asyncio.sleep(5)

        else:
            print('\nclearing all order lists: \n')
            self.grids_dict[self.active_grid_pos] = dca_logic.initialize_grid(total_entry_exit_orders, 0, 0, grid_pos_size, ttl_pos_size)
            self.filled_orders_list = []

            input_quantity = main_pos_input_quantity

            #TODO: Fix Input Quantity to handle leftover quantity from initializing without 0 grid_pos_size

            main_pos_entry_price = await self.create_main_pos_entry('Market', self.entry_side, input_quantity, 0, ttl_pos_size)

            await asyncio.sleep(0)

            # calculate and create open orders below Main pos:

            grid_price_dict = dca_logic.generate_multi_order_price_list(profit_percent_1, profit_percent_2, num_initial_entry_orders, num_initial_exit_orders, 
                                                                    num_secondary_orders, main_pos_entry_price, input_quantity_1, input_quantity_2, self.entry_side)
            self.grids_dict[self.active_grid_pos]['grid_prices'] = grid_price_dict['price_list']
            self.db.dcamp_update_grid_prices(self.active_grid_pos, grid_price_dict['price_list'])
            
            grid_prices = grid_price_dict['price_list']
            await self.create_secondary_orders(grid_prices, total_entry_exit_orders, num_total_entry_orders, grid_pos_size)

            grid_range_price = calc().calc_percent_difference(self.entry_side, 'entry', main_pos_entry_price, grid_percent_range)
            print(f'\nmain_pos_entry_price: {main_pos_entry_price}')
            print(f'grid_range_price: {grid_range_price}\n')
            self.db.replace_grid_row_value(self.active_grid_pos, 'grid_range_price', grid_range_price)
            self.grids_dict[self.active_grid_pos]['range_price'] = grid_range_price

    async def create_main_pos_entry(self, order_type, entry_side, input_quantity, main_pos_entry, ttl_pos_size):
        global grids_dict
        entry_link_id = 'open'
        main_pos_exec_price = 0
        print(f'\ncreating main_pos entry, order_type: {order_type} ')

        pre_pos_size = ttl_pos_size
        print(f'pre_pos_size: {pre_pos_size}')
        
        if (input_quantity > 0):
            pos_size_check = True
            while (pos_size_check):
                print(f'create_main_pos_entry order_check: {pos_size_check}')
                if (order_type == 'Market'):
                    link_id = dca_logic.create_link_id(entry_link_id, self.active_grid_pos, 1)
                    if (main_pos_entry == 0):
                        price = self.api.last_price()
                    else:
                        price = main_pos_entry
                    main_pos_order_link_id = self.api.place_order(price, 'Market', entry_side, input_quantity, 0, False, link_id)
                    main_pos_exec_price = self.api.get_last_trade_price_record(main_pos_order_link_id)

                    if (main_pos_exec_price == 0.0):
                        main_pos_exec_price = self.api.last_price()

                    self.db.replace_grid_row_value(self.active_grid_pos, 'pos_price', main_pos_exec_price)
                    self.grids_dict[self.active_grid_pos]['pos_price'] = main_pos_exec_price

                    await asyncio.sleep(0.05)

                else:
                    # force initial Main Pos limit close order
                    #TODO: Capture entry price for chasing limit in ws orders
                    limit_price_difference = self.limit_price_difference
                    await self.api.force_limit_order(entry_side, input_quantity, limit_price_difference, 0, False, entry_link_id)
                    main_pos_exec_price = 0 # TODO: Fix <----

                post_pos_size = self.api.get_position_size()
                print(f'post_pos_size: {post_pos_size}')
                if (post_pos_size > pre_pos_size):
                    pos_size_check = False
                    print(f'create_main_pos_entry pos_size check: {pos_size_check}')
            
        else:
            print(f'skipping in create_main_pos_entry, input_quantity: {input_quantity}')

        print(f'main_pos_exec_price: {main_pos_exec_price}')
        return main_pos_exec_price
        

    async def create_secondary_orders(self, grid_prices: dict, total_entry_exit_orders: int, num_total_entry_orders: int, grid_pos_size: int):

        global grids_dict

        # create buy/sell orders dict: 

        orders_list = self.api.get_orders()
        grid_orders_list = dca_logic.get_orders_in_grid(self.active_grid_pos, orders_list)
        orders_dict = dca_logic.get_sorted_orders_dict(self.entry_side, grid_orders_list)
        print(f'\n in create secondary orders \n')

        active_entry_orders_list = orders_dict[self.entry_side]
        active_entry_orders_len = len(active_entry_orders_list)
        active_exit_orders_list = orders_dict[self.exit_side]
        active_exit_orders_len = len(active_exit_orders_list)
        num_total_active_orders = active_entry_orders_len + active_exit_orders_len
        num_total_available_orders = total_entry_exit_orders - num_total_active_orders

        # determine active & available entry orders

        quantity_check = 0
        available_orders_index = 0
        active_orders_index = 0

        for k in grid_prices:
            print(f'last_price: {self.api.last_price()}')
            print(f'\nin create secondary orders: {k}')
            value = grid_prices[k]
            print(f'\nvalue in grid_prices (update_orders)')
            print(value)
            side = value['side']
            link_name = value['pp']

            
            if (k > active_exit_orders_len):

                input_quantity = value['input_quantity']
                

                if (side == None):
                    if (quantity_check < grid_pos_size):
                        side = self.exit_side
                    else:
                        side = self.entry_side

                if (side == self.entry_side):
                    price = value['entry']
                    reduce_only = False
                elif (side == self.exit_side):
                    quantity_check += input_quantity
                    price = value['exit']
                    reduce_only = True

                if (available_orders_index < num_total_available_orders):
                    print(f'available_orders_index: {available_orders_index}')
                    print(f'num_total_available_orders: {num_total_available_orders}')
                    link_id = dca_logic.create_link_id(link_name, self.active_grid_pos, k)
                    order_link_id = self.api.place_order(price, 'Limit', side, input_quantity, 0, reduce_only, link_id)
                    available_orders_index += 1

                    # capture main_exit_order_link_id:
                    if (k == 1):
                        self.grids_dict[self.active_grid_pos]['main_exit_order_link_id'] = order_link_id
                        self.db.replace_grid_row_value(self.active_grid_pos, 'main_exit_order_link_id', order_link_id)
                    
                    await asyncio.sleep(0)

                elif (active_orders_index < num_total_active_orders):
                    orders_dict_side_len = len(orders_dict[side])
                    print(f'active_orders_index: {active_orders_index}')
                    print(f'num_total_active_orders: {num_total_active_orders}')
                    if (orders_dict_side_len == 0) or (active_orders_index > orders_dict_side_len):
                        self.api.place_order(price, 'Limit', side, input_quantity, 0, reduce_only, link_id)
                    else:
                        order_id = orders_dict[side][active_orders_index]['order_id']
                        self.api.change_order_price_size(price, input_quantity, order_id)
                    active_orders_index += 1
                    await asyncio.sleep(0)

                else:
                    print(f'not enough available orders: {k}')

            else:
                print(f'udpate secondary orders, k: {k}, is not greater than num active orders')

        print(f'\nTEST VIEW Initial Orders:')
        print(pprint.pprint(self.api.get_orders()))


# TODO: fix creating duplicate pos orders
    async def check_grid_orders(self, grid_pos, grid_range_price, total_entry_exit_orders, ttl_pos_size, profit_percent_1):
        orders_list = self.api.get_orders()
        all_orders_dict = dca_logic.get_sorted_orders_dict(self.entry_side, orders_list)
        total_exit_quantity = all_orders_dict['total_exit_quantity']
        all_exit_orders = all_orders_dict[self.exit_side]

        ttl_exit_qty_check = self.grids_dict[self.active_grid_pos]['ttl_exit_qty']
        if (total_exit_quantity != ttl_exit_qty_check):
            self.grids_dict[self.active_grid_pos]['ttl_exit_qty'] = ttl_exit_qty_check
            self.db.replace_grid_row_value(self.active_grid_pos, 'ttl_exit_qty', total_exit_quantity)


        print(f'\nchecking grid orders: ')
        
        await asyncio.sleep(0.5)
        filled_orders_list_len = len(self.filled_orders_list)
        waiting_orders_list_len = len(self.waiting_orders_list)

        print(f'total_entry_exit_orders: {total_entry_exit_orders}')
        print(f'filled_orders_list_len: {filled_orders_list_len}')
        print(f'waiting_orders_list_len: {waiting_orders_list_len}\n')

        grid_pos_check = 0

        if (filled_orders_list_len == 0) and (waiting_orders_list_len == 0):
            while (grid_pos_check < grid_pos):
                grid_pos_check += 1
                print(f'\nchecking orders in grid: {grid_pos_check}')

                grid_orders_list = dca_logic.get_orders_in_grid(grid_pos_check, orders_list)
                grid_orders_list_len = len(grid_orders_list)
                grids_dict = self.grids_dict[grid_pos_check]
                grid_pos_size = grids_dict['pos_size']
                quantity_dict = dca_logic.get_sorted_orders_dict(self.entry_side, grid_orders_list)
                grid_exit_quantity = quantity_dict['total_exit_quantity']

                if (grid_exit_quantity < grid_pos_size) or (grid_orders_list_len < total_entry_exit_orders):
                    active_order_keys = []
                    active_orders_dict = {}
                    low_order_keys = []
                    low_order_ids = {}

                    grid_pos_size_check = grid_pos_size
                    price_list = self.grids_dict[grid_pos]['grid_prices']

                    for order in grid_orders_list:
                        print(pprint.pprint(order))
                        price = float(order['price'])
                        order_link_id = order['order_link_id']
                        extracted_order_link_id = dca_logic.extract_link_id(order_link_id)
                        order_pos = extracted_order_link_id['order_pos']
                        name = extracted_order_link_id['name']

                        if ((self.entry_side == 'Buy') and (price > grid_range_price)) \
                            or ((self.entry_side == 'Sell') and (price < grid_range_price)):
                            active_order_keys.append(order_pos)
                            active_orders_dict[order_pos] = {}
                            active_orders_dict[order_pos]['order_id'] = order['order_id']
                            active_orders_dict[order_pos]['side'] = order['side']
                            active_orders_dict[order_pos]['qty'] = order['qty']
                            active_orders_dict[order_pos]['price'] = price
                            active_orders_dict[order_pos]['order_link_id'] = order_link_id
                            print('test!!!!')
                            
                        else:  
                            low_order_keys.append(order_pos)
                            low_order_ids[order_pos] = {}
                            low_order_ids[order_pos]['order_id'] = order['order_id']

                    print(f'\nprinting active_orders_dict:')
                    print(pprint.pprint(active_orders_dict))
                    print(f'printing active_order_keys:')
                    print(active_order_keys)

                    for key in price_list:
                        last_price = self.api.last_price()
                        value = price_list[key]
                        pl_qty = value['input_quantity']
                        name = value['pp']

                        if key in active_order_keys:
                            order_info = active_orders_dict[key]
                            actual_qty = order_info['qty']
                            order_id = order_info['order_id']
                            order_link_id = order_info['order_link_id']
                            side = order_info['side']
                            if (actual_qty < pl_qty):
                                self.api.change_order_size(pl_qty, order_link_id)

                            if (side == self.exit_side):
                                grid_pos_size_check -= pl_qty

                        elif key not in active_order_keys:
                            print(f'key {key} not in list')
                            qty = value['input_quantity']

                            new_link_id = dca_logic.create_link_id(name, grid_pos_check, key)
                            if (grid_pos_size_check > 0):
                                price = value['exit']
                                grid_pos_size_check -= pl_qty
                                if ((self.entry_side == 'Buy') and (last_price < price)) \
                                    or ((self.entry_side == 'Sell') and (last_price > price)):
                                    print(f'creating new exit order')
                                    if (ttl_exit_qty_check + qty) < ttl_pos_size:
                                        print(f'skipping create exit order, not enough pos size')
                                    elif (ttl_exit_qty_check + qty) > ttl_pos_size:
                                        temp_qty = 0
                                        for order in all_exit_orders:
                                            order_link_id = order['order_link_id']
                                            extracted_order_link_id = dca_logic.extract_link_id(order_link_id)
                                            order_pos = extracted_order_link_id['order_pos']
                                            order_base_input_quantity = price_list[order_pos]['input_quantity']
                                            qty_check = order['qty']
                                            if (qty_check > order_base_input_quantity):
                                                qty_difference = qty_check - order_base_input_quantity
                                                if (qty_difference >= qty):
                                                    changed_qty = qty_check - qty
                                                elif (qty_difference < qty):
                                                    changed_qty = qty_check - qty_difference

                                                temp_qty += changed_qty
                                                print(f'changing exit order qty: {changed_qty}')
                                                self.api.change_order_size(changed_qty, order_link_id)

                                                if (temp_qty >= qty):
                                                    break
                                    
                                        order_link_id = self.api.place_order(price, 'Limit', self.exit_side, qty, 0, True, new_link_id)
                                    
                                        if (key == 1):
                                            self.db.replace_grid_row_value(grid_pos_check, 'main_exit_order_link_id', order_link_id)
                                        
                                        ttl_exit_qty_check += qty

                                else:
                                    print(f'unable to create exit order in grid')

                            else:
                                price = value['entry']
                                if ((self.entry_side == 'Buy') and (last_price > price)) \
                                    or ((self.entry_side == 'Sell') and (last_price < price)):
                                    
                                    if (key in low_order_keys):
                                        order_id = low_order_ids[key]
                                        print(f'changing order to create entry order in grid')
                                        self.api.change_order_price_size(price, qty, order_id)
                                    else:
                                        print(f'creating new order entry order in grid')
                                        self.api.place_order(price, 'Limit', self.entry_side, qty, 0, False, new_link_id)
                                else:
                                    print('unable to create entry order in grid')
                
                #TODO: Update / add back
                # self.update_slipped_exit_qty(ttl_pos_size, profit_percent_1)

    def update_slipped_exit_qty(self, ttl_pos_size, profit_percent_1):
        filled_orders_list_len = len(self.filled_orders_list)

        # check exit quantity, move slipped to closest exit order:
        print(f'\nexit quantity check')
        orders_list = self.api.get_orders()
        quantity_dict = dca_logic.get_sorted_orders_dict(self.entry_side, orders_list)
        ttl_exit_quantity = quantity_dict['total_exit_quantity']

        print(f'grid_pos_size: {ttl_pos_size}, grid_exit_quantity: {ttl_exit_quantity}')
        exit_qty_difference = ttl_pos_size - ttl_exit_quantity
        print(f'exit_qty_difference: {exit_qty_difference}')
        if (filled_orders_list_len == 0) and (exit_qty_difference > 0):
            
            orders_dict = dca_logic.get_sorted_orders_dict(self.entry_side, orders_list)
            exit_orders = orders_dict[self.exit_side]
            exit_orders_len = len(exit_orders)

            if (exit_orders_len > 0):
                order_to_update = exit_orders[0]
                order_link_id = order_to_update['order_link_id']
                print(f'updating exit order: {order_link_id}')
                input_quantity = order_to_update['qty'] + exit_qty_difference
                price = order_to_update['price']
                order_id = order_to_update['order_id']
                self.api.change_order_price_size(price, input_quantity, order_id) 

            else:
                print(f'no available exit orders, creating new order:')
                last_price = self.api.last_price()
                entry_side = self.entry_side
                price = calc().calc_percent_difference(entry_side, 'exit', self.api.get_active_position_entry_price(), profit_percent_1)

                if ((entry_side == 'Buy') and (last_price >= price)) \
                    or ((entry_side == 'Sell') and (last_price <= price)):
                    price = calc().calc_percent_difference(entry_side, 'exit', last_price, profit_percent_1)

                link_id = dca_logic.create_link_id('exit', 0, 1)
                self.api.place_order(price, 'Limit', self.exit_side, exit_qty_difference, 0, True, link_id)



    # collect orders via ws
    async def collect_orders(self):
        global waiting_orders_list

        print('collecting orders')
        while True:
            order = await self.ws.get_order()
            self.waiting_orders_list.append(order[0])
            await asyncio.sleep(0)


    # TODO: Add checks for confirming active orders
    async def store_new_changed_filled_orders(self, profit_percent_1, profit_percent_2, total_entry_exit_orders):
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

                        else:
                            order = dca_logic.get_updated_order_info(waiting_order, profit_percent_1, profit_percent_2)
                            self.waiting_orders_list.remove(waiting_order)

                            grid_pos = order['grid_pos']
                            if (grid_pos != self.active_grid_pos):
                                print('!! grid_pos: outside current grid !!')
                            
                            order_status = order['order_status']
                            link_name = order['link_name']

                            if (link_name == 'open'):
                                print(f'skip store order: {link_name}')

                            else:
                                if (order_status == 'Filled') or (order_status == 'PartiallyFilled'):
                                    self.filled_orders_list.append(order)
                                    self.db.dcamp_create_new_order_row(order)

                                elif (order_status == 'New'):
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
                                    print(f'\nOrder was Cancelled\n')
                                    self.grids_dict[grid_pos]['slipped'].append(order)

                                else:
                                    print('invalid order status')

                    # if filled orders, process:
                    await asyncio.sleep(0)
                    await self.update_secondary_orders(total_entry_exit_orders)

        except Exception as e:
            print("an exception occured - {}".format(e))
            sys.exit()
        

    #TODO: Address blank link order ID when manually closing order
    async def update_secondary_orders(self, total_entry_exit_orders):
        global filled_orders_list

        while (len(self.filled_orders_list) > 0):

            closed_order = self.filled_orders_list[0]
            self.filled_orders_list.remove(self.filled_orders_list[0])

            orders_list = self.api.get_orders()
            grid_orders_list = dca_logic.get_orders_in_grid(self.active_grid_pos, orders_list)
            grid_orders_list_len = len(grid_orders_list)

            current_num_orders = len(orders_list)
            print(f'current_num_orders: {current_num_orders}\n')
            print(f'total_entry_exit_orders: {total_entry_exit_orders}')
            print('processing waiting available order: \n')

            order_status = closed_order['order_status']
            order_pos = closed_order['order_pos']
            side = closed_order['side']

            if (order_pos == 1):
                self.create_trade_record(closed_order)

            elif (current_num_orders == total_entry_exit_orders):
                print('Too many orders, Skipping: ')
                print(f'current_num_orders: {current_num_orders}\n')
                print('')

            else:

                if (order_status == 'PartiallyFilled'):
                    print(f'processing partially filled, adding quantity to side: {side}')
                    input_quantity = closed_order['input_quantity']
                    orders_list = self.api.get_orders()
                    grid_orders_list = dca_logic.get_orders_in_grid(self.active_grid_pos, orders_list)
                    orders_dict = dca_logic.get_sorted_orders_dict(self.entry_side, orders_list)
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
                    side = closed_order['side']

                    grid_price_list = self.grids_dict[self.active_grid_pos]['grid_prices']
                    grid_price_list_len = len(grid_price_list)

                    if(grid_price_list_len > 0):
                        order_details = grid_price_list[order_pos]
                        input_quantity = order_details['input_quantity']
                        link_name = order_details['pp']
                        new_link_id = dca_logic.create_link_id(link_name, self.active_grid_pos, order_pos)

                        if (order_status == 'Cancelled'):
                            price = closed_order['price']
                            if (side == self.entry_side):
                                reduce_only = False
                            else:
                                reduce_only = True

                        elif (side == self.entry_side):
                            #create new exit order upon entry close
                            print("\ncreating new exit order")
                            side = self.exit_side
                            price = order_details['exit']
                            reduce_only = True

                        elif (side == self.exit_side):
                            print("\nCreating Trade Record")
                            self.create_trade_record(closed_order)            
                            #create new entry order upon exit close
                            print('creating new entry order')
                            side = self.entry_side
                            price = order_details['entry']
                            reduce_only = False
                        else:
                            print('something is wrong in update_secondary_orders')
                            print(pprint.pprint(closed_order))
                            sys.exit()

                        if (grid_orders_list_len < total_entry_exit_orders):
                            grid_orders_list = dca_logic.get_orders_in_grid(self.active_grid_pos, self.api.get_orders())
                            grid_orders_dict = dca_logic.get_sorted_orders_dict(self.entry_side, grid_orders_list)
                            entry_orders = grid_orders_dict[self.entry_side]

                            active_order_pos_list = []
                            for order in entry_orders:
                                order_link_id = order['order_link_id']
                                extracted_link_id = dca_logic.extract_link_id(order_link_id)
                                active_order_pos = extracted_link_id['order_pos']
                                if (active_order_pos == order_pos):
                                    order_id = order['order_id']
                                    active_order_pos_list.append(order_id)

                            if ((len(active_order_pos_list)) > 0):
                                order_id = active_order_pos_list[0]
                                self.api.change_order_price_size(price, input_quantity, order_id)
                            else:
                                self.api.place_order(price, 'Limit', side, input_quantity, 0, reduce_only, new_link_id)
                        else:
                            orders_len_difference = total_entry_exit_orders - grid_orders_list_len
                            print(f'update_secondary_orders difference: {orders_len_difference}')

            await asyncio.sleep(0)

            print(f'num filled_orders: {len(self.filled_orders_list)}')
            if (len(self.filled_orders_list) == 0):
                print('\n emptied orders list in update secondary orders\n')
            

    async def handle_slipped_orders(self, grid_pos):
        global grids_dict

        slipped_orders = self.grids_dict[grid_pos]['slipped']
        active_order_keys = []

        last_price = self.api.last_price()
        if (len(slipped_orders) > 0):
            print(f'num slipped orders: {len(slipped_orders)}')

            orders_list = self.api.get_orders()
            grid_orders_list = dca_logic.get_orders_in_grid(grid_pos, orders_list)
            
            for order in grid_orders_list:
                order_link_id = order['order_link_id']
                extracted_link_id = dca_logic.extract_link_id(order_link_id)
                order_pos = extracted_link_id['order_pos']
                active_order_keys.append(order_pos)

            for order in self.grids_dict[grid_pos]['slipped']:
                order_pos = order['order_pos']
                if order_pos in active_order_keys:
                    print(f'order_pos key {order_pos} already active')
                    self.grids_dict[grid_pos]['slipped'].remove(order)
                else:
                    side = order['side']
                    price = order['price']
                    name = order['link_name']
                    qty = order['input_quantity']
                    new_link_id = dca_logic.create_link_id(name, grid_pos, order_pos)

                    if (side == 'Buy') and (last_price > price) \
                        or (side == 'Sell') and (last_price < price):
                        print(f'processing slipped order: ')
                        self.grids_dict[grid_pos]['slipped'].remove(order)
                        self.api.place_order(price, 'Limit', side, qty, 0, False, new_link_id)

                await asyncio.sleep(0)

