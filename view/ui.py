import sys
sys.path.append("..")
import database.config as config
from api.bybit_api import Bybit_Api
from logic.trade_logic import Trade_Logic
from logic.calc import Calc as calc
from database.database import Database as db

class Ui:

    def start(self):
        flag = True

        #manual Setters:
        leverage = 5
        input_quantity = 100 * leverage
        trade_id = 'bybit_manual'
        api_key = config.BYBIT_TESTNET_API_KEY
        api_secret = config.BYBIT_TESTNET_API_SECRET

        while (flag == True):
            symbol_pair = input("Enter Symbol: ").upper()
            if (symbol_pair == "BTCUSD") or (symbol_pair == "ETHUSD"):
                flag = False
            else:
                print("Invalid Input, try 'BTCUSD' or 'ETHUSD'")

        if (symbol_pair == "BTCUSD"):
            symbol = 'BTC'
            key_input = 0
            limit_price_difference = 0.50
            db().update_trade_values(trade_id, 'manual', symbol, symbol_pair,  0, limit_price_difference, leverage, input_quantity, 'empty', 0, 0, 0)

        elif (symbol_pair == "ETHUSD"):
            symbol = 'ETH'
            key_input = 1
            limit_price_difference = 0.05
            db().update_trade_values(trade_id, 'manual', symbol, key_input, 1, limit_price_difference, leverage, input_quantity, 'empty', 0, 0, 0)

        self.api = Bybit_Api(api_key, api_secret, symbol, symbol_pair, key_input)
        self.tl = Trade_Logic(api_key, api_secret, symbol, symbol_pair, key_input, leverage, limit_price_difference)

        self.inputOptions(symbol_pair)
        self.startMenu(symbol_pair, trade_id, input_quantity)

    def inputOptions(self, symbol_pair):
        print("")
        print("TESTNET - Input Options:")
        print("")
        print("Symbol: " + symbol_pair)
        print("")
        print("Market Actions:")
        print("")
        print("Create Long Order: 'long'")
        print("Create Short Order: 'short'")
        print("Create Long Market Order: 'long market'")
        print("Create Short Market Order: 'short market'")
        print("Cancel Pending Orders: 'cancel'")
        print("Market Close: 'closem'")
        print("Force Limit Close: 'closel")
        print("")
        print("Development Info:")
        print("")
        print("Stop Loss: 'stoploss'")
        print("Price Info: 'price info'")
        print("Symbol Info: 'info'")
        print("Wallet: 'wallet'")
        print("Active Orders: 'active'")
        print("Position: 'position'")
        print("Update SL: 'update sl'")
        print("Change Currency: change")
        print("Exit: 'exit'")

    def startMenu(self, symbol_pair, trade_id, input_quantity):
        flag = True

        while(flag == True):

            print("")
            taskInput = input("Input Task: ")
            calc().time_stamp()

            if(taskInput == "exit"):
                self.shutdown()

            elif(taskInput == "price info"):
                self.api.price_info()

            elif(taskInput == "info"):
                print(self.api.symbol_info_result())

            elif(taskInput == "long"):
                self.tl.create_order("Buy", 'Limit', input_quantity)

            elif(taskInput == "short"):
                self.tl.create_order("Sell", 'Limit', input_quantity)

            elif(taskInput == "long market"):
                self.tl.create_order('Buy', 'Market', input_quantity)

            elif(taskInput == "short market"):
                self.tl.create_order("Sell", 'Market', input_quantity)

            elif(taskInput == "wallet"):
                self.api.wallet_result()

            elif(taskInput == "stoploss"):
                self.api.change_stop_loss(500)
                print("Updated Stop Loss")

            elif(taskInput == "closem"):
                self.tl.close_position_market() 

            elif(taskInput == "closel"):
                self.tl.force_limit_close() 

            elif(taskInput == "cancel"):
                self.api.cancel_all_orders()
                print("Orders Cancelled")

            elif(taskInput == "active"):
                print(self.tl.active_order_check())

            elif(taskInput == "position"):
                print("Position: ")
                self.tl.force_limit_order('Buy')

            elif(taskInput == "test"):
                self.api.place_order(self.api.last_price(), 'Market', 'Buy', 100, 0, 'PostOnly', False)
                
            elif(taskInput == "test1"):
                self.api.place_order(self.api.last_price() + 100, 'Limit', 'Sell', 100, 0, 'PostOnly', True)

            elif(taskInput == "change"):
                flag = False
                self.start()

            elif(taskInput == "update sl"):
                flag = False
                while(flag == False):
                    sl_amountInput = input("Enter SL Amount:")
                    if sl_amountInput.isnumeric():
                        flag = True
                        self.api.change_stop_loss(sl_amountInput)
                    else:
                        print("Invalid Entry...")

            else:
                print("Invalid Input, try again...")
                self.inputOptions(symbol_pair)

    def shutdown(self):
        print("")
        print("Shutting down...")
        sys.exit("Program Terminated")
        print("")

