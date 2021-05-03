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

        

        if (entry_side == 'Buy'):
            self.exit_side = 'Sell'
        else:
            self.exit_side = 'Buy'

        active_orders_table_name = 'dcamp_active_orders'
        
        delete_active_orders_table = True
        create_active_orders_table = True

        self.api = Bybit_Api(api_key, api_secret, symbol, symbol_pair, self.key_input)
        self.ws = Bybit_WS(api_key, api_secret, symbol_pair, True)
        self.db = DCA_DB(trade_id, active_orders_table_name, create_active_orders_table, delete_active_orders_table)

        self.api.set_leverage(self.leverage)
        
        self.slipped_orders_list = []
        self.filled_orders_list = []
        self.active_orders_list = []
        self.cancelled_orders_list = []

        # Set Trade Values
        self.profit_percent_1 = 0
        self.profit_percent_2 = 0

        print('... Strategy_DCA initialized ...')

    # TODO: Fix main pos quantity thats savedw
    async def main(self):

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

        # initialize db active orders table rows
        self.db.initialize_active_orders_table(total_entry_exit_orders)


        # starting tasks
        task_ping_timer = asyncio.create_task(self.ws.ping(0.5, 15))
        task_gather_last_price = asyncio.create_task(self.get_last_price())
        task_collect_orders = asyncio.create_task(self.collect_orders(total_entry_exit_orders, profit_percent_1, profit_percent_2))
        task_start_dca_multi_position = asyncio.create_task(self.dca_multi_position(main_pos_percent_of_total_quantity, 
                                                            secondary_pos_1_percent_of_total_quantity, secondary_pos_2_percent_of_total_quantity, 
                                                                total_secondary_orders_1, secondary_orders_2, total_secondary_orders_2, percent_rollover, 
                                                                    self.max_active_positions, self.input_quantity, profit_percent_1, profit_percent_2, 
                                                                        total_entry_exit_orders, total_entry_orders, total_exit_orders))

        await task_ping_timer
        await task_collect_orders        
        await task_start_dca_multi_position
        await task_gather_last_price



        # # # # # # TEST # # # # # #




    def continue_saved_state(total_entry_exit_orders):


        pos_check = self.api.get_position_size()
        num_orders = self.api.get_orders()

        print('checking for previous state')
        if self.api.get_position_size() > 0:
            print('Previous position exits:')
            print('filling orders: ')

            

        if len(self.api.get_orders()) > 0:
            order_check = True


    async def get_last_price(self):
        last_price = self.api.last_price()

        while True:
            await asyncio.sleep(0)
            last_price = await self.ws.get_last_price()
            print(f'last_price: {last_price}')

    # collect orders via ws
    async def collect_orders(self, total_entry_exit_orders, profit_percent_1, profit_percent_2):

        while True:
            await asyncio.sleep(0)
            order = await self.ws.get_order()
            await self.store_new_changed_filled_orders(order, profit_percent_1, profit_percent_2)            

    # store new, changed & filled orders in global lists
    async def store_new_changed_filled_orders(self, order, profit_percent_1, profit_percent_2):
        global active_orders_list
        global filled_orders_list
        global slipped_orders_list
        global cancelled_orders_list

        order = dca_logic.get_updated_order_info(order, profit_percent_1, profit_percent_2)
        order_status = order['order_status']
        key = order['link_id_pos']
        print(f'\n order status: {order_status}\n')

        self.db.dcamp_replace_active_order(order)
        self.active_orders_list[key] = order

        if(order_status == 'Filled'):
            print('\nadding closed order to filled_orders_list')
            self.filled_orders_list.append(order)
            print(f'filled_orders_list len: {len(self.filled_orders_list)}\n')

        elif(order_status == 'New'):
            print('\nadding new or changed order to order list\n')
            
        elif(order_status == 'Cancelled'):
            print('\nOrder was Cancelled, checking for slipped or intention... \n')
            cancelled_order_id = order['order_id']
            
            if (cancelled_order_id in self.cancelled_orders_list) == False:
                print('confirmed slipped order, moving cancelled order to slipped list')
                self.slipped_orders_list.append(order)
            else:
                print('confirmed cancelled order, removing order id from cancelled orders list')
                self.cancelled_orders_list.remove(cancelled_order_id)

        else:
            print('invalid order status')

        print('\n checking slipped orders: ')
        print(f'pre_slip_list len: {len(self.slipped_orders_list)}')
        for order in self.slipped_orders_list:
            await asyncio.sleep(0)
            print(f'num of slipped orders: {len(self.slipped_orders_list)}')
            side = order['side']
            price = order['price']
            last_price = self.api.last_price()
            print(f'side: {side}, price: {price}, last_price: {last_price}')

            if ((side == 'Buy') and (price < last_price)) or ((side == 'Sell') and (price > last_price)):
                print('adding slipped_order to filled_orders_list')
                self.filled_orders_list.append(order)
                self.slipped_orders_list.remove(order)
            else:
                print(f'order still slipped: ')
                
        print(f'post_slip_list len: {len(self.slipped_orders_list)}\n')

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
        global active_orders_list
        global slipped_orders_list
        global cancelled_orders_list
        global filled_orders_list

        available_input_quantity = total_input_quantity
        position_trade_quantity = total_input_quantity / max_active_positions

        main_pos_input_quantity = round(position_trade_quantity * main_pos_percent_of_total_quantity, 0)
        secondary_pos_input_quantity_1 = round(position_trade_quantity * secondary_pos_1_percent_of_total_quantity, 0)
        secondary_pos_input_quantity_2 = round(position_trade_quantity * secondary_pos_2_percent_of_total_quantity, 0)

        secondary_entry_1_input_quantity = int(secondary_pos_input_quantity_1 / total_secondary_orders_1)
        secondary_exit_1_input_quantity = secondary_entry_1_input_quantity * (1 - percent_rollover)

        secondary_entry_2_input_quantity = int(secondary_pos_input_quantity_2 / total_secondary_orders_2)
        secondary_exit_2_input_quantity = secondary_entry_2_input_quantity * (1 - percent_rollover)

        ##TEST##
        test_flag = True
        while test_flag == True:

            active_position_size = self.api.get_position_size()
            slipped_exit_quantity = 0

            if (active_position_size > 0):
                print(f'first position size: {active_position_size}')
                orders_list = self.api.get_orders()
                ids_and_quantity_dict = dca_logic.get_total_quantity_and_ids_dict(self.exit_side, orders_list)

                exit_link_ids_list = ids_and_quantity_dict['order_link_ids']
                total_exit_quanity = ids_and_quantity_dict['total_quantity']
                
                print(f'total_exit_quanity: {total_exit_quanity}')

                slipped_exit_quantity = active_position_size - total_exit_quanity
                print(f'slipped_exit_quantity: {slipped_exit_quantity}')

                if (slipped_exit_quantity > 0):
                    print('adding slipped quantity to first pos exit order: ')
                    first_position_exit_order = self.active_orders_list[1]
                    first_position_exit_order_link_id = first_position_exit_order['order_link_id']
                    first_position_exit_quantity = first_position_exit_order['input_quantity']

                    if (first_position_exit_order_link_id in exit_link_ids_list) == True:
                        print(f'found first position exit_order: adding {slipped_exit_quantity}')
                        current_first_position_exit_quantity = self.active_orders_list[1]['input_quantity']
                        new_first_position_exit_quantity_size = current_first_position_exit_quantity + slipped_exit_quantity
                        self.api.change_order_size(new_first_position_exit_quantity_size, first_position_exit_order_link_id)
                    else:
                        print(f'did not find position exit order, adding slipped exit quantity to next position: ')
                        active_position_size = 0

            if active_position_size == 0:

                print('\initializing all order lists: \n')
                self.active_orders_list = dca_logic.initialize_orders_list(total_entry_exit_orders)
                self.filled_orders_list = []
                self.cancelled_orders_list = []
                self.slipped_orders_list = []
                
                # create initial main_pos entry pos & exit orders, add previous pos slipped quantity:
                main_pos_input_quantity += slipped_exit_quantity
                await self.create_main_pos_entry_exit('Market', self.entry_side, main_pos_input_quantity, 
                            profit_percent_2, total_exit_orders)

                main_pos_entry = self.api.get_active_position_entry_price()
                await asyncio.sleep(0)
                # calculate and create open orders below Main pos:
                await self.create_secondary_orders(main_pos_entry, total_secondary_orders_1, secondary_orders_2, 
                            total_entry_orders, profit_percent_1, profit_percent_2, secondary_entry_1_input_quantity, 
                                secondary_entry_2_input_quantity)

                print('\nout first loop\n')

            else:
                await asyncio.sleep(0.5)
                await self.update_secondary_orders(total_entry_exit_orders, profit_percent_1, profit_percent_2)

                print('exit update_secondary_orders')


            current_orders_len = len(self.api.get_orders())
            if (current_orders_len > total_entry_exit_orders):
                print('\ntoo many orders, breaking: ')
                print(f'total_entry_exit_orders: {total_entry_exit_orders}')
                print(f'current_orders_len: {current_orders_len}')
                
                test_flag = False

    async def create_main_pos_entry_exit(self, order_type, entry_side, main_pos_input_quantity, profit_percent_2, total_exit_orders):

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
        secondary_orders_2, total_entry_orders, profit_percent_1, profit_percent_2, \
            secondary_entry_1_input_quantity, secondary_entry_2_input_quantity):

        global cancelled_orders_list

        if self.entry_side == 'Buy':
            long_short = 'long'
        else:
            long_short = 'short'

        # create buy/sell orders dict: 
        orders_dict = dca_logic.get_orders_dict(self.entry_side, self.api.get_orders())
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
            self.cancelled_orders_list.append(order_id)
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
                entry_price = calc().calc_percent_difference(long_short, 'entry', secondary_1_entry_price, profit_percent)
                secondary_1_entry_price = entry_price
                secondary_2_entry_price = entry_price
            else: 
                input_quantity = secondary_entry_2_input_quantity
                link_name = 'pp_2'
                profit_percent = profit_percent_2
                entry_price = calc().calc_percent_difference(long_short, 'entry', secondary_2_entry_price, profit_percent)
                secondary_2_entry_price = entry_price               

            if (x <= available_entry_orders):
                print(f'\navailable_entry_orders: {available_entry_orders}\n')
                print(f'in fill available entry orders: x = {x}')
                await asyncio.sleep(0)
                link_id_index += 1
                link_id = dca_logic.create_link_id(link_name, link_id_index)
                self.api.place_order(entry_price, 'Limit', self.entry_side, input_quantity, 0, False, link_id)

            else:

                print(f'\nactive_entry_orders len: {len(active_entry_orders_list)}')
                print(f'active_orders_index: {active_orders_index}')
                print(f'in update existing entry orders: x = {x}')
                order_id = orders_dict[self.entry_side][active_orders_index]['order_id']
                await asyncio.sleep(0)
                self.api.change_order_price_size(entry_price, input_quantity, order_id)
                active_orders_index +=1


    #TODO: Address blank link order ID when force closing order
    async def update_secondary_orders(self, total_entry_exit_orders, profit_percent_1, profit_percent_2):
        global filled_orders_list
        global active_orders_list

        # try:
        order_flag = True
        print('in update_secondary_orders')
        while order_flag == True:
            # TODO: Update for partial fill checks
            await asyncio.sleep(0.75)
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
                link_id_pos = closed_order['link_id_pos']
                link_id = closed_order['order_link_id']
                link_name = closed_order['link_name']

                new_link_id = dca_logic.create_link_id(link_name, link_id_pos)

                if (link_id_pos == 1):
                    print('\n link_id_pos = 1 ... create trade record break:')
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
                        price = calc().calc_percent_difference('long', 'exit', price, profit_percent)
                        reduce_only = True

                    elif (side == self.exit_side):
                        print("\nCreating Trade Record")
                        await self.create_trade_record(closed_order)            
                        #create new entry order upon exit close
                        print('creating new entry order')
                        side = self.entry_side
                        price = calc().calc_percent_difference('long', 'entry', price, profit_percent)
                        reduce_only = False

                    else:
                        print("... Something's fucking wrong in 'update_secondary_orders ...")

                    self.api.place_order(price, 'Limit', side, input_quantity, 0, reduce_only, new_link_id)


                print('\nclosed orders list len: ')
                print(len(self.filled_orders_list))
                if (len(self.filled_orders_list) == 0):
                    print('\n emptied orders list in update secondary orders\n')
                    order_flag = False

        # except Exception as e:
        #     print("an exception occured - {}".format(e))

