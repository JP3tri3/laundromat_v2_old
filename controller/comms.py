import sys
sys.path.append("..")
from database.database import Database as db
from logic.calc import Calc as calc
import json
import datetime


# class Comms:

#     def __init__(self):
#         self.total_profit_loss = 0
#         self.total_number_trades = 0



# def update_data(name_input, key_input, valueInput):
#     name = name_input
#     key = key_input
#     value = valueInput
#     try:
#         access_file = open("data.json", "r")
#         json_object = json.load(access_file)
#         access_file.close()

#         json_object[name][key] = value

#         access_file = open("data.json", "w")
#         json.dump(json_object, access_file, indent=4)
#         access_file.close()
#     except Exception as e:
#         print("an exception occured - {}".format(e))
#         update_data(name, key, value)

def update_display_data(key, value):
    access_file = open("data.json", "r")
    json_object = json.load(access_file)
    access_file.close()

    json_object[key] = value

    access_file = open("data.json", "w")
    json.dump(json_object, access_file, indent=4)
    access_file.close()

def update_display_dataValues():
    update_display_data('mainTest_number_Of_trades', total_number_trades)
    update_display_data('mainTest_profit_loss', round(total_profit_loss, 4))


def view_data(name_input, key_input):
    name = name_input
    key = key_input

    try:
        with open('data.json') as f:
            data = json.load(f)
            f.close()
        return data[name][key]
    except Exception as e:
        print("an exception occured - {}".format(e))
        view_data(name, key)

def update_data_persistent(data):
        table_id = data['input_name']

        last_candle_high = data['last_candle_high']
        last_candle_low = data['last_candle_low']
        last_candle_vwap = data['last_candle_vwap']
        wt1 = data['wt1']
        wt2 = data['wt2']

        db().update_strat_values(table_id, wt1, wt2, last_candle_high, last_candle_low, last_candle_vwap)        

def update_data_on_alert(data):
        strat_id = data['name']
        input_column = data['key']
        input_value = data['value']

        update_data(input_name, input_key, input_value)
        conn.updateTableValue('strategy', strat_id, input_column, input_value)

def clear_json(flag):
    if(flag == True):
        update_display_data('mainTest_number_Of_trades', 0)
        update_display_data('mainTest_profit_loss', 0)
        update_display_data('test1_number_Of_trades', 0)
        update_display_data('test1_profit_loss', 0)
        update_display_data('test2_number_Of_trades', 0)
        update_display_data('test2_profit_loss', 0)
        update_display_data('test3_number_Of_trades', 0)
        update_display_data('test3_profit_loss', 0)        
        print("Display Cleared")





# def clear_logs(flag):
#     if(flag == True):
#         file = open("logs.txt","r+")
#         file.truncate(0)
#         file.close()
#         print("Logs Cleared")