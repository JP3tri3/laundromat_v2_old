import time
import sys
sys.path.append("..")

class Stop_Loss:

    def __init__(self):
        self.percent_level = 0
        self.level = 0
        self.stop_loss = 0

    def check_level(self, side, last_price):
        global level
        if((side == 'Buy') and (last_price > self.level)) \
            or ((side == 'Sell') and (self.level == 0)) \
            or ((side == 'Sell') and (last_price < self.level)):
            self.level = last_price
            print("Level: " + str(self.level))
            return 1
        else:
            return 0

    def percentage_stop_loss_strat(self, side, entry_price, last_price, leverage, percent_gained, one_percent_less_entry):
        global level
        global percent_level
        global stop_loss

        if (self.check_level(side, last_price) == 1):

            pre_percent_level = self.percent_level

            print("calculating Stop Loss:")
            print("Level before calc: " + str(self.level))
            print("")
            if (self.percent_level < 0.25):
                self.stop_loss = (entry_price - one_percent_less_entry) if (side == 'Buy') \
                    else (entry_price + one_percent_less_entry)
                self.percent_level = 0.25
            elif (percent_gained >= 0.25) and (self.percent_level >= 0.25) and (percent_level < 0.5):
                self.stop_loss = entry_price
                self.percent_level = 0.5
                self.level = last_price
            elif (percent_gained >= 0.5) and (self.percent_level < 0.75):
                self.stop_loss = self.level
                self.percent_level = 0.75
                self.level = last_price
            elif (percent_gained >= 0.75) and (self.percent_level < 1.0):
                self.stop_loss = self.level
                self.percent_level = 1.0
                self.level = last_price
            elif (percent_gained > (self.percent_level + 0.5)):
                self.stop_loss = self.level
                self.percent_level += 0.5
                self.level = last_price
            else:
                return 0

            if (pre_percent_level != self.percent_level):
                print("Changing Stop Loss")
                print("")
                total_percent_gained = percent_gained
                return self.stop_loss

        else:
            return 0

    def candles_stop_loss_strat(self, last_candle_high, last_candle_low, one_percent_less_entry, side, last_price):

        if (self.check_level(side, last_price) == 1):
            difference = (2.0 * one_percent_less_entry)
            if (side == 'Buy'):
                stop_loss_check = float(last_candle_low) - difference
                if (self.stop_loss < stop_loss_check):
                    self.stop_loss = stop_loss_check
                    return self.stop_loss
                
                else:
                    return 0

            elif (side == 'Sell'):
                stop_loss_check = float(last_candle_high) + difference
                if (self.stop_loss == 0) or (self.stop_loss > stop_loss_check):                
                    self.stop_loss = stop_loss_check
                    return self.stop_loss

                else:
                    return 0

            else:
                print("Invalide Side in Candles Stop Loss")
                return 0
        else:
            return 0



