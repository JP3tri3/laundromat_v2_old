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
        reset_trade_records = False
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
        profit_percent_1 = 0.00075
        profit_percent_2 = (profit_percent_1 / (num_secondary_orders + 2))
        print(f'profit_percent_1: {profit_percent_1}')
        print(f'profit_percent_2: {profit_percent_2}')

        num_total_entry_orders = num_initial_entry_orders + (num_initial_entry_orders * num_secondary_orders)
        num_total_exit_orders = num_initial_exit_orders + (num_initial_exit_orders * num_secondary_orders)
        print(f'num_total_entry_orders: {num_total_entry_orders}')
        print(f'num_total_exit_orders: {num_total_exit_orders}')
        total_entry_exit_orders = num_total_entry_orders + num_total_exit_orders
        print(f'total_entry_exit_orders: {total_entry_exit_orders}')

        #TODO: add percent calculation: 
        secondary_pos_1_percent_of_total_quantity = 0.5
        secondary_pos_2_percent_of_total_quantity = 0.5

        position_trade_quantity = self.input_quantity / self.max_active_positions
        print(f'position_trade_quantity: {position_trade_quantity}')

        secondary_pos_input_quantity_1 = round(position_trade_quantity * secondary_pos_1_percent_of_total_quantity, 0)
        secondary_pos_input_quantity_2 = round(position_trade_quantity * secondary_pos_2_percent_of_total_quantity, 0)
        
        print(f'secondary_pos_input_quantity_1: {secondary_pos_input_quantity_1}')
        print(f'secondary_pos_input_quantity_2: {secondary_pos_input_quantity_2}')

        num_input_quantity_1_orders = num_initial_entry_orders + num_initial_exit_orders
        num_input_quantity_2_orders = num_initial_secondary_entry_orders + num_initial_secondary_exit_orders

        input_quantity_1 = int(secondary_pos_input_quantity_1 / (num_input_quantity_1_orders))
        input_quantity_2 = int(secondary_pos_input_quantity_2 / (num_input_quantity_2_orders))
        print(f'input_quantity_1: {input_quantity_1}')
        print(f'input_quantity_2: {input_quantity_2}')

        main_pos_input_quantity = (num_initial_exit_orders * input_quantity_1) + \
                                    (num_initial_secondary_exit_orders * input_quantity_2)
        print(f'main_pos_input_quantity: {main_pos_input_quantity}')

        input_quantity_1_trade_quantity = input_quantity_1 * num_input_quantity_1_orders
        input_quantity_2_trade_quantity = input_quantity_2 * num_input_quantity_2_orders

        grid_pos_ttl_trade_qty = input_quantity_1_trade_quantity + input_quantity_2_trade_quantity
        print(f'grid_pos_ttl_trade_qty: {grid_pos_ttl_trade_qty}')

        # initialize grids dict:
        self.grids_dict[self.active_grid_pos] = dca_logic.initialize_grid(total_entry_exit_orders, 0, 0, 0, 0)

        if (reset_all_db_tables):
            self.db.initialize_all_tables(dlt_table_t_f=True, create_table_t_f=True)
        
        if (reset_trade_records):
            self.db.create_trade_records_table(True, True)

        if main_strat:
            print(f'\nin main_strat\n')

            self.db.dcamp_create_new_grids_table(total_entry_exit_orders)

            # initialize from saved state:
            if (initialize_save_state_tf):
                await self.initialize_saved_state(total_entry_exit_orders, profit_percent_1, profit_percent_2, grid_pos_ttl_trade_qty, input_quantity_1)

                # removes unused rows from DB (active / slipped / grid) / clears filled:
                if (reset_all_db_tables == False):
                    self.db.initialize_non_peristent_tables(True, True)
                    self.db.dcamp_remove_unused_active_orders_rows(self.active_grid_pos)
                    self.db.dcamp_remove_slipped_orders_rows(self.active_grid_pos)
                    self.db.dcamp_remove_unused_grids_rows(self.active_grid_pos)

            # start main tasks
            task_ping_timer = asyncio.create_task(self.ws.ping(0.5, 5))
            task_collect_orders = asyncio.create_task(self.collect_orders())
            task_process_waiting_orders = asyncio.create_task(self.store_new_changed_filled_orders(profit_percent_1, profit_percent_2, total_entry_exit_orders))
            task_start_dca_multi_position = asyncio.create_task(self.dca_multi_position(num_initial_entry_orders, num_initial_exit_orders, num_total_entry_orders, 
                                                                num_secondary_orders, profit_percent_1, profit_percent_2, total_entry_exit_orders, 
                                                                main_pos_input_quantity, input_quantity_1, input_quantity_2))

            await asyncio.gather(task_ping_timer, task_process_waiting_orders, task_start_dca_multi_position, task_collect_orders)

        # # # # # # TEST # # # # # #
        if test_strat:
            
            print(" !!!!! TESTING !!!!")

            
            print(self.api.wallet_result())

    # initialize from saved state:
    async def initialize_saved_state(self, total_entry_exit_orders, profit_percent_1, profit_percent_2, grid_pos_ttl_trade_qty,
                                        input_quantity_1):
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


            print(f'\ndetermined grid_range_price: {active_grid_range_price}')
            print(f'determined active_grid_pos: {self.active_grid_pos}\n')

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
                    self.grids_dict[self.active_grid_pos]['ttl_previous_pos_size'] = ttl_previous_pos_size
                    ttl_pos_size -= grid_pos_size


                    grid_orders_list = dca_logic.get_orders_in_grid(grid_pos_check, orders_list)
                    grid_orders_dict = dca_logic.get_sorted_orders_dict(self.entry_side, grid_orders_list, last_price)
                    grid_exit_qty = grid_orders_dict[self.exit_side]['ttl_qty']
                    total_exit_qty += grid_exit_qty
                    self.db.replace_grid_row_value(grid_pos_check, 'ttl_exit_qty', total_exit_qty)
                            
            ttl_pos_size = ttl_previous_pos_size

            # place slipped exit quantity in closest exit order
            await self.check_grid_orders(self.active_grid_pos, total_entry_exit_orders, profit_percent_1, input_quantity_1)

        self.move_orders_below_grids(self.active_grid_pos)
        self.update_slipped_exit_qty(self.api.get_position_size(), profit_percent_1)
        self.update_grids_list_db()
           
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

        global grids_dict
        global active_grid_pos
        global waiting_orders_list

        #TODO: optimize grid_range_margin margin

        grid_range_margin = profit_percent_1
        grid_percent_range = (grid_range_margin * num_initial_entry_orders) + (grid_range_margin * (num_initial_exit_orders + 1))

        grid_row_dict = self.db.get_grid_row_dict(self.active_grid_pos, total_entry_exit_orders)
        grid_range_price = grid_row_dict['grid_range_price']

        previous_grid_row_dict = self.db.get_grid_row_dict(self.active_grid_pos - 1, total_entry_exit_orders)
        previous_grid_range_price = previous_grid_row_dict['grid_range_price']
        ttl_previous_pos_size = previous_grid_row_dict['ttl_pos_size']
        self.grids_dict[self.active_grid_pos]['ttl_previous_pos_size'] = ttl_previous_pos_size

        ttl_pos_size = self.api.get_position_size()
        grid_pos_size = self.determine_grid_pos_size(ttl_previous_pos_size, ttl_pos_size)

        print(f'\nprevious_grid_range_price: {previous_grid_range_price}')
        print(f'ttl_previous_pos_size: {ttl_previous_pos_size}\n')

        waiting_state = True
        outside_existing_grid = False
        confirmed_trend = False

        last_price = self.api.last_price()

        if ((grid_range_price != 0) and (self.entry_side == 'Buy') and (last_price > grid_range_price)) \
            or ((grid_range_price != 0) and (self.entry_side == 'Sell') and  (last_price < grid_range_price)):
            waiting_state = False

        if ((grid_range_price != 0) and (self.entry_side == 'Buy') and (last_price < grid_range_price)) \
            or ((grid_range_price != 0) and (self.entry_side == 'Sell') and  (last_price > grid_range_price)):
            outside_existing_grid = True

        while (True):
            grid_range_price = self.grids_dict[self.active_grid_pos]['range_price']

            print(f'\nactive_grid_pos: {self.active_grid_pos}')
            print(f'waiting for price update:')
            last_price = await self.ws.get_last_price()
            await asyncio.sleep(0)
            print(f'last_price: {last_price}\n')

            print(f'status checks:')
            print(f'waiting_state: {waiting_state}\n')
            print(f'outside_existing_grid: {outside_existing_grid}')
            print(f'previous_grid_range_price: {previous_grid_range_price}')
            print(f'grid_range_price: {grid_range_price}\n')

            if (waiting_state):
                print(f'\nin waiting_state')
                
                confirmed_trend = trend.determine_new_trend(self.symbol, self.entry_side, self.max_active_positions, self.active_grid_pos)
                print(f'confirmed_trend: {confirmed_trend}')

                if (confirmed_trend):
                    print('initializing new grid: ')
                    confirmed_trend = False

                    # initialize new grid:
                    previous_grid_range_price = self.grids_dict[self.active_grid_pos]['range_price']
                    ttl_previous_pos_size = self.grids_dict[self.active_grid_pos]['ttl_pos_size']
                    self.grids_dict[self.active_grid_pos]['ttl_previous_pos_size'] = ttl_previous_pos_size
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
                    grid_pos_size = self.determine_grid_pos_size(ttl_previous_pos_size, ttl_pos_size)
                    await self.check_grid_orders(self.active_grid_pos, total_entry_exit_orders, profit_percent_1, input_quantity_1)
                    self.waiting_orders_list = []
                    await self.clear_slipped_orders()

                elif (self.entry_side == 'Buy') and (last_price > previous_grid_range_price) and (previous_grid_range_price != 0) \
                    or (self.entry_side == 'Sell') and (last_price < previous_grid_range_price):
                    # init_existing_grid:
                    print(f'\n\n\n\nentering previous grid...')
                    print(f'init existing grid')
                    self.active_grid_pos -= 1
                    print(f'changed active_grid_pos to: {self.active_grid_pos}')
                    if (self.active_grid_pos > 0):
                        previous_grid_range_price = self.grids_dict[self.active_grid_pos - 1]['range_price']
                        ttl_previous_pos_size = self.grids_dict[self.active_grid_pos - 1]['ttl_pos_size'] 
                        
                    else:
                        previous_grid_range_price = 0
                        ttl_previous_pos_size = 0

                    self.grids_dict[self.active_grid_pos]['ttl_previous_pos_size'] = ttl_previous_pos_size

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

                    grid_exit_quantity = self.grids_dict[self.active_grid_pos]['exit_qty']
                    grid_entry_quantity = self.grids_dict[self.active_grid_pos]['entry_qty']
                    grid_pos_size = self.grids_dict[self.active_grid_pos]['pos_size']
                    ttl_pos_size = self.grids_dict[self.active_grid_pos]['ttl_pos_size']

                    if (grid_exit_quantity == 0):
                        print(f'\ntotal_exit_quantity == 0\n')
                        self.move_orders_below_grids(self.active_grid_pos - 1)
                        self.waiting_orders_list = []
                        await self.handle_initial_entry_exit_orders(profit_percent_1, profit_percent_2, grid_percent_range, main_pos_input_quantity, 
                                                                    total_entry_exit_orders, num_total_entry_orders, num_secondary_orders, 
                                                                        input_quantity_1, input_quantity_2, grid_pos_size, ttl_pos_size, 
                                                                            num_initial_entry_orders, num_initial_exit_orders, 
                                                                                previous_grid_range_price)
                        
                        self.update_slipped_exit_qty(ttl_pos_size, profit_percent_1)

                    elif (grid_entry_quantity == 0):
                        print(f'\ntotal_entry_quantity == 0\n')

                    await self.handle_slipped_orders(self.active_grid_pos)

                await asyncio.sleep(0)

    def move_orders_below_grids(self, grid_pos):
        last_price = self.api.last_price()
        orders_list = self.api.get_orders()
        check_price = round(calc().calc_percent_difference(self.entry_side, 'entry', last_price, 0.70), 2)
        new_price = round(calc().calc_percent_difference(self.entry_side, 'entry', last_price, 0.75), 2)
        for order in orders_list:
            order_link_id = order['order_link_id']
            order_id = order['order_id']
            order_price = float(order['price'])
            extracted_link_id = dca_logic.extract_link_id(order_link_id)
            order_grid_pos = extracted_link_id['grid_pos']    
            if (order_grid_pos > grid_pos):
                if ((self.entry_side == 'Buy') and (order_price > check_price)) \
                    or ((self.entry_side == 'Sell') and (order_price < check_price)):
                    self.api.change_order_price_size(new_price, 1, order_id)

    # handle initial entry & exit orders: 
    async def handle_initial_entry_exit_orders (self, profit_percent_1, profit_percent_2, grid_percent_range, main_pos_input_quantity, 
                                                    total_entry_exit_orders, num_total_entry_orders, num_secondary_orders, input_quantity_1, 
                                                        input_quantity_2, grid_pos_size, ttl_pos_size, num_initial_entry_orders, 
                                                            num_initial_exit_orders, previous_grid_range_price):
        global grids_dict



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
            await self.clear_slipped_orders()
            self.grids_dict[self.active_grid_pos] = dca_logic.initialize_grid(total_entry_exit_orders, 0, 0, grid_pos_size, ttl_pos_size)

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
            self.update_grids_list_db()

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
        grid_orders_dict = dca_logic.get_sorted_orders_dict(self.entry_side, grid_orders_list, self.api.last_price())
        print(f'\n in create secondary orders \n')

        active_entry_orders_list = grid_orders_dict['active_orders']
        active_entry_orders_len = len(active_entry_orders_list)
        active_exit_orders_list = grid_orders_dict[self.exit_side]['sorted']
        active_exit_orders_len = len(active_exit_orders_list)
        num_total_active_orders = active_entry_orders_len + active_exit_orders_len
        num_total_available_orders = total_entry_exit_orders - num_total_active_orders
        inactive_orders = grid_orders_dict['inactive_orders']
        # determine active & available entry orders

        quantity_check = 0
        available_orders_index = 0
        # active_orders_index = 0

        for k in grid_prices:
            print(f'last_price: {self.api.last_price()}')
            print(f'\nin create secondary orders: {k}')
            value = grid_prices[k]
            print(value)

            print(f'k: {k}')
            print(f'active_exit_orders_len: {active_exit_orders_len}')

            if (k > active_exit_orders_len):
                side = value['side']
                link_name = value['pp']
                link_id = dca_logic.create_link_id(link_name, self.active_grid_pos, k)
                input_quantity = value['input_quantity']
                
                print(f'\nk > active_exit_orders_len\n')


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
                    if (side == self.entry_side) and (k in inactive_orders):
                        order_id = inactive_orders[k]['order_id']
                        self.api.change_order_price_size(price, input_quantity, order_id)
                    else:
                        order_link_id = self.api.place_order(price, 'Limit', side, input_quantity, 0, reduce_only, link_id)
                        available_orders_index += 1

                    # capture main_exit_order_link_id:
                    if (k == 1):
                        self.grids_dict[self.active_grid_pos]['main_exit_order_link_id'] = order_link_id
                        self.db.replace_grid_row_value(self.active_grid_pos, 'main_exit_order_link_id', order_link_id)

                    await asyncio.sleep(0)

                else:
                    print(f'not enough available orders: {k}')

            else:
                print(f'udpate secondary orders, k: {k}, is not greater than num active orders')

