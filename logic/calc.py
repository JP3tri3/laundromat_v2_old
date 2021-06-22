import sys
sys.path.append("..")
import datetime
import asyncio

class Calc:

    def time_stamp(self):
        ct = datetime.datetime.now()
        print("Time: ", ct)
        return ct

    async def timer(interval, clock, func, *args):
        ticker = 0
        while True:
            await asyncio.sleep(interval)
            if ticker - int(ticker) == 0:
                print(ticker)

            if int(ticker) == int(clock):
                print("Ticker has reached: {}".format(clock))
                func(*args)
                ticker = 0

            ticker += interval

    def calc_fees(self, market_type, input_quantity):
        return (input_quantity) * 0.00075 if (market_type == "Market") \
            else (input_quantity) * 0.00025

    def calc_one_percent_less_entry(self, leverage, entry_price):
        return(float(entry_price) * 0.01) / leverage

    def calc_one_percent(self, leverage, last_price):
        return(float(last_price) * 0.01) / leverage

    def calc_percent_difference(self, entry_side, entry_exit, entry_price, percent):
        if ((entry_side == 'Buy') and (entry_exit == 'entry')) or ((entry_side == 'Sell') and (entry_exit == 'exit')):
            percent = (1 - percent)
        elif ((entry_side == 'Buy') and (entry_exit == 'exit')) or ((entry_side == 'Sell') and (entry_exit == 'entry')):
            percent += 1
        else:
            print("Somethings Fucking Wrong with calc_percent_difference")
        return(round(entry_price * percent, 2))

    def calc_percent_gained(self, side, entry_price, last_price, leverage):
        try:
            difference = (last_price - entry_price) if(side == "Buy") \
                else (entry_price - last_price)

            percent = (difference/last_price) * 100
            return float(round(percent * leverage, 3))

        except Exception as e:
            print("an exception occured - {}".format(e))

    def calc_limit_price_difference(self, side, last_price, limit_price_difference):
        return (last_price - limit_price_difference) if (side == 'Buy') \
            else (last_price + limit_price_difference)

    def calc_dollar_cost_average(self, order_price, num_order_contracts, added_order_price, num_added_contracts):
        
        previous_cost = order_price * num_order_contracts
        added_cost = added_order_price * num_added_contracts

        total_combined_cost = previous_cost + added_cost
        total_combined_contracts = num_order_contracts + num_added_contracts

        dollar_cost_average = round(total_combined_cost / total_combined_contracts, 2)

        print(f'\ncalculating DCA: ')
        print(f'previous order_price: {order_price}')
        print(f'previous num_contracts: {num_order_contracts}')
        print(f'added_order_price: {added_order_price}')
        print(f'num_added_contracts: {num_added_contracts}')
        print(f'dollar_cost_average: {dollar_cost_average}\n')

        return dollar_cost_average


        32107.2

        24767.2