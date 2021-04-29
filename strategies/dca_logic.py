import sys
sys.path.append("..")
from logic.calc import Calc as calc


#print closed balance details
def print_closed_balance_details(last_price, open_balance, open_p_l, my_wallet_balance, my_wallet_realized_p_l):
    print('')
    print('closed balance details: ')
    print("Balance at open: ")
    print(open_balance)
    print("Balance at close: ")
    close_balance = my_wallet_balance
    print(close_balance)
    print('')
    print('balance difference: ')
    difference = close_balance - open_balance
    print(difference)
    print('')
    print('total gain: ')
    print(difference * last_price)
    print('')
    print('P_L')
    closed_p_l = my_wallet_realized_p_l
    print('open_p_l: ')
    print(open_p_l)
    print('closed_p_l: ')
    print(closed_p_l)
    print('p_l_difference: ')
    p_l_difference = closed_p_l - open_p_l
    print(p_l_difference)
    print('total p_l: ')
    print(p_l_difference * last_price)


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

    for x in range(len(order_list)):

        if (order_list[x]['side'] == entry_side):
            entry_orders_list.append(order_list[x])
        else:
            exit_orders_list.append(order_list[x])

    if (entry_side == 'Buy'):
        order_list_kv['Buy'] = sorted(entry_orders_list, key=lambda k: k['price'], reverse=True)
        order_list_kv['Sell'] = sorted(exit_orders_list, key=lambda k: k['price'])

    else:
        order_list_kv['Sell'] = sorted(entry_orders_list, key=lambda k: k['price'])
        order_list_kv['Buy'] = sorted(exit_orders_list, key=lambda k: k['price'], reverse=True)
    
    return order_list_kv


def get_updated_orders_list(order_list, profit_percent_1, profit_percent_2):
    new_lst = []
    for order in order_list:
        order_link_id = order['order_link_id']
        link_id = order_link_id[:4]
        if (link_id == 'main'):
            profit_percent = profit_percent_1
        elif (link_id == 'pp_1'):
            profit_percent = profit_percent_1
        elif (link_id == 'pp_2'):
            profit_percent = profit_percent_2
        else:
            profit_percent = 0

        updated_order = ({'link_id' : link_id,
                        'side' : order['side'], 
                        'order_status': order['order_status'], 
                        'input_quantity' : order['qty'],
                        'price' : float(order['price']),
                        'profit_percent' : profit_percent,
                        'order_id' : order['order_id']
                        })

        new_lst.append(updated_order)
        
    return new_lst


# # UNUSED: create price list for orders
# def create_order_price_list(self, initial_price, num_of_orders, profit_percent):
#     lst = []
#     index = 0
#     entry_price = initial_price

#     lst.append(round(initial_price, 0))

#     for x in range(num_of_orders):
#         entry_price = calc().calc_percent_difference('long', 'entry', entry_price, profit_percent)
#         lst.append(round(entry_price, 0))
#     return lst


# UNUSED: get last input quantity - use with get_closest_order_to_position
# def get_last_input_quantity_dict(self, entry_side, order_list):
#     closest_order = get_closest_order_to_position(entry_side, order_list)
#     last_input_quantity_kv = []
#     secondary_pos_input_quantity = 0
    
#     for x in range(len(order_list[entry_side])):
#         price = float(order_list[x]['price'])
#         if(price == closest_order):
#             secondary_pos_input_quantity = order_list[x]['input_quantity']

#     last_input_quantity_kv['main'] = main_pos_input_quantity = self.api.get_position_size()
#     last_input_quantity_kv['secondary'] = secondary_pos_input_quantity

#     return last_input_quantity_kv


# UNUSED: get list differences
# def get_list_differences(lst_1, lst_2):
#     return (list(list(set(lst_1)-set(lst_2)) + list(set(lst_2)-set(lst_1))))


# UNUSED: check for order changes
# def check_order_change(self, orders_list, closest_order):
#     order_change_check = 1

#     if (len(orders_list) == 0):
#         print("Orders List Empty")
#         order_change_check = 0
#     else:
#         for x in range(len(orders_list)):
#             price = float(orders_list[x]['price'])
#             if (price == closest_order):
#                 order_change_check = 0
#                 break

#     if (order_change_check == 1):
#         print("")
#         print("ORDER CLOSED")

#     return order_change_check