# TODO: fix creating duplicate pos orders
    async def check_grid_orders(self, grid_pos, total_entry_exit_orders, profit_percent_1, input_quantity_1):
        global grids_dict

        print(f'\nchecking grid orders: ')
        
        await asyncio.sleep(0.2)
        waiting_orders_list_len = len(self.waiting_orders_list)

        print(f'total_entry_exit_orders: {total_entry_exit_orders}')
        print(f'waiting_orders_list_len: {waiting_orders_list_len}\n')

        if (waiting_orders_list_len == 0):
            last_price = self.api.last_price()
            orders_list = self.api.get_orders()            
            grid_pos_check = grid_pos

            while (grid_pos_check > 0):
                
                print(f'\nchecking orders in grid: {grid_pos_check}')
                grid_orders_list = dca_logic.get_orders_in_grid(grid_pos_check, orders_list)
                grid_orders_list_len = len(grid_orders_list)
                grids_dict = self.grids_dict[grid_pos_check]
                grid_pos_size = grids_dict['pos_size']
                grid_orders_dict = dca_logic.get_sorted_orders_dict(self.entry_side, grid_orders_list, last_price)
                
                grid_exit_quantity = grid_orders_dict[self.exit_side]['ttl_qty']
                grid_exit_quantity_check = 0
                grid_exit_qty_to_orders_check = 0

                grid_exit_orders = grid_orders_dict[self.exit_side]
                grid_active_exit_order_positions = grid_exit_orders['positions']
                grid_active_exit_orders_sorted = grid_exit_orders['sorted']
                grid_active_entry_orders = grid_orders_dict['active_orders']
                grid_inactive_entry_orders = grid_orders_dict['inactive_orders']
                

                if (grid_exit_quantity < grid_pos_size) or (grid_orders_list_len < total_entry_exit_orders):

                    price_list = self.grids_dict[grid_pos]['grid_prices']

                    for key in price_list:
                        print(f'\nchecking key: {key}')
                        value = price_list[key]
                        pl_qty = value['input_quantity']
                        name = value['pp']
                        grid_exit_qty_to_orders_check += pl_qty

                        if (grid_exit_quantity_check < grid_pos_size):
                            print(f'checking exit_orders')
                            if (key in grid_active_exit_order_positions):
                                print(f'key in grid_active_exit_order_positions')
                                order = grid_active_exit_order_positions[key]
                                qty = order['qty']
                                if (qty > pl_qty):
                                    order_link_id = order['order_link_id']
                                    self.api.change_order_size(pl_qty, order_link_id)
                                    qty_difference = qty - pl_qty
                                    qty -= qty_difference
                            elif (key not in grid_active_exit_order_positions):
                                print(f'key not in grid_active_exit_order_positions')
                                pl_price = value['exit']
                                side = self.exit_side
                                if ((self.entry_side == 'Buy') and (last_price < pl_price)) \
                                    or ((self.entry_side == 'Sell') and (last_price > pl_price)):
                                    new_link_id = dca_logic.create_link_id(name, grid_pos_check, key)
                                    self.api.place_order(pl_price, 'Limit', side, pl_qty, 0, True, new_link_id)
                                    qty = pl_qty
                                else:
                                    qty = grid_pos_size - grid_exit_quantity_check
                                    grid_orders_list = dca_logic.get_orders_in_grid(grid_pos_check, self.api.get_orders())
                                    grid_orders_dict = dca_logic.get_sorted_orders_dict(self.entry_side, grid_orders_list, last_price)
                                    grid_active_exit_orders_sorted = grid_exit_orders['sorted']

                                    if (pl_qty == input_quantity_1):
                                        name = 'pp_1'
                                    else:
                                        name = 'pp_2'
                                    
                                    print(f'adding order to slipped orders list for grid pos: {self.active_grid_pos}')

                                    order = {
                                        'price': pl_price,
                                        'input_quantity': pl_qty,
                                        'side': side,
                                        'link_name': name,
                                        'order_pos': key, 
                                        'grid_pos': grid_pos
                                    }

                                    self.grids_dict[self.active_grid_pos]['slipped'].append(order)

                                    if (len(grid_active_exit_orders_sorted) > 0):
                                        order_to_update = grid_active_exit_orders_sorted[0]
                                        order_link_id = order_to_update['order_link_id']
                                        self.api.change_order_size(qty, order_link_id)
                                    else:
                                        pl_main_exit_price = price_list[1]['exit']
                                        new_link_id = dca_logic.create_link_id('pp_1', grid_pos_check, 1)
                                        if ((self.entry_side == 'Buy') and (last_price < pl_main_exit_price)) \
                                            or ((self.entry_side == 'Sell') and (last_price > pl_main_exit_price)):
                                            price = pl_main_exit_price
                                        else:
                                            price = calc().calc_percent_difference(self.entry_side, 'exit', last_price, profit_percent_1)
                                        
                                        self.api.place_order(price, 'Limit', self.exit_side, qty, 0, True, new_link_id)
                            
                            grid_exit_quantity_check += qty
                            print(f'grid_exit_quantity_check: {grid_exit_quantity_check}')
                            print(f'grid_pos_size: {grid_pos_size}')

                        elif (grid_exit_qty_to_orders_check >= grid_pos_size):
                            print(f'checking entry_orders')
                            print(f'grid_exit_qty_to_orders_check >= grid_pos_size')
                            print(f'grid_exit_qty_to_orders_check: {grid_exit_qty_to_orders_check}')
                            print(f'grid_pos_size: {grid_pos_size}')
                            side = self.entry_side

                            if (key not in grid_active_entry_orders):
                                print(f'key not in grid_active_entry_orders')
                                pl_price = value['entry']
                                if (self.entry_side == 'Buy') and (last_price > pl_price) \
                                    or (self.entry_side == 'Sell') and (last_price < pl_price):
                                    if (key in grid_inactive_entry_orders):
                                        order_to_update = grid_inactive_entry_orders[key]
                                        order_id = order_to_update['order_id']
                                        self.api.change_order_price_size(pl_price, pl_qty, order_id)
                                    else:
                                        new_link_id = dca_logic.create_link_id(name, grid_pos_check, key)
                                        self.api.place_order(pl_price, 'Limit', self.entry_side, pl_qty, 0, False, new_link_id)
                                else:
                                    order = {
                                        'price': pl_price,
                                        'input_quantity': pl_qty,
                                        'side': side,
                                        'link_name': name,
                                        'order_pos': key,
                                        'grid_pos': grid_pos
                                    }
                                    self.grids_dict[self.active_grid_pos]['slipped'].append(order)

                grid_pos_check -= 1

                #TODO: Update / add back
                # self.update_slipped_exit_qty(ttl_pos_size, profit_percent_1)

    def update_slipped_exit_qty(self, ttl_pos_size, profit_percent_1):
        waiting_orders_list_len = len(self.waiting_orders_list)

        # check exit quantity, move slipped to closest exit order:
        print(f'\nexit quantity check')
        orders_list = self.api.get_orders()
        last_price = self.api.last_price()
        quantity_dict = dca_logic.get_sorted_orders_dict(self.entry_side, orders_list, last_price)
        ttl_exit_quantity = quantity_dict[self.exit_side]['ttl_qty']

        print(f'grid_pos_size: {ttl_pos_size}, grid_exit_quantity: {ttl_exit_quantity}')
        exit_qty_difference = ttl_pos_size - ttl_exit_quantity
        print(f'exit_qty_difference: {exit_qty_difference}')
        if (waiting_orders_list_len == 0) and (exit_qty_difference > 0):
            
            orders_dict = dca_logic.get_sorted_orders_dict(self.entry_side, orders_list, last_price)
            exit_orders = orders_dict[self.exit_side]['sorted']
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
            await asyncio.sleep(0)
            order = await self.ws.get_order()
            print(pprint.pprint(order))
            self.waiting_orders_list.append(order[0])
            
    # TODO: Add checks for confirming active orders
    async def store_new_changed_filled_orders(self, profit_percent_1, profit_percent_2, total_entry_exit_orders):
        global grids_dict
        global waiting_orders_list

        try:
            while True:
                await asyncio.sleep(0.5)
                if (self.waiting_orders_list != []):
                    for waiting_order in self.waiting_orders_list:
                        order_link_id = waiting_order['order_link_id']
                        if (order_link_id == ''):
                            print(f'skip store oder: {order_link_id}, empty order_link_id')

                        else:
                            order = dca_logic.get_updated_order_info(waiting_order, profit_percent_1, profit_percent_2)

                            grid_pos = order['grid_pos']
                            if (grid_pos != self.active_grid_pos):
                                print('!! grid_pos: outside current grid !!')
                            
                            order_status = order['order_status']
                            link_name = order['link_name']

                            if (link_name == 'open'):
                                print(f'skip store order: {link_name}, pos open order\n')

                            else:
                                if (order_status == 'Filled') or (order_status == 'PartiallyFilled'):
                                    self.db.dcamp_create_new_order_row(order)
                                    await self.update_secondary_orders(total_entry_exit_orders, order)

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
                                    print(f'\nOrder was Cancelled, adding to slipped\n')
                                    self.grids_dict[grid_pos]['slipped'].append(order)
                                    self.db.dcamp_replace_slipped_order(order)

                                else:
                                    print('invalid order status')

                        self.waiting_orders_list.remove(waiting_order)
                        await asyncio.sleep(0)

                    self.update_grids_list_db()


                    

        except Exception as e:
            print("an exception occured in store_new_changed_filled_orders - {}".format(e))
        
    def update_grids_list_db(self):
        print(f'\nupdate_grids_list_db')
        ttl_previous_pos_size = self.grids_dict[self.active_grid_pos]['ttl_previous_pos_size']
        ttl_pos_size = self.api.get_position_size()
        orders_list = self.api.get_orders()
        last_price = self.api.last_price()

        self.determine_grid_pos_size(ttl_previous_pos_size, ttl_pos_size)
        self.update_grid_entry_exit_quantity(orders_list, last_price)
        self.update_ttl_exit_qty_info(orders_list, last_price)

    def determine_grid_pos_size(self, ttl_previous_pos_size, ttl_pos_size):
        global active_grid_pos
        global grids_dict

        if (ttl_previous_pos_size != None) and (ttl_pos_size != None):
            stored_ttl_pos_size = self.grids_dict[self.active_grid_pos]['ttl_pos_size']
            if ttl_pos_size != stored_ttl_pos_size:
                self.grids_dict[self.active_grid_pos]['ttl_pos_size'] = ttl_pos_size
                self.db.replace_grid_row_value(self.active_grid_pos, 'ttl_pos_size', ttl_pos_size)
            
            pre_grid_pos_size = self.grids_dict[self.active_grid_pos]['pos_size']
            grid_pos_size = ttl_pos_size - ttl_previous_pos_size
            
            if (grid_pos_size != pre_grid_pos_size):
                self.grids_dict[self.active_grid_pos]['pos_size'] = grid_pos_size
                self.db.replace_grid_row_value(self.active_grid_pos, 'pos_size', grid_pos_size)

            return grid_pos_size

        else:
            return ttl_previous_pos_size

    def update_grid_entry_exit_quantity(self, orders_list, last_price):
        global grids_dict
        grid_orders_list = dca_logic.get_orders_in_grid(self.active_grid_pos, orders_list)
        grid_orders_dict = dca_logic.get_sorted_orders_dict(self.entry_side, grid_orders_list, last_price)
        grid_exit_quantity = grid_orders_dict[self.exit_side]['ttl_qty']
        grid_entry_quantity = grid_orders_dict[self.entry_side]['ttl_qty']
        grid_entry_orders = grid_orders_dict['active_orders']
        grid_exit_orders = grid_orders_dict[self.exit_side]['sorted']
        num_active_orders = len(grid_entry_orders) + len(grid_exit_orders)
        print(f'num_active_orders: {num_active_orders}\n')

        self.grids_dict[self.active_grid_pos]['exit_qty'] = grid_exit_quantity
        self.grids_dict[self.active_grid_pos]['entry_qty'] = grid_entry_quantity

    def update_ttl_exit_qty_info(self, all_orders_list, last_price):
        global grids_dict
        all_orders_dict = dca_logic.get_sorted_orders_dict(self.entry_side, all_orders_list, last_price)
        all_exit_orders_dict = all_orders_dict[self.exit_side]
        total_exit_quantity = all_exit_orders_dict['ttl_qty']

        ttl_exit_qty_check = self.grids_dict[self.active_grid_pos]['ttl_exit_qty']
        if (total_exit_quantity != ttl_exit_qty_check):
            self.grids_dict[self.active_grid_pos]['ttl_exit_qty'] = ttl_exit_qty_check
            self.db.replace_grid_row_value(self.active_grid_pos, 'ttl_exit_qty', total_exit_quantity)

    async def update_secondary_orders(self, total_entry_exit_orders, order):

        last_price = self.api.last_price()
        orders_list = self.api.get_orders()
        grid_orders_list = dca_logic.get_orders_in_grid(self.active_grid_pos, orders_list)
        grid_orders_dict = dca_logic.get_sorted_orders_dict(self.entry_side, grid_orders_list, last_price)
        grid_active_exit_orders_len = len(grid_orders_dict[self.exit_side]['sorted'])
        grid_active_entry_orders_len = len(grid_orders_dict['active_orders'])
        inactive_entry_orders = grid_orders_dict['inactive_orders']
        grid_ttl_active_orders_len = grid_active_exit_orders_len + grid_active_entry_orders_len

        print(f'\ncurrent_num_orders_in_grid: {grid_ttl_active_orders_len}')
        print(f'total_entry_exit_orders: {total_entry_exit_orders}')
        print(f'processing waiting available order: \n')

        order_status = order['order_status']
        order_pos = order['order_pos']
        side = order['side']

        if (order_pos == 1):
            self.create_trade_record(order)

        elif (grid_ttl_active_orders_len == total_entry_exit_orders):
            print('Too many orders, Skipping: ')
            print('')
        else:
            if (order_status == 'PartiallyFilled'):
                print(f'processing partially filled, adding quantity to side: {side}')
                #TODO: Fix partial fills processing
                input_quantity = order['input_quantity']
                orders_dict = dca_logic.get_sorted_orders_dict(self.entry_side, orders_list, last_price)
                if (side == self.entry_side):
                    order_to_update = orders_dict[self.exit_side]['sorted'][0]
                else:
                    order_to_update = orders_dict[self.entry_side]['sorted'][0]

                current_input_size = order_to_update['qty']
                new_input_quantity = current_input_size + input_quantity
                price = order_to_update['price']
                order_id = order_to_update['order_id']
                self.api.change_order_price_size(price, new_input_quantity, order_id)

            else:
                side = order['side']
                grid_price_list = self.grids_dict[self.active_grid_pos]['grid_prices']
                grid_price_list_len = len(grid_price_list)

                if(grid_price_list_len > 0):
                    order_details = grid_price_list[order_pos]
                    input_quantity = order_details['input_quantity']
                
                    if (side == self.entry_side):
                        #create new exit order upon entry close
                        print("\ncreating new exit order")
                        side = self.exit_side
                        price = order_details['exit']
                        reduce_only = True

                    elif (side == self.exit_side):
                        print(f"\nCreating Trade Record")
                        self.create_trade_record(order)            
                        #create new entry order upon exit close
                        print('creating new entry order')
                        side = self.entry_side
                        price = order_details['entry']
                        reduce_only = False
                    else:
                        print('something is wrong in update_secondary_orders')
                        print(pprint.pprint(order))
                        sys.exit()

                    if (side == self.entry_side) and (order_pos in inactive_entry_orders):
                        order_id = inactive_entry_orders[order_pos]['order_id']
                        self.api.change_order_price_size(price, input_quantity, order_id)
                    else:
                        link_name = order_details['pp']
                        new_link_id = dca_logic.create_link_id(link_name, self.active_grid_pos, order_pos)
                        self.api.place_order(price, 'Limit', side, input_quantity, 0, reduce_only, new_link_id)

        await asyncio.sleep(0)

    async def handle_slipped_orders(self, grid_pos):
        global grids_dict

        slipped_orders_len = len(self.grids_dict[grid_pos]['slipped'])
        print(f'\nnum slipped orders check: {slipped_orders_len}\n')
        populate_orders_list_flag = True
        orders_list = []

        if (slipped_orders_len > 0):
            
            last_price = self.api.last_price()
            
            await asyncio.sleep(0)

            for order in self.grids_dict[grid_pos]['slipped']:
                order_pos = order['order_pos']
                side = order['side']
                price = order['price']

                if (side == 'Buy') and (last_price > price) \
                    or (side == 'Sell') and (last_price < price):

                    if (populate_orders_list_flag):
                        orders_list = self.api.get_orders()
                        populate_orders_list_flag = False

                    grid_orders_list = dca_logic.get_orders_in_grid(grid_pos, orders_list)
                    grid_orders_dict = dca_logic.get_sorted_orders_dict(self.entry_side, grid_orders_list, self.api.last_price())
                    active_exit_orders = grid_orders_dict[self.exit_side]['positions']
                    active_entry_orders = grid_orders_dict['active_orders']
                    inactive_entry_orders = grid_orders_dict['inactive_orders']

                    self.grids_dict[grid_pos]['slipped'].remove(order)
                    self.db.replace_slipped_order_empty(order)

                    if ((side == self.exit_side) and (order_pos in active_exit_orders)) \
                        or ((side == self.entry_side) and (order_pos in active_entry_orders)):
                        print(f'order_pos key {order_pos} already active')

                    else:
                        qty = order['input_quantity']
                        print(f'processing slipped order: ')
                        if (side == self.entry_side) and (order_pos in inactive_entry_orders):
                            order = inactive_entry_orders[order_pos]
                            order_id = order['order_id']
                            self.api.change_order_price_size(price, qty, order_id)
                        else:
                            name = order['link_name']
                            new_link_id = dca_logic.create_link_id(name, grid_pos, order_pos)
                            self.api.place_order(price, 'Limit', side, qty, 0, False, new_link_id)

                    await asyncio.sleep(0)

    async def clear_slipped_orders(self):
        global grids_dict

        grid_pos = self.active_grid_pos
        slipped_orders_list = self.grids_dict[grid_pos]['slipped']
        self.grids_dict[grid_pos]['slipped'] = []

        for order in slipped_orders_list:
            self.db.replace_slipped_order_empty(order)
