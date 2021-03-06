import sys
from typing import List
sys.path.append("..")
from logic.calc import Calc as calc # type: ignore
import pprint

# create dict to store existing grid:

def initialize_grid(size, pos_price, grid_range_price, grid_pos_size, ttl_pos_size):
    print('\n...initializing grid dict...\n')
    # Store previous grid
    grid_dict = {}

    grid_dict['range_price'] = grid_range_price
    grid_dict['pos_size'] = grid_pos_size
    grid_dict['ttl_pos_size'] = ttl_pos_size
    grid_dict['main_exit_order_link_id'] = ''
    grid_dict['slipped_qty'] = 0
    grid_dict['pos_price'] = pos_price
    grid_dict['ttl_exit_qty'] = 0
    grid_dict['active'] = initialize_orders_list(size)
    grid_dict['cancelled'] = []
    grid_dict['slipped'] = []
    grid_dict['grid_prices'] = []

    return grid_dict

def convert_timestamp(ts):
    converted_timestamp = ''
    for x in range(len(ts)):
        char = ts[x]
        if char.isnumeric():
            converted_timestamp += char
    
    return int(converted_timestamp)

def initialize_orders_list(size):
    kv_dict = {}
    for i in range(size):
        index = i + 1
        kv_dict[index] =  None
    
    return kv_dict

# add order name / grid pos / order pos to link id
def create_link_id(name_id, grid_pos, order_pos):
    # name-grid_pos-order_pos

    link_id = name_id + '-' + str(grid_pos) + '-' + str(order_pos) + '-'
    return link_id


# extract order name / grid pos / order pos from link id
def extract_link_id(link_id):
    try:
    
        kv_dict = {}

        max_custom_id_length = 16
        name = ''
        grid_pos = ''
        order_pos = ''
        attach = '-'
        cycle = 0

        for x in range(max_custom_id_length):
            if (link_id[x] != attach):
                char = link_id[x]
                if (cycle == 0):
                    name += char
                elif (cycle == 1):
                    grid_pos += char
                elif (cycle == 2):
                    order_pos += char
                else:
                    break
            else:
                cycle += 1

        grid_pos = int(grid_pos)
        order_pos = int(order_pos)

        kv_dict['name'] = name
        kv_dict['grid_pos'] = grid_pos
        kv_dict['order_pos'] = order_pos

        return kv_dict
    except Exception as e:
        print("an exception occured - {}".format(e))
        return False

# extract orders for grid: 
def get_orders_in_grid(grid_pos: int, order_list: list):
    try:
        lst = []

        if (order_list == None):
            order_list_len = 0
        else:
            order_list_len = len(order_list)

        if (order_list_len > 0):
            for order in order_list:
                order_link_id = order['order_link_id']
                extracted_link_id = extract_link_id(order_link_id)
                if extracted_link_id['grid_pos'] == grid_pos:
                    lst.append(order)

        return lst
    except Exception as e:
        print("an exception occured - {}".format(e))
        return False

