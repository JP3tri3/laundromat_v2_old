import sys
sys.path.append("..")
import mysql.connector
from database import config
import datetime

db = mysql.connector.connect(
    host = config.host,
    user = config.user,
    passwd = config.passwd,
    auth_plugin = config.auth_plugin,
    database = config.database_name
)

mycursor = db.cursor()

# # create table:
# mycursor.execute("CREATE TABLE Strategy (id VARCHAR(50), wt1 DECIMAL, wt2 DECIMAL, last_candle_high DECIMAL, last_candle_low DECIMAL, last_candle_vwap DECIMAL, active_position VARCHAR(50), new_trend VARCHAR(50), last_trend VARCHAR(50), active_trend VARCHAR(50))")
# mycursor.execute("CREATE TABLE trades (id VARCHAR(50),  strat_id VARCHAR(50), symbol VARCHAR(50), symbol_pair VARCHAR(50), key_input INT, limit_price_difference FLOAT, leverage INT, input_quantity INT, side VARCHAR(8), stop_loss FLOAT, percent_gain DECIMAL, trade_record_id INT)")
# mycursor.execute("CREATE TABLE trade_records (id INT UNSIGNED, trade_id VARCHAR(16), strat_id VARCHAR(16), symbol_pair VARCHAR(50), side VARCHAR(8), input_quantity INT UNSIGNED, entry_price FLOAT UNSIGNED, exit_price FLOAT UNSIGNED, stop_loss FLOAT UNSIGNED, percent_gain VARCHAR(24), dollar_gain VARCHAR(24), coin_gain VARCHAR(24), total_p_l_dollar VARCHAR(24), total_p_l_coin VARCHAR(24), time VARCHAR(50))")

# # describe table details:
# mycursor.execute("DESCRIBE Strategy")

# for x in mycursor:
#     print(x)

# # insert into table
# mycursor.execute("INSERT INTO Strategy () VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", ("1_min", 0.0, 0.0, 0.0, 0.0, 0.0, "null", "null", "null", "null"))
# mycursor.execute("INSERT INTO Strategy () VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", ("9_min", 0.0, 0.0, 0.0, 0.0, 0.0, "null", "null", "null", "null"))
# mycursor.execute("INSERT INTO Strategy () VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", ("16_min", 0.0, 0.0, 0.0, 0.0, 0.0, "null", "null", "null", "null"))
# mycursor.execute("INSERT INTO Strategy () VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", ("30_min", 0.0, 0.0, 0.0, 0.0, 0.0, "null", "null", "null", "null"))
# db.commit()

## Insert Column
# mycursor.execute("ALTER TABLE trade_records ADD time VARCHAR(50)")
# db.commit()

# mycursor.execute("INSERT INTO trades () VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", ('bybit_manual', 'empty', 'empty', 'empty', 0, 0.0, 0, 0, 'empty', 0, 0, 0))
# mycursor.execute("INSERT INTO trades () VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", ('bybit_auto_1', 'empty', 'empty', 'empty', 0, 0.0, 0, 0, 'empty', 0, 0, 0))
# mycursor.execute("INSERT INTO trades () VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", ('bybit_auto_2', 'empty', 'empty', 'empty', 0, 0.0, 0, 0, 'empty', 0, 0, 0))
# mycursor.execute("INSERT INTO trades () VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", ('bybit_auto_3', 'empty', 'empty', 'empty', 0, 0.0, 0, 0, 'empty', 0, 0, 0))
# mycursor.execute("INSERT INTO trades () VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", ('bybit_auto_4', 'empty', 'empty', 'empty', 0, 0.0, 0, 0, 'empty', 0, 0, 0))

# db.commit()
# mycursor.execute("SELECT * FROM Strategy")

# Query
# mycursor.execute("SELECT * FROM trades WHERE id = 'main'")
# for x in mycursor:
#     print(x)

# # Query specific
# mycursor.execute("SELECT wt1, wt2 FROM Strategy WHERE id = '9_min'")

# # Alter / Add
# mycursor.execute("ALTER TABLE strategy ADD COLUMN test VARCHAR(50) NOT NULL")

# # Alter / Remove
# mycursor.execute("ALTER TABLE Strategy DROP test")

# # Alter / Change column name

# mycursor.execute("ALTER TABLE Strategy CHANGE name id VARCHAR(50)")


## Update Values
def updateTableValue(table_name, id_name, column_name, value):
    try:
        if (isinstance(value, str)):
            query = "UPDATE " +str(table_name)+ " SET " + str(column_name) + "='" + str(value) + "' WHERE id = '" + str(id_name) + "'"
        else:
            query = "UPDATE " +str(table_name)+ " SET " + str(column_name) + "=" + str(value) + " WHERE id = '" + str(id_name) + "'"
        print(query)
        mycursor.execute(query)
        db.commit()
    except mysql.connector.Error as error:
        print("Failed to update record to database: {}".format(error))


