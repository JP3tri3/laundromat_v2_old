import sys
sys.path.append("..")
from logic.calc import Calc as calc
import pprint


def initialize_orders_list(size):
    kv_dict = {}
    for i in range(size):
        index = i + 1
        kv_dict[index] =  None
    
    return kv_dict

def create_link_id(name_id, pos_id):
    # name_id: first xxxx- (first 4)
    # pos_id: 6, 7, 8 0000-xxx-
    link_id = name_id + '-' + str(pos_id) + '-'
    print(f'link_id: {link_id}')
    return link_id

def extract_link_id_pos(link_id):
    # pos_id: 6, 7, 8 0000-xxx-

    index = 5
    pos_id = ''
    attach = '-'
    print(f'in extract_link_id: {link_id}')
    for x in range(3):
        if (link_id[index] != attach):
            pos_id = pos_id + link_id[index]
            index += 1
        else:
            break

    print(f'pos_id: {pos_id}')
    return int(pos_id)

# compare lists and return difference comparing order_id
def get_orders_not_active(init_orders_list, active_orders_list):
    lst = init_orders_list.copy()

    for index in active_orders_list:
        order_id = index['order_id']
        for id in lst:
            if id['order_id'] == order_id:
                lst.remove(id)
                break

    return lst

#retreive orders & separate into dict
def get_orders_dict(entry_side, order_list):
    entry_orders_list = []
    exit_orders_list = []

    order_list_kv = {}

    for order in order_list:

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

def get_total_quantity_and_ids_dict(side, order_list):
    order_link_ids = []
    total_quantity = 0

    order_dict = {}

    for order in order_list:
        if (order['side'] == side):
            order_link_ids.append(order['order_link_id'])
            total_quantity += order['qty']

    order_dict['order_link_ids'] = order_link_ids
    order_dict['total_quantity'] = total_quantity

    return order_dict

def get_updated_order_info(order, profit_percent_1, profit_percent_2):
        
        order = order[0]

        order_link_id = order['order_link_id']
        link_name = order_link_id[:4]
        link_id_pos = extract_link_id_pos(order_link_id)

        if (link_name == 'main'):
            profit_percent = profit_percent_1 / link_id_pos
        elif (link_name == 'pp_1'):
            profit_percent = profit_percent_1
        elif (link_name == 'pp_2'):
            profit_percent = profit_percent_2
        else:
            profit_percent = 0

        updated_order = ({'link_name' : link_name,
                            'link_id_pos' : link_id_pos,
                            'side' : order['side'], 
                            'order_status': order['order_status'], 
                            'input_quantity' : order['qty'],
                            'price' : float(order['price']),
                            'profit_percent' : profit_percent,
                            'reduce_only' : order['reduce_only'], 
                            'order_id' : order['order_id'],
                            'order_link_id' : order_link_id,
                            })

        return updated_order


# UNUSED: get list differences
# def get_list_differences(lst_1, lst_2):
#     return (list(list(set(lst_1)-set(lst_2)) + list(set(lst_2)-set(lst_1))))