def get_sorted_orders_dict(entry_side: str, order_list: list, last_price: float):
    total_entry_quantity = 0
    total_exit_quantity = 0
    entry_orders_list = []
    exit_orders_list = []
    entry_sorted_list = []
    exit_sorted_list = []
    entry_positions = {}
    exit_positions = {}
    order_list_kv = {}
    entry_orders_in_grid = {}
    entry_orders_outside_grid = {}

    if (entry_side == 'Buy'): exit_side = 'Sell'
    else: exit_side = 'Buy'

    compare_price = calc().calc_percent_difference(entry_side, 'entry', last_price, 0.5)
    print(f'compare_price: {compare_price}')
    entry_order_doubles_check = {}

    for order in order_list:
        quantity = order['qty']
        side = order['side']
        order_link_id = order['order_link_id']
        extracted_link_id = extract_link_id(order_link_id)
        order_pos = extracted_link_id['order_pos']

        if (side == entry_side):
            total_entry_quantity += quantity
            
            order_price = float(order['price'])
            if (order_pos not in entry_order_doubles_check):
                entry_order_doubles_check[order_pos] = order
                entry_positions[order_pos] = order

            elif (order_pos in entry_order_doubles_check):
                order_price_to_check = float(entry_order_doubles_check[order_pos]['price'])
                if ((entry_side == 'Buy') and (order_price > order_price_to_check)) \
                    or ((entry_side == 'Sell') and (order_price < order_price_to_check)):
                    entry_order_doubles_check[order_pos] = order
                    entry_positions[order_pos] = order

            if ((entry_side == 'Buy') and (order_price > compare_price)) \
                or ((entry_side == 'Sell') and (order_price < compare_price)):
                entry_orders_in_grid[order_pos] = order
                entry_orders_list.append(order)
            else:
                entry_orders_outside_grid[order_pos] = order
                
        else:
            exit_orders_list.append(order)
            total_exit_quantity += quantity
            exit_positions[order_pos] = order
            
    if (entry_side == 'Buy'):
        entry_sorted_list = sorted(entry_orders_list, key=lambda k: k['price'], reverse=True)
        exit_sorted_list = sorted(exit_orders_list, key=lambda k: k['price'])

    else:
        entry_sorted_list = sorted(entry_orders_list, key=lambda k: k['price'])
        exit_sorted_list = sorted(exit_orders_list, key=lambda k: k['price'], reverse=True)

    order_list_kv[entry_side] = {'sorted': entry_sorted_list, 'positions' : entry_positions, 'ttl_qty' : total_entry_quantity}
    order_list_kv[exit_side] = {'sorted' : exit_sorted_list, 'positions': exit_positions, 'ttl_qty' : total_exit_quantity}
    order_list_kv['active_orders'] = entry_orders_in_grid
    order_list_kv['inactive_orders'] = entry_orders_outside_grid

    return order_list_kv



def get_updated_order_info(order, profit_percent_1: float, profit_percent_2: float):
    try:
        if (type(order) != dict):
            order = order[0]

        order_link_id = order['order_link_id']
        extracted_link_id = extract_link_id(order_link_id)
        link_name = extracted_link_id['name']
        order_pos = extracted_link_id['order_pos']
        grid_pos = extracted_link_id['grid_pos']

        if (link_name == 'pp_1'):
            profit_percent = profit_percent_1
        elif (link_name == 'pp_2'):
            profit_percent = profit_percent_2
        else:
            profit_percent = 0

        if 'timestamp' in order:
            time_stamp = order['timestamp']
        else:
            time_stamp = order['updated_at']

        updated_order = ({'grid_pos' : int(grid_pos),
                            'link_name' : link_name,
                            'order_pos' : int(order_pos),
                            'side' : order['side'], 
                            'order_status': order['order_status'], 
                            'input_quantity' : order['qty'],
                            'price' : float(order['price']),
                            'profit_percent' : profit_percent,
                            'order_id' : order['order_id'],
                            'order_link_id' : order_link_id,
                            'leaves_qty' : order['leaves_qty'],
                            'timestamp' : time_stamp
                            })

        return updated_order

    except Exception as e:
        print("an exception occured - {}".format(e))
        
        print('exciting on dca_logic.get_updated_order_info exception: ')
        sys.exit()


