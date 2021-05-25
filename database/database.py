import sys
sys.path.append("..")
import config # type: ignore
import mysql.connector
import asyncio
import datetime
import pprint

db = mysql.connector.connect(
    host = config.host,
    user = config.user,
    passwd = config.passwd,
    auth_plugin = config.auth_plugin,
    database = config.database_name
)

mycursor = db.cursor()

def time_stamp():
    ct = datetime.datetime.now()
    return ct

def setup_default_tables():
    mycursor.execute("CREATE TABLE Strategy (id VARCHAR(50), wt1 DECIMAL, wt2 DECIMAL, last_candle_high DECIMAL, last_candle_low DECIMAL, last_candle_vwap DECIMAL, active_position VARCHAR(50), new_trend VARCHAR(50), last_trend VARCHAR(50), active_trend VARCHAR(50))")
    mycursor.execute("CREATE TABLE trades (id VARCHAR(50),  strat_id VARCHAR(50), symbol VARCHAR(50), symbol_pair VARCHAR(50), key_input INT, limit_price_difference FLOAT, leverage INT, input_quantity INT, side VARCHAR(8), stop_loss FLOAT, percent_gain DECIMAL, trade_record_id INT)")
    mycursor.execute("CREATE TABLE trade_records (id INT UNSIGNED, trade_id VARCHAR(16), strat_id VARCHAR(16), symbol_pair VARCHAR(50), side VARCHAR(8), input_quantity INT UNSIGNED, entry_price FLOAT UNSIGNED, exit_price FLOAT UNSIGNED, stop_loss FLOAT UNSIGNED, percent_gain VARCHAR(24), dollar_gain VARCHAR(24), coin_gain VARCHAR(24), total_p_l_dollar VARCHAR(24), total_p_l_coin VARCHAR(24), time VARCHAR(50))")

    mycursor.execute("INSERT INTO trades () VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", ('bybit_manual', 'empty', 'empty', 'empty', 0, 0.0, 0, 0, 'empty', 0, 0, 0))
    mycursor.execute("INSERT INTO trades () VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", ('bybit_auto_1', 'empty', 'empty', 'empty', 0, 0.0, 0, 0, 'empty', 0, 0, 0))
    mycursor.execute("INSERT INTO trades () VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", ('bybit_auto_2', 'empty', 'empty', 'empty', 0, 0.0, 0, 0, 'empty', 0, 0, 0))
    mycursor.execute("INSERT INTO trades () VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", ('bybit_auto_3', 'empty', 'empty', 'empty', 0, 0.0, 0, 0, 'empty', 0, 0, 0))
    mycursor.execute("INSERT INTO trades () VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", ('bybit_auto_4', 'empty', 'empty', 'empty', 0, 0.0, 0, 0, 'empty', 0, 0, 0))

    db.commit()

def update_trade_values(id_name, strat_id, symbol, symbol_pair, key_input, limit_price_difference, leverage, input_quantity, side, stop_loss, percent_gain, trade_record_id):
    try:
        query = "UPDATE trades SET strat_id='" +str(strat_id)+ "', symbol='" +str(symbol)+ "', symbol_pair='" +str(symbol_pair)+ "', key_input=" +str(key_input)+ ", limit_price_difference=" +str(limit_price_difference)+ ", leverage=" +str(leverage)+ ", input_quantity=" +str(input_quantity)+ ", side='" +str(side)+  "', stop_loss=" +str(stop_loss)+ ", percent_gain=" +str(percent_gain)+ ", trade_record_id=" +str(trade_record_id)+" WHERE id='" +str(id_name)+ "'" 
        print(query)
        mycursor.execute(query)
        db.commit()
    except mysql.connector.Error as error:
        print("Failed to update record to database: {}".format(error))

def delete_table(table_name):
    try:
        print(f'dropping table: {table_name}')
        query = "DROP TABLE " + str(table_name)
        mycursor.execute(query)
        db.commit()
    except mysql.connector.Error as error:
        print("Failed to update record to database: {}".format(error))

