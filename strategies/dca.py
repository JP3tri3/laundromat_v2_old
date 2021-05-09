import sys
sys.path.append("..")
from logic.calc import Calc as calc
from api.bybit_api import Bybit_Api
from api.bybit_ws import Bybit_WS
from strategies.dca_db import DCA_DB
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
        self.limit_price_difference = limit_price_difference
        self.entry_side = entry_side

        

        if (entry_side == 'Buy'): self.exit_side = 'Sell'
        else: self.exit_side = 'Buy'

        #TODO: Strat db settings, move to class arguments:
        strat_name = 'dcamp'
        delete_tables = True
        create_tables = True
        instance = 1

        self.api = Bybit_Api(api_key, api_secret, symbol, symbol_pair, self.key_input)
        self.ws = Bybit_WS(api_key, api_secret, symbol_pair, True)
        self.db = DCA_DB(trade_id, strat_name, instance, create_tables, delete_tables)

        self.api.set_leverage(self.leverage)
        
        self.filled_orders_list = []
        
        self.grids_dict = {}

        # TODO: Create checks for if active_grid_pos in link id isn't accurate
        self.active_grid_pos = 0
        self.grid_range_price = 0

        # Set Trade Values
        self.profit_percent_1 = 0
        self.profit_percent_2 = 0

        #TEST
        # self.test_num = 0

        print('... Strategy_DCA initialized ...')

    # TODO: Fix main pos quantity thats savedw
    async def main(self):
        global grids_dict
        # TODO: Testing, remove
        test_strat = False
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

        # initialize grids_dict
        self.grids_dict[self.active_grid_pos] = dca_logic.initialize_grid(total_entry_exit_orders, 0, 0)

        if main_strat:
            print('in main_strat')
        # starting tasks
            task_ping_timer = asyncio.create_task(self.ws.ping(0.5, 15))
            task_collect_orders = asyncio.create_task(self.collect_orders(total_entry_exit_orders, profit_percent_1, profit_percent_2))
            task_start_dca_multi_position = asyncio.create_task(self.dca_multi_position(main_pos_percent_of_total_quantity, 
                                                                secondary_pos_1_percent_of_total_quantity, secondary_pos_2_percent_of_total_quantity, 
                                                                    total_secondary_orders_1, secondary_orders_2, total_secondary_orders_2, percent_rollover, 
                                                                        self.max_active_positions, self.input_quantity, profit_percent_1, profit_percent_2, 
                                                                            total_entry_exit_orders, total_entry_orders, total_exit_orders))

            await task_ping_timer
            await task_collect_orders       
            await task_start_dca_multi_position

        # # # # # # TEST # # # # # #
        if test_strat:
            
            print(" !!!!! TESTING !!!!")
            self.active_grid_pos += 1
            # print(f'\ngrid_pos: {self.active_grid_pos}\n')

            self.db.replace_trade_data_value('active_grid_pos', 2)

            order = {'grid_pos': 1,
                        'input_quantity': 10,
                        'leaves_qty': 10,
                        'link_name': 'main',
                        'order_id': 'b06a9d22-1c9f-4767-a566-028f13648703',
                        'order_link_id': 'main-1-1-3563423431620527220.584705',
                        'order_pos': 1,
                        'order_status': 'Cancelled',
                        'price': 58571.0,
                        'profit_percent': 0.0004,
                        'reduce_only': False,
                        'side': 'Buy'}
            
            print(pprint.pprint(order))

            # self.db.dcamp_create_new_order_row(order)

            # self.db.dcamp_replace_slipped_order_status(order)

            # self.grids_dict[self.active_grid_pos] = dca_logic.initialize_grid(total_entry_exit_orders, 0, 0)

            # task_collect_orders = asyncio.create_task(self.collect_orders_test(total_entry_exit_orders, profit_percent_1, profit_percent_2))
            # test_task = asyncio.create_task(self.test_func())
            # await task_collect_orders  
            # await test_task 

    async def test_func(self):
        await asyncio.sleep(2)
        link_id = (f'main-{self.active_grid_pos}-1-356342343')
        self.api.place_order(self.api.last_price() - 400, 'Limit', 'Buy', 10, 0, False, 'main-1-1-356342343')
        # link_id = (f'main-{self.active_grid_pos}-3-356342341')
        # self.api.place_order(self.api.last_price() - 500, 'Limit', 'Buy', 10, 0, False, 'main-1-3-356342343')

    async def collect_orders_test(self, total_entry_exit_orders, profit_percent_1, profit_percent_2):
        global grids_dict
        print('collecting orders')
        await asyncio.sleep(0)
        order = await self.ws.get_order()

        new_order = dca_logic.get_updated_order_info(order, profit_percent_1, profit_percent_2)
        print(pprint.pprint(new_order))
        # grid_pos = new_order['grid_pos']

        # print(f'grid_pos: {grid_pos}')

        # print(pprint.pprint(new_order))

        # if (grid_pos != self.active_grid_pos):
        #     print('!! grid_pos: outside current grid !!')
        # order_pos = new_order['order_pos']

        # self.grids_dict[grid_pos]['active'][order_pos] = new_order

        # print(pprint.pprint(self.grids_dict))

        # first_position_exit_order = self.grids_dict[self.active_grid_pos]['active'][1]
        # print('first pos exit order test !!!!!')
        # print(first_position_exit_order)


    # initialize from saved state:
    def initialized_saved_state(self, total_order_size):
        global active_grid_pos
        global grids_dict

        print(' ... loading saved state ... ')

        orders_list = self.api.get_order()
        num_active_orders = len(orders_list)
        position_size = self.api.get_position_size()

        if (position_size == 0) and (num_active_orders == 0):
            print('no existing state')
        elif (position_size > 0 and num_active_orders == 0):
            print(f'active position size: {position_size}')
            print(f'num_active_orders: {num_active_orders}')

            active_grid_pos = 0

            for order in orders_list:
                order_link_id = order['order_link_id']
                updated_order = get_updated_order_info(order)
                grid_pos = updated_order['grid_pos']
                order_pos = updated_order['order_pos']
                if (grid_pos > active_grid_pos):
                    self.grids_dict[grid_pos] = dca_logic.initialize_grid(total_order_size, 0, 0)
                    active_grid_pos = grid_pos
                self.grids_dict[grid_pos]['active'][order_pos] = updated_order
        
        # need to determine main pos locations
        
        


    # collect orders via ws
    async def collect_orders(self, total_entry_exit_orders, profit_percent_1, profit_percent_2):
        print('collecting orders')
        while True:
            await asyncio.sleep(0)
            order = await self.ws.get_order()
            await self.store_new_changed_filled_orders(order, profit_percent_1, profit_percent_2)

    # TODO: Add checks for confirming active orders
    # store new, changed & filled orders in global lists
    async def store_new_changed_filled_orders(self, order, profit_percent_1, profit_percent_2):
        print('in store orders')
        global filled_orders_list
        global grids_dict

        order_link_id = order[0]['order_link_id']
        if (order_link_id == ''):
            print(f'skip store oder: {order_link_id}')
        else:
            order = dca_logic.get_updated_order_info(order, profit_percent_1, profit_percent_2)

            grid_pos = order['grid_pos']
            if (grid_pos != self.active_grid_pos):
                print('!! grid_pos: outside current grid !!')
            order_pos = order['order_pos']
            order_status = order['order_status']
            link_name = order['link_name']
            print(f'\n order status: {order_status}\n')

            if (link_name == 'open'):
                main_pos_price = order['price']
                self.grids_dict[grid_pos]['main_pos_price'] = main_pos_price
                
                print(f'skip store order: {link_name}')
            else:
                self.grids_dict[grid_pos]['active'][order_pos] = order

                if (order_status == 'Filled'):
                    print('\nadding closed order to filled_orders_list')
                    self.filled_orders_list.append(order)
                    self.db.dcamp_create_new_order_row(order)
                    print(f'filled_orders_list len: {len(self.filled_orders_list)}\n')

                elif (order_status == 'New'):
                    print('\nadding new or changed order to order list\n')
                    self.db.dcamp_replace_active_order(order)

                elif (order_status == 'Cancelled'):
                    print('\nOrder was Cancelled, checking for slipped or intention... \n')
                    cancelled_order_id = order['order_id']
                    
                    if (cancelled_order_id in self.grids_dict[grid_pos]['cancelled']) == False:
                        print('confirmed slipped order, moving cancelled order to slipped list')
                        self.grids_dict[grid_pos]['slipped'].append(order)
                        self.db.dcamp_replace_active_order(order)
                        self.db.dcamp_create_new_order_row(order)
                        
                    else:
                        print('confirmed cancelled order, removing order id from cancelled orders list')
                        self.grids_dict[grid_pos]['cancelled'].remove(cancelled_order_id)
                else:
                    print('invalid order status')

            for order in self.grids_dict[grid_pos]['slipped']:
                await asyncio.sleep(0)
                side = order['side']
                price = order['price']
                last_price = self.api.last_price()
                print(f'side: {side}, price: {price}, last_price: {last_price}')

                if ((side == 'Buy') and (price < last_price)) or ((side == 'Sell') and (price > last_price)):
                    print('adding slipped_order to filled_orders_list')
                    self.filled_orders_list.append(order)
                    self.grids_dict[grid_pos]['slipped'].remove(order)
                    self.db.dcamp_replace_slipped_order_status(order)
                else:
                    print(f'order still slipped: ')

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


    async def dca_multi_position(self, main_pos_percent_of_total_quantity, secondary_pos_1_percent_of_total_quantity, 
                                            secondary_pos_2_percent_of_total_quantity, total_secondary_orders_1, secondary_orders_2,
                                                total_secondary_orders_2, percent_rollover, max_active_positions, 
                                                    total_input_quantity, profit_percent_1, profit_percent_2, total_entry_exit_orders, 
                                                        total_entry_orders, total_exit_orders):

        global filled_orders_list
        global grids_dict
        global active_grid_pos

        available_input_quantity = total_input_quantity
        position_trade_quantity = total_input_quantity / max_active_positions

        main_pos_input_quantity = round(position_trade_quantity * main_pos_percent_of_total_quantity, 0)
        secondary_pos_input_quantity_1 = round(position_trade_quantity * secondary_pos_1_percent_of_total_quantity, 0)
        secondary_pos_input_quantity_2 = round(position_trade_quantity * secondary_pos_2_percent_of_total_quantity, 0)

        secondary_entry_1_input_quantity = int(secondary_pos_input_quantity_1 / total_secondary_orders_1)
        secondary_exit_1_input_quantity = secondary_entry_1_input_quantity * (1 - percent_rollover)

        secondary_entry_2_input_quantity = int(secondary_pos_input_quantity_2 / total_secondary_orders_2)
        secondary_exit_2_input_quantity = secondary_entry_2_input_quantity * (1 - percent_rollover)

        # determine_grid_size, currently by largest set profit * orders:
        grid_margin = 200
        #TODO: optimize grid_range_margin margin
        grid_range_margin = 0.01
        grid_percent_range = (profit_percent_1 * total_secondary_orders_1) + grid_range_margin
        grid_range_price = self.grid_range_price
        grid_pos_size = 0

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
                self.active_grid_pos += 1
                self.grids_dict[self.active_grid_pos] = dca_logic.initialize_grid(total_entry_exit_orders, 0, 0)
                self.db.replace_trade_data_value('active_grid_pos', self.active_grid_pos)

                # sys.exit("Program Terminated")

                # initialize db active orders table rows
                self.db.initialize_active_orders_table(self.active_grid_pos, total_entry_exit_orders)
                


                #TODO: Testing, remove:
                new_trend = False
                
            elif (init_existing_grid):
                print('init existing grid')
                self.active_grid_pos -= 1
                grid = self.grids_dict[self.active_grid_pos]
                orders = grid['orders']
                grid_range_price = grid['range_price']
                grid_pos_size = grid['pos_size']
                init_existing_grid = False


            active_position_size = self.api.get_position_size()
            first_position_entry = self.api.get_active_position_entry_price()

            
            await self.handle_initial_entry_exit_orders(profit_percent_1, profit_percent_2, active_position_size, first_position_entry, 
                                    grid_percent_range, main_pos_input_quantity, total_entry_exit_orders, total_exit_orders, 
                                        total_entry_orders, total_secondary_orders_1, secondary_orders_2, 
                                            secondary_entry_1_input_quantity, secondary_entry_2_input_quantity, 
                                                grid_range_price, grid_pos_size)


            await asyncio.sleep(0.5)
            # if filled orders, process:
            await self.update_secondary_orders(total_entry_exit_orders, profit_percent_1, profit_percent_2)





    async def handle_initial_entry_exit_orders (self, profit_percent_1, profit_percent_2, active_position_size, 
                                                first_position_entry, grid_percent_range, main_pos_input_quantity, 
                                                    total_entry_exit_orders, total_exit_orders, total_entry_orders,
                                                     total_secondary_orders_1, secondary_orders_2, 
                                                        secondary_entry_1_input_quantity, 
                                                            secondary_entry_2_input_quantity, grid_range_price, 
                                                                grid_pos_size):
        
        slipped_exit_quantity = 0
        #TODO: Calc grid position size:

        if (active_position_size > 0):
            # Handle checking active position, updating entry price

            # TODO: Update to calculate when not grid 1
            grid_range_price = calc().calc_percent_difference(self.entry_side, 'entry', first_position_entry, grid_percent_range)

            orders_dict = dca_logic.get_grid_orders_dict(self.active_grid_pos, self.entry_side, self.api.get_orders())
            ids_and_quantity_dict = dca_logic.get_total_quantity_and_ids_dict(orders_dict[self.exit_side])

            exit_link_ids_list = ids_and_quantity_dict['order_link_ids']
            total_exit_quanity = ids_and_quantity_dict['total_quantity']
            slipped_exit_quantity = active_position_size - total_exit_quanity
            
            first_position_exit_order = self.grids_dict[self.active_grid_pos]['active'][1]

            if (slipped_exit_quantity > 0) and (first_position_exit_order != None):

                print('adding slipped quantity to first pos exit order: ')

                print(f'\ntotal_exit_quanity: {total_exit_quanity}')
                print(f'slipped_exit_quantity: {slipped_exit_quantity}\n5')

                print('!!! TEST !!!!!!!!!!!!')
                print(f'active_grid_pos: {self.active_grid_pos}')
                print(pprint.pprint(self.grids_dict))

                first_position_exit_order_link_id = first_position_exit_order['order_link_id']
                first_position_exit_quantity = first_position_exit_order['input_quantity']

                if (first_position_exit_order_link_id in exit_link_ids_list) == True:
                    print(f'found first position exit_order: adding {slipped_exit_quantity}')
                    current_first_position_exit_quantity = self.grids_dict[self.active_grid_pos]['active'][1]['input_quantity']
                    new_first_position_exit_quantity_size = current_first_position_exit_quantity + slipped_exit_quantity
                    self.api.change_order_size(new_first_position_exit_quantity_size, first_position_exit_order_link_id)
                else:
                    print(f'did not find position exit order, adding slipped exit quantity to next position: ')
                    active_position_size = 0

        elif (active_position_size == 0):
            print('\nclearing all order lists: \n')
            self.grids_dict[self.active_grid_pos] = dca_logic.initialize_grid(total_entry_exit_orders, 
                                                                                grid_range_price, grid_pos_size)
            
            # create initial main_pos entry pos & exit orders, add previous pos slipped quantity:
            main_pos_input_quantity += slipped_exit_quantity
            await self.create_main_pos_entry_exit('Market', self.entry_side, main_pos_input_quantity, 
                        profit_percent_2, total_exit_orders)

            #TODO: Fix main pos entry for multi-grid
            main_pos_entry = self.api.get_active_position_entry_price()
            await asyncio.sleep(0)
            # calculate and create open orders below Main pos:
            await self.create_secondary_orders(main_pos_entry, total_secondary_orders_1, secondary_orders_2, 
                        total_entry_orders, profit_percent_1, profit_percent_2, secondary_entry_1_input_quantity, 
                            secondary_entry_2_input_quantity)


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

    async def create_main_pos_entry_exit(self, order_type, entry_side, main_pos_input_quantity, profit_percent_2, total_exit_orders):

        entry_link_id = 'open-1-1-'
        exit_link_id = 'main'

        if (order_type == 'Market'):
            print('\ncreating Market main_pos entry: ')
            main_pos_order_link_id = self.api.place_order(self.api.last_price(), 'Market', self.entry_side, main_pos_input_quantity, 0, False, entry_link_id)
            print('\ncreating main_pos exit: ')
        else:
            # force initial Main Pos limit close order
            print('\nforcing Limit main_pos entry: ')
            #TODO: Capture entry price for chasing limit in ws orders
            limit_price_difference = self.limit_price_difference
            main_pos_order_link_id = await self.api.force_limit_order(self.entry_side, main_pos_input_quantity, limit_price_difference, 0, False, entry_link_id)

        print('\ncreating main pos exits: ')
        main_pos_entry = round(self.api.get_active_position_entry_price(), 0)                
        total_num_orders = total_exit_orders
        input_quantity = main_pos_input_quantity
        input_quantity_2 = round(main_pos_input_quantity / total_num_orders, 0)
        start_price = main_pos_entry
        num_order = total_num_orders

        for x in range(total_num_orders):
            profit_percent = profit_percent_2 * num_order
            await asyncio.sleep(0)
            print(x)
            link_id = dca_logic.create_link_id(exit_link_id, self.active_grid_pos, x + 1)
            profit_percent = profit_percent_2 * num_order
            print(f'profit_percent {profit_percent}')
            print(f'num_order {num_order}')
            price = calc().calc_percent_difference(self.entry_side, 'exit', start_price, profit_percent)
            print(f'price: {price}')
            self.api.place_order(price, 'Limit', self.exit_side, input_quantity, 0, True, link_id)
            num_order -= 1
            input_quantity = input_quantity_2

        return main_pos_order_link_id
                    

    async def create_secondary_orders(self, main_pos_entry, total_secondary_orders_1, \
        secondary_orders_2, total_entry_orders, profit_percent_1, profit_percent_2, \
            secondary_entry_1_input_quantity, secondary_entry_2_input_quantity):

        global grids_dict

        # create buy/sell orders dict: 
        orders_dict = dca_logic.get_grid_orders_dict(self.active_grid_pos, self.entry_side, self.api.get_orders())
        print('\n in create secondary orders \n')
        #determine active & available orders
        active_entry_orders_list = orders_dict[self.entry_side]
        available_entry_orders = total_entry_orders - len(active_entry_orders_list)
        orders_to_cancel = len(active_entry_orders_list) - total_entry_orders
        secondary_1_entry_price = main_pos_entry
        secondary_2_entry_price = main_pos_entry

        print(f'\ncurrent active entry orders: {len(active_entry_orders_list)}')
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
        for x in range(total_entry_orders):
            x += 1
            if (x == num_check):
                num_check += total_secondary_orders_1
                input_quantity = secondary_entry_1_input_quantity
                link_name = 'pp_1'
                profit_percent = profit_percent_1
                entry_price = calc().calc_percent_difference(self.entry_side, 'entry', secondary_1_entry_price, profit_percent)
                secondary_1_entry_price = entry_price
                secondary_2_entry_price = entry_price
            else: 
                input_quantity = secondary_entry_2_input_quantity
                link_name = 'pp_2'
                profit_percent = profit_percent_2
                entry_price = calc().calc_percent_difference(self.entry_side, 'entry', secondary_2_entry_price, profit_percent)
                secondary_2_entry_price = entry_price               

            if (x <= available_entry_orders):
                print(f'\navailable_entry_orders: {available_entry_orders}\n')
                print(f'in fill available entry orders: x = {x}')
                await asyncio.sleep(0)
                link_id_index += 1
                link_id = dca_logic.create_link_id(link_name, self.active_grid_pos, link_id_index)
                self.api.place_order(entry_price, 'Limit', self.entry_side, input_quantity, 0, False, link_id)

            else:
                print(f'\nactive_entry_orders len: {len(active_entry_orders_list)}')
                print(f'active_orders_index: {active_orders_index}')
                print(f'in update existing entry orders: x = {x}')
                await asyncio.sleep(0)
                order_id = orders_dict[self.entry_side][active_orders_index]['order_id']
                self.api.change_order_price_size(entry_price, input_quantity, order_id)
                active_orders_index +=1


    #TODO: Address blank link order ID when manually closing order
    async def update_secondary_orders(self, total_entry_exit_orders, profit_percent_1, profit_percent_2):
        global filled_orders_list

        # try:
        order_flag = True
            
        while (len(self.filled_orders_list) > 0):

            closed_order = self.filled_orders_list[0]
            self.filled_orders_list.remove(self.filled_orders_list[0])

            current_num_orders = len(self.api.get_orders())
            print(f'current_num_orders: {current_num_orders}\n')
            print(f'total_entry_exit_orders: {total_entry_exit_orders}')
            print('processing waiting available order: \n')

            input_quantity = closed_order['input_quantity']
            profit_percent = closed_order['profit_percent']
            order_status = closed_order['order_status']
            price = closed_order['price']
            side = closed_order['side']
            order_pos = closed_order['order_pos']
            link_id = closed_order['order_link_id']
            link_name = closed_order['link_name']
            leaves_qty = closed_order['leaves_qty']
            new_link_id = dca_logic.create_link_id(link_name, self.active_grid_pos, order_pos)

            if (leaves_qty == 0):
                if (order_pos == 1):
                    print('\n order_pos = 1 ... create trade record break:')
                    await self.create_trade_record(closed_order)

                elif (current_num_orders == total_entry_exit_orders):
                    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                    print('Too many orders, Skipping: ')
                    print(f'current_num_orders: {current_num_orders}\n')
                    print('')

                else:
                    await asyncio.sleep(0)
                    if (order_status == 'Cancelled'):
                        reduce_only = closed_order['reduce_only']

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

                    self.api.place_order(price, 'Limit', side, input_quantity, 0, reduce_only, new_link_id)
            else:
                print(f'leaves_qty still open: {leaves_qty}')

            await asyncio.sleep(0)
            
            print(f'num filled_orders: {len(self.filled_orders_list)}')
            if (len(self.filled_orders_list) == 0):
                print('\n emptied orders list in update secondary orders\n')


        # except Exception as e:
        #     print("an exception occured - {}".format(e))

    # async def get_last_price(self):
    #     last_price = self.api.last_price()

    #     while True:
    #         await asyncio.sleep(0)
    #         last_price = await self.ws.get_last_price()
    #         print(f'last_price: {last_price}')