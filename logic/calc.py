import sys
sys.path.append("..")
import datetime

class Calc:

    def time_stamp(self):
        ct = datetime.datetime.now()
        print("Time: ", ct)
        return ct

    def calc_fees(self, market_type, input_quantity):
        return (input_quantity) * 0.00075 if (market_type == "Market") \
            else (input_quantity) * 0.00025

    def calc_one_percent_less_entry(self, leverage, entry_price):
        return(float(entry_price) * 0.01) / leverage

    def calc_one_percent(self, leverage, last_price):
        return(float(last_price) * 0.01) / leverage

    def calc_percent_difference(self, long_short, entry_exit, entry_price, percent):
        if ((long_short == 'long') and (entry_exit == 'entry')) or ((long_short == 'short') and (entry_exit == 'exit')):
            percent = (1 - percent)
        elif ((long_short == 'long') and (entry_exit == 'exit')) or ((long_short == 'short') and (entry_exit == 'entry')):
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