def update_strat_values(id_name, wt1, wt2, last_candle_high, last_candle_low, last_candle_vwap):
    try:
        query = "UPDATE strategy SET wt1=" +str(wt1)+ ", wt2=" +str(wt2)+ ", last_candle_low=" +str(last_candle_low)+ ", last_candle_high=" +str(last_candle_high)+ ", last_candle_vwap=" +str(last_candle_vwap)+ " WHERE id = '" +str(id_name)+ "'"
        print(query)
        mycursor.execute(query)
        db.commit()
    except mysql.connector.Error as error:
        print("Failed to update record to database: {}".format(error))  

def update_strat_trends(id_name, active_position, new_trend, last_trend, active_trend):
    try:
        query = "UPDATE strategy SET active_position='" +str(active_position)+ "', new_trend='" +str(new_trend)+ "', last_trend='" +str(last_trend)+ "', active_trend='" +str(active_trend)+ "' WHERE id = '" +str(id_name)+ "'"
        print(query)
        mycursor.execute(query)
        db.commit()
    except mysql.connector.Error as error:
        print("Failed to update record to database: {}".format(error))  

def update_trade_values(id_name, strat_id, symbol, symbol_pair, key_input, limit_price_difference, leverage, input_quantity, side, stop_loss, percent_gain, trade_record_id):
    try:
        query = "UPDATE trades SET strat_id='" +str(strat_id)+ "', symbol='" +str(symbol)+ "', symbol_pair='" +str(symbol_pair)+ "', key_input=" +str(key_input)+ ", limit_price_difference=" +str(limit_price_difference)+ ", leverage=" +str(leverage)+ ", input_quantity=" +str(input_quantity)+ ", side='" +str(side)+  "', stop_loss=" +str(stop_loss)+ ", percent_gain=" +str(percent_gain)+ ", trade_record_id=" +str(trade_record_id)+" WHERE id='" +str(id_name)+ "'" 
        print(query)
        mycursor.execute(query)
        db.commit()
    except mysql.connector.Error as error:
        print("Failed to update record to database: {}".format(error))

## Create
def create_trade_record(trade_record_id, trade_id, strat_id, symbol_pair, side, input_quantity, entry_price, exit_price, stop_loss, percent_gain, dollar_gain, coin_gain, total_p_l_dollar, total_p_l_coin, time):
    try:
        query = "INSERT INTO trade_records () VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        print(query)
        mycursor.execute(query,(trade_record_id, trade_id, strat_id, symbol_pair, side, input_quantity, entry_price, exit_price, stop_loss, percent_gain, dollar_gain, coin_gain, total_p_l_dollar, total_p_l_coin, time))
        db.commit()
    except mysql.connector.Error as error:
        print("Failed to update record to database: {}".format(error))

## Delete 
def delete_trade_records():
    try:
        query = "DELETE FROM trade_records"
        print(query)
        mycursor.execute(query)
        db.commit()
    except mysql.connector.Error as error:
        print("Failed to update record to database: {}".format(error))

## View Value
def viewDbValue(table_name, id_name, column_name):
    try: 
        query = "SELECT " + str(column_name) + " FROM " +str(table_name)+ " WHERE id = '" + str(id_name) + "'"
        mycursor.execute(query)
        result = mycursor.fetchall()
        db.commit()
        return result[0][0]
    except mysql.connector.Error as error:
        print("Failed to retrieve record from database: {}".format(error))

def view_db_values_multiple(table_name, id_name_1, id_name_2, column_name):
    try: 
        query = "SELECT " + str(column_name) + " FROM " +str(table_name)+ " WHERE id = '" + str(id_name_1) + "' AND trade_id = '" + str(id_name_2) + "'"
        mycursor.execute(query)
        result = mycursor.fetchall()
        db.commit()
        return result[0][0]
    except mysql.connector.Error as error:
        print("Failed to retrieve record from database: {}".format(error))

## Get Table Row
def get_table_pair(table_name, id_name):
    try:
        kv_dict = {}
        column_query = "SHOW COLUMNS FROM " + str(table_name)
        column_name_result = mycursor.execute(column_query)
        column_name_list = mycursor.fetchall()

        row_query = "Select * FROM " + str(table_name) + " WHERE id = '" + str(id_name) + "' LIMIT 0,1"
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

## Get Table Columns
def get_table_column_names(table_name):
    try:
        for x in range(len(returnResult)):
            column_name_list.append(returnResult[x][0])

        db.commit()
        return(column_name_list)

    except mysql.connector.Error as error:
        print("Failed to retrieve record from database: {}".format(error))    




# updateTableValue('trades', 'main', 'leverage', 0)
# update_strat_values('9_min', 0, 0, 0, 0, 0)
# viewDbValues('9_min', 'wt1')
# mycursor.getUpdateCount()
# print(viewDbValues('9_min', 'wt1'))
# test1 = viewDbValues('9_min', 'wt1')
# create_trade_record('test1', 'BTCUSD', 14.4, 128.5, 932.4, 43.3, 12.3, 77.3, 4.2, 199999.2)
# deleteTradeRecords()
# clearAllTableValues()

# create_trade_record(0, 'empty', 0, 0, 0, 0, 0, 0, 0, 'empty', 0)

# test = viewTableRow('trades', 'bybit_btcusd_manual')

# print(type(test))
# print(test[0][2])


# update_trade_values('bybit_manual', '1_min', 'BTC', 'BTCUSD', 0, 0.50, 5, 500, 'empty', 0, 0, 0)