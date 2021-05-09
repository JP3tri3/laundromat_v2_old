import sys
sys.path.append("..")
from logic.calc import Calc as calc
import pprint

# create dict to store existing grid:

def initialize_grid(size, grid_range_price, grid_pos_size):
    print('\n...initializing grid dict...\n')
    # Store previous grid
    grid_dict = {}

    grid_dict['range_price'] = grid_range_price
    grid_dict['pos_size'] = grid_pos_size
    grid_dict['pos_price'] = 0
    grid_dict['active'] = initialize_orders_list(size)
    grid_dict['cancelled'] = []
    grid_dict['slipped'] = []

    return grid_dict

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
    print(f'link_id: {link_id}')
    return link_id

# extract order name / grid pos / order pos from link id
def extract_link_id(link_id):
    try:
    
        kv_dict = {}

        max_custom_id_length = 14
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
    lst = []

    for order in order_list:
        order_link_id = order['order_link_id']
        extracted_link_id = extract_link_id(order_link_id)
        if extracted_link_id['grid_pos'] == grid_pos:
            lst.append(order)

    return lst


# compare lists and return difference comparing order_id
# def get_orders_not_active(init_orders_list, active_orders_list):
#     lst = init_orders_list.copy()

#     for index in active_orders_list:
#         order_id = index['order_id']
#         for id in lst:
#             if id['order_id'] == order_id:
#                 lst.remove(id)
#                 break

#     return lst

#retreive grid orders & separate into dict
def get_grid_orders_dict(grid_pos: int, entry_side: str, order_list: list):
    entry_orders_list = []
    exit_orders_list = []
    grid_lst = []
    order_list_kv = {}

    for order in order_list:
        order_link_id = order['order_link_id']
        extracted_link_id = extract_link_id(order_link_id)
        if extracted_link_id['grid_pos'] == grid_pos:
            grid_lst.append(order)

    for order in grid_lst:

        if (order['side'] == entry_side):
            entry_orders_list.append(order)
        else:
            exit_orders_list.append(order)
            
    if (entry_side == 'Buy'):
        order_list_kv['Buy'] = sorted(entry_orders_list, key=lambda k: k['price'], reverse=True)
        order_list_kv['Sell'] = sorted(exit_orders_list, key=lambda k: k['price'])

    else:
        order_list_kv['Sell'] = sorted(entry_orders_list, key=lambda k: k['price'])
        order_list_kv['Buy'] = sorted(exit_orders_list, key=lambda k: k['price'], reverse=True)

    return order_list_kv

def get_total_quantity_and_ids_dict(order_list: list):
    order_link_ids = []
    total_quantity = 0

    order_dict = {}

    for order in order_list:
            order_link_ids.append(order['order_link_id'])
            total_quantity += order['qty']

    order_dict['order_link_ids'] = order_link_ids
    order_dict['total_quantity'] = total_quantity

    return order_dict

def get_updated_order_info(order, profit_percent_1: float, profit_percent_2: float):
        
        order = order[0]

        order_link_id = order['order_link_id']
        print(f'get_updated_order_info order id: {order_link_id}')
        extracted_link_id = extract_link_id(order_link_id)
        link_name = extracted_link_id['name']
        order_pos = extracted_link_id['order_pos']
        grid_pos = extracted_link_id['grid_pos']

        if (link_name == 'main'):
            profit_percent = profit_percent_1 / order_pos
        elif (link_name == 'pp_1'):
            profit_percent = profit_percent_1
        elif (link_name == 'pp_2'):
            profit_percent = profit_percent_2
        else:
            profit_percent = 0

        updated_order = ({'grid_pos' : int(grid_pos),
                            'link_name' : link_name,
                            'order_pos' : int(order_pos),
                            'side' : order['side'], 
                            'order_status': order['order_status'], 
                            'input_quantity' : order['qty'],
                            'price' : float(order['price']),
                            'profit_percent' : profit_percent,
                            'reduce_only' : order['reduce_only'], 
                            'order_id' : order['order_id'],
                            'order_link_id' : order_link_id,
                            'leaves_qty' : order['leaves_qty']
                            })

        return updated_order


# UNUSED: get list differences
# def get_list_differences(lst_1, lst_2):
#     return (list(list(set(lst_1)-set(lst_2)) + list(set(lst_2)-set(lst_1))))