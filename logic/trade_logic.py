import json
import sys
sys.path.append("..")
from api.bybit_api import Bybit_Api
from logic.calc import Calc as calc
from model.trades import Trade
from time import time, sleep

class Trade_Logic:
    
    def __init__(self, api_key, api_secret, symbol, symbol_pair, key_input, leverage, limit_price_difference):
        self.atr = None
        self.key_input = key_input
        self.leverage = leverage
        self.limit_price_difference = limit_price_difference

        self.api = Bybit_Api(api_key, api_secret, symbol, symbol_pair, self.key_input)
        print('... Trade_Logic initialized ...')

    def active_order_check(self):
        order = self.api.get_orders()
        return 0 if (order == []) else 1

    def active_position_check(self):
        try:
            position_value = self.api.get_position_value()
            return 1 if (position_value != '0') else 0
        except Exception as e:
            print("Active Position Check Exception Occured...")
            print("Trying again...")
            sleep(1)
            self.active_position_check()

    def input_atr(self):
        global atr
        flag = False
        print("")
        while(flag == False):
            atr = input("Input ATR: ")
            if(atr.isnumeric()):
                print("ATR input accepted for SL: " + str(atr))
                flag = True
            else:
                print("Invalid Input, try again...")


        print('exit force limit order loop')
        print('pos_size: ' + str(pos_size))
        print('get_position size: ' + str(self.api.get_position_size()))


    def create_order(self, side_input, order_type, input_quantity):
        global percent_level
        global percent_gained_lock

        percent_gained_lock = 0.0
        percent_level = 0.0
        flag = False

        if (self.active_order_check() == 1):
            print("Current Active Order...")
            print("Create Order Cancelled")
        elif (self.active_position_check() == 1):
            print("Current Active Position...")
            print("Create Order Cancelled")
        else:
            one_percent = calc().calc_one_percent(self.leverage, self.api.last_price())
            initial_stop_loss = (self.api.last_price() - (2*one_percent)) if (side_input == 'Buy') \
                else (self.api.last_price() + (2*one_percent))

            while(flag == False):
                if ((self.active_order_check() == 0) and (self.active_position_check() == 0)):
                    print("Attempting to place order...")
                    entry_price = calc().calc_limit_price_difference(side_input, self.api.last_price(), self.limit_price_difference)
                    self.api.place_order(price=entry_price, order_type=order_type, side=side_input, input_quantity=input_quantity, stop_loss=initial_stop_loss, reduce_only=False)

                    if(order_type == 'Limit') and (self.active_order_check() == 1):
                        print("")
                        print("Retrieving Order ID...")
                        print("Order ID: " + str(self.api.get_order_id()))
                        self.force_limit_order(side=side_input)
                else:
                    print("")
                    print("Confirming Order...")
                    
                    if((self.active_order_check() == 0) and (self.active_position_check() == 0)):
                        print("Order Failed")
                    else:
                        entry_price = float(self.api.get_active_position_entry_price())
                        print("")
                        print("Order Successful")
                        print("Entry Price: " + str(entry_price))
                        print("Initial Stop Loss: " + str(initial_stop_loss))
                        print("")
                        flag = True
                        return 1

    def close_position_market(self):
        position_size = self.api.get_position_size()
        flag = True

        if(self.api.get_position_side() == "Sell"):
            self.api.place_order(self.api.last_price(), 'Market', 'Buy', position_size, 0, True)
        else:
            self.api.place_order(self.api.last_price(), 'Market', 'Sell', position_size, 0, True)

        while(flag == True):
            if (self.active_position_check() == 1):
                print("Error Closing Position")
                self.close_position_market()
            else:
                print("Position Closed at: " + str(self.api.last_price()))
                flag = False

    def force_limit_close(self):
        flag = False
        current_price = self.api.last_price()
        input_quantity = self.api.get_position_size()
        side = self.api.get_position_side()
        print("current_price: " + str(current_price))

        side = 'Sell' if (side == 'Buy') else 'Buy'

        while(flag == False):
            if(self.active_position_check() == 1) and (self.active_order_check() == 0):
                print("Print Order Check")
                price = calc().calc_limit_price_difference(side, self.api.last_price(), self.limit_price_difference)
                self.api.place_order(price=price, order_type='Limit', side=side, input_quantity=input_quantity, stop_loss=0, reduce_only=True)
                time.sleep(2)
            elif (self.active_position_check() == 1) and (self.active_position_check() == 1):
                if (self.api.last_price() != current_price) and (self.api.last_price() != price):
                    print("last_price: " + str(self.api.last_price()))
                    print("current_price: " + str(current_price))
                    print("price: " + str(price))
                    current_price = self.api.last_price()
                    price = calc().calc_limit_price_difference(side, self.api.last_price(), self.limit_price_difference)
                    print("Price change: " + str(price))
                    self.api.change_order_price(price)
                    print("Order Price Updated: " + str(price))
                    print("")
                sleep(0.5)
            elif(self.active_position_check() == 0) and (self.active_order_check() == 0):
                flag = True
            else:
                print("Something's fucking wrong.")
                sleep(0.5)