def generate_multi_order_price_list(profit_percent_1: float, profit_percent_2: float, num_initial_entry_orders: int, 
                                    num_initial_exit_orders: int, num_secondary_orders: int, initial_price: float, 
                                        input_quantity_1: int, input_quantity_2: int, entry_side: str):
    
    if (entry_side == 'Buy'): exit_side = 'Sell'
    else: exit_side = 'Buy'
    
    price_dict = {}
    grid_price_dict = {}
    
    price_list = []
    price = initial_price
    initial_exit_orders = generate_order_price_list(profit_percent_1, entry_side, 'exit', num_initial_exit_orders, price)
    for key in initial_exit_orders:
        primary_value = initial_exit_orders[key]
        price_dict['pp'] = 'pp_1'
        price_dict['entry'] = primary_value['entry']
        price_dict['exit'] = primary_value['exit']
        price_dict['side'] = exit_side
        price_dict['input_quantity'] = input_quantity_1
        price_list.append(price_dict)
        price = primary_value['entry']
        price_dict = {}

        
        secondary_price = calc().calc_percent_difference(entry_side, 'exit', price, profit_percent_2)
        secondary_exit_orders = generate_order_price_list(profit_percent_2, entry_side, 'exit', num_secondary_orders, secondary_price)
        
        for k in secondary_exit_orders:
            secondary_value = secondary_exit_orders[k]
            price_dict['pp'] = 'pp_2'
            price_dict['entry'] = secondary_value['entry']
            price_dict['exit'] = secondary_value['exit']
            price_dict['side'] = exit_side
            price_dict['input_quantity'] = input_quantity_2
            price_list.append(price_dict)
            price_dict = {}


    price_dict['pp'] = 'main'
    price_dict['entry'] = initial_price
    price_dict['exit'] = 0
    price_dict['side'] = entry_side
    price_dict['input_quantity'] = 0

    grid_price_dict['main_pos_price'] = price_dict
    price_dict = {}

    price = initial_price
    initial_entry_orders = generate_order_price_list(profit_percent_1, entry_side, 'entry', num_initial_entry_orders, price)
    for key in initial_entry_orders:
        
        primary_value = initial_entry_orders[key]
        secondary_price = calc().calc_percent_difference(entry_side, 'entry', price, profit_percent_2)
        secondary_entry_orders = generate_order_price_list(profit_percent_2, entry_side, 'entry', num_secondary_orders, secondary_price)
        
        for k in secondary_entry_orders:
            secondary_value = secondary_entry_orders[k]
            price_dict['pp'] = 'pp_2'
            price_dict['entry'] = secondary_value['entry']
            price_dict['exit'] = secondary_value['exit']
            price_dict['side'] = entry_side
            price_dict['input_quantity'] = input_quantity_2
            price_list.append(price_dict)
            price_dict = {}

        price_dict['pp'] = 'pp_1'
        price_dict['entry'] = primary_value['entry']
        price_dict['exit'] = primary_value['exit']
        price_dict['side'] = entry_side
        price_dict['input_quantity'] = input_quantity_1
        price_list.append(price_dict)
        price = primary_value['entry']
        price_dict = {}

    sorted_price_list = sorted(price_list, key=lambda k: k['exit'], reverse=True) 

    price_list_dict = {}
    x = 0
    for price in sorted_price_list:
        x +=1
        price_list_dict[x] = price

    grid_price_dict['price_list'] = price_list_dict

    return grid_price_dict




def generate_order_price_list(profit_percent, entry_side, entry_exit, num_orders, initial_price):
    price_list_dict = {}

    price = initial_price
    x = 0
    exit_count = num_orders
    while (x < num_orders):
        x += 1

        if (entry_exit == 'entry'):
            entry_price = calc().calc_percent_difference(entry_side, entry_exit, price, profit_percent)
            exit_price = price
            price = entry_price
            price_list_dict[x] = {'entry' : entry_price, 'exit' : exit_price}
        else:
            entry_price = price
            exit_price = calc().calc_percent_difference(entry_side, entry_exit, entry_price, profit_percent)
            price = exit_price
            price_list_dict[exit_count] = {'entry' : entry_price, 'exit' : exit_price}
            exit_count -= 1
        
    return price_list_dict






# UNUSED: get list differences
# def get_list_differences(lst_1, lst_2):
#     return (list(list(set(lst_1)-set(lst_2)) + list(set(lst_2)-set(lst_1))))