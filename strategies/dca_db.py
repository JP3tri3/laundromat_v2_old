import sys
sys.path.append("..")
import config
import datetime
import mysql.connector

class DCA_DB:

    def __init__(self, trade_id, active_orders_table_name, create_table_t_f, dlt_table_t_f):
        self.trade_id = trade_id
        self.active_orders_table_name = active_orders_table_name
        self.trade_record_id = 0  
        
        self.db = mysql.connector.connect(
            host = config.host,
            user = config.user,
            passwd = config.passwd,
            auth_plugin = config.auth_plugin,
            database = config.database_name
        )

        self.mycursor = self.db.cursor()

        # create db active orders table:
        self.delete_table(active_orders_table_name, dlt_table_t_f)
        self.dcamp_create_active_orders_table(create_table_t_f)
        

        print('... DCA_DB initialized ...')

    def initialize_active_orders_table(self, num_orders):
        for x in range(num_orders):
            x += 1
            self.dcamp_create_active_orders_row(x)

    def initialize_active_orders_table(self, num_orders):
        for x in range(num_orders):
            x += 1
            self.dcamp_create_active_orders_row(x)

    def commit_trade_record(self, coin_gain, dollar_gain, entry_price, exit_price, percent_gain, input_quantity):
        global trade_record_id

        print('IN TRADE RECORDS')
        self.trade_record_id += 1
        kv_dict = self.get_trades_table_row(self.trade_id)

        strat_id = kv_dict['strat_id']
        symbol = kv_dict['symbol']
        symbol_pair = kv_dict['symbol_pair']
        input_quantity = input_quantity
        side = kv_dict['side']
        stop_loss = kv_dict['stop_loss']

        if (self.trade_record_id > 1):
            trade_record_id = (self.trade_record_id - 1)
            previous_dollar_total = float(self.get_trade_record_value(trade_record_id, 'total_p_l_dollar'))
            previous_coin_total = float(self.get_trade_record_value(trade_record_id, 'total_p_l_coin'))
            total_p_l_dollar = previous_dollar_total + float(dollar_gain)
            total_p_l_coin = previous_coin_total + float(coin_gain)
        else:
            total_p_l_dollar = dollar_gain
            total_p_l_coin = coin_gain

        self.create_trade_record(self.trade_record_id, self.trade_id, strat_id, symbol_pair, side, \
            input_quantity, entry_price, exit_price, stop_loss, str(percent_gain), str(dollar_gain), \
                str(coin_gain), str(total_p_l_dollar), str(total_p_l_coin), self.time_stamp())

    def time_stamp(self):
        ct = datetime.datetime.now()
        return ct
    
    def dcamp_create_active_orders_table(self, create_table_t_f):

        if create_table_t_f == True:
            print('creating new active ordders table')
            self.mycursor.execute("CREATE TABLE " +str(self.active_orders_table_name)+ " (trade_id VARCHAR(16), link_id_pos INT UNSIGNED, link_name VARCHAR(8), side VARCHAR(8), status VARCHAR(12), input_quantity INT UNSIGNED, price FLOAT UNSIGNED, profit_percent FLOAT UNSIGNED, link_id VARCHAR(50), order_id VARCHAR(50), time VARCHAR(50))")
        else:
            print('create_table == False, not creating new table')

    def delete_table(self, table_name, dlt_table_t_f):
        try:
            if (dlt_table_t_f == True):
                print(f'dropping table: {table_name}')
                query = "DROP TABLE " + str(table_name)
                self.mycursor.execute(query)
                self.db.commit()
            else:
                print(f'using existing table {table_name}')
        except mysql.connector.Error as error:
            print("Failed to update record to database: {}".format(error))

    def dcamp_create_active_orders_row(self, link_id_pos):
        try:
            query = "INSERT INTO " +str(self.active_orders_table_name)+ " () VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            print(query)
            self.mycursor.execute(query,(self.trade_id, link_id_pos, 'empty', 'empty', 'empty', 0, 0, 0, 'empty', 'empty', 'empty'))
            self.db.commit()
        except mysql.connector.Error as error:
            print("Failed to update record to database: {}".format(error))

    def dcamp_replace_active_order(self, order):
        try:
            grid_pos = order['grid_pos']
            link_id_pos = order['order_pos']
            link_name = order['link_name']
            side = order['side']
            status = order['order_status']
            input_quantity = order['input_quantity']
            price = order['price']
            profit_percent = order['profit_percent']
            link_id = order['order_link_id']
            order_id = order['order_id']

            query = "UPDATE " +str(self.active_orders_table_name)+ " SET link_name='" +str(link_name)+ "', side='" +str(side)+ "', profit_percent='" +str(profit_percent)+"', status='" +str(status)+ "', input_quantity=" +str(input_quantity)+ ", price=" +str(price)+ ", profit_percent=" +str(profit_percent)+ ", link_id='" +str(link_id)+ "', order_id='" +str(order_id)+ "', time='" +str(self.time_stamp())+ "' WHERE link_id_pos=" +str(link_id_pos) 
            print(query)
            self.mycursor.execute(query)
            self.db.commit()
        except mysql.connector.Error as error:
            print("Failed to update record to database: {}".format(error))

    # create trade records:
    def create_trade_record(self, trade_record_id, trade_id, strat_id, symbol_pair, side, input_quantity, entry_price, exit_price, stop_loss, percent_gain, dollar_gain, coin_gain, total_p_l_dollar, total_p_l_coin, time):
        try:
            query = "INSERT INTO trade_records () VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            print(query)
            self.mycursor.execute(query,(trade_record_id, trade_id, strat_id, symbol_pair, side, input_quantity, entry_price, exit_price, stop_loss, percent_gain, dollar_gain, coin_gain, total_p_l_dollar, total_p_l_coin, time))
            self.db.commit()
        except mysql.connector.Error as error:
            print("Failed to update record to database: {}".format(error))

    def get_trades_table_row(self, id_name):
        
        try:
            table_name = 'trades'
            kv_dict = {}
            column_query = "SHOW COLUMNS FROM " + str(table_name)
            column_name_result = self.mycursor.execute(column_query)
            column_name_list = self.mycursor.fetchall()

            row_query = "Select * FROM " + str(table_name) + " WHERE id = '" + str(id_name) + "' LIMIT 0,1"
            row_result = self.mycursor.execute(row_query)
            row_list = self.mycursor.fetchall()
            row_list = row_list[0]

            for x in range(len(row_list)):        
                kv_pair = [(column_name_list[x][0], row_list[x])]
                kv_dict.update(kv_pair)

            self.db.commit()

            return(kv_dict)

        except mysql.connector.Error as error:
            print("Failed to retrieve record from database: {}".format(error))
    
    def get_trade_record_value(self, id_name, column_name):
        
        try: 
            table_name = 'trade_records'
            query = "SELECT " + str(column_name) + " FROM " +str(table_name)+ " WHERE id = '" + str(id_name) + "'"
            self.mycursor.execute(query)
            result = self.mycursor.fetchall()
            self.db.commit()
            return result[0][0]
        except mysql.connector.Error as error:
            print("Failed to retrieve record from database: {}".format(error))