# create trigger values table
def create_trigger_values_table(symbol: str):
    try:
        table_name = f'triggers_{symbol}'

        delete_table(table_name)

        print(f'creating new trigger_values table')
        mycursor.execute(f"CREATE TABLE {table_name} (id VARCHAR(12), pre_vwap VARCHAR(12), vwap VARCHAR(12), pre_rsi VARCHAR(12), rsi VARCHAR(12),  pre_mfi VARCHAR(12), mfi VARCHAR(12), time VARCHAR(36))")

        time = str(time_stamp())

        tfs = ['1m', '4m', '6m', '9m', '12m', '16m', '24m', '30m', '1hr', '4hr', '1d']

        for tf in tfs:  
            query = (f"INSERT INTO {table_name} () VALUES (%s, %s, %s, %s, %s, %s, %s, %s)")
            vals = (tf, '0', '0', '0', '0', '0', '0', time)
            print(query)
            mycursor.execute(query, vals)
            db.commit()

    except mysql.connector.Error as error:
        print("Failed to update record to database: {}".format(error))


# replace trigger values
async def replace_tf_trigger_values(data):
    try:
        
        symbol = data['symbol']
        id = data['tf']
        table_name = f'triggers_{symbol}'

        pre_kv_dict = get_row_values_dict(table_name, id)
        await asyncio.sleep(0)
        time = str(time_stamp())

        print(pprint.pprint(pre_kv_dict))

        pre_vwap = str(round(float(pre_kv_dict['vwap']), 3))
        vwap = str(round(float(data['vwap']), 3))
        pre_rsi = str(round(float(pre_kv_dict['rsi']), 3))
        rsi = str(round(float(data['rsi']), 3))
        pre_mfi = str(round(float(pre_kv_dict['mfi']), 3))
        mfi = str(round(float(data['mfi']), 3))

        query = (f"UPDATE {table_name} SET pre_vwap = %s, vwap = %s, pre_rsi = %s, rsi = %s, pre_mfi = %s, mfi = %s, time = %s WHERE id = %s")
        vals = (pre_vwap, vwap, pre_rsi, rsi, pre_mfi, mfi, time, id)

        print(query, vals)
        print('')
        mycursor.execute(query, vals)
        await asyncio.sleep(0)
        db.commit()
    except mysql.connector.Error as error:
        print("Failed to update record to database: {}".format(error))

def get_symbol_row_values_dict(symbol: str, tf: str) -> dict:
    table_name = f'triggers_{symbol}'
    kv_dict = get_row_values_dict(table_name, tf)

    if (len(kv_dict) == 0):
        print(f'\nget_symbol_row_values_dict len = 0')
        print(f'check trigger table rows\n')

    return kv_dict

def get_row_values_dict(table_name: str, id: int) -> dict:

    try:
        kv_dict = {}
        column_query = "SHOW COLUMNS FROM " + str(table_name)
        column_name_result = mycursor.execute(column_query)
        column_name_list = mycursor.fetchall()

        row_query = "Select * FROM " + str(table_name) + " WHERE id = '" + str(id) + "' LIMIT 0,1"
        row_result = mycursor.execute(row_query)
        row_list = mycursor.fetchall()
        row_list = row_list[0]

        for x in range(len(row_list)):        
            kv_pair = [(column_name_list[x][0], row_list[x])]
            kv_dict.update(kv_pair)

        db.commit()

        return(kv_dict)

    except mysql.connector.Error as error:
        print("Failed to retrieve record from database: {}".format(error))

# delete trade records:

## Delete 
def delete_trade_records(flag: bool):
    try:
        if (flag == True):
            print("Deleting Trade Records...")
            query = "DELETE FROM trade_records"
            print(query)
            mycursor.execute(query)
            db.commit()
        else:
            print("Maintaining Trade Records...")
            return 0
    
    except mysql.connector.Error as error:
        print("Failed to update record to database: {}".format(error))
