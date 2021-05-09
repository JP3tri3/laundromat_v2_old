import sys
sys.path.append("..")
import config
import datetime
import mysql.connector

class DCA_DB:

    def __init__(self, trade_id, strat_name, instance, create_table_t_f, dlt_table_t_f):
        self.trade_id = trade_id
        self.active_orders_table_name = strat_name + '_active_orders_' + str(instance)
        self.slipped_orders_table_name = strat_name + '_slipped_orders_' + str(instance)
        self.filled_orders_table_name = strat_name + '_filled_orders_' + str(instance)
        self.grids_table = strat_name + '_grids_' + str(instance)
        self.trade_data_table_name = strat_name + '_trade_data'
        self.trade_record_id = 0  
        
        self.db = mysql.connector.connect(
            host = config.host,
            user = config.user,
            passwd = config.passwd,
            auth_plugin = config.auth_plugin,
            database = config.database_name
        )

        self.mycursor = self.db.cursor()

        self.initialize_all_tables(strat_name, dlt_table_t_f, create_table_t_f)

        print('... DCA_DB initialized ...')


    def initialize_all_tables(self, strat_name: str, dlt_table_t_f: bool, create_table_t_f: bool):
        print(f'... initializing tables for {strat_name} ...')
        print(f'\ndelete all tables: {dlt_table_t_f}')
        if (dlt_table_t_f == True):
            print('removing all tables:')
            self.delete_table(self.active_orders_table_name)
            self.delete_table(self.slipped_orders_table_name)
            self.delete_table(self.filled_orders_table_name)
            self.delete_table(self.trade_data_table_name)
            self.delete_table(self.grids_table)
        else:
            print('not removing tables')

        print(f'create all tables: {create_table_t_f}')
        if (create_table_t_f == True):
            print('creating all tables')
            self.dcamp_create_orders_table(self.active_orders_table_name)
            self.dcamp_create_orders_table(self.slipped_orders_table_name)
            self.dcamp_create_orders_table(self.filled_orders_table_name)
            self.dcamp_create_new_dcamp_trade_data_table(self.trade_data_table_name, self.trade_id)
            self.dcamp_create_new_grids_table(self.grids_table)
        else:
            print('not creating new tables\n')

    # initialize orders tables: 
    def initialize_active_orders_table(self, grid_pos: int, num_orders: int):
        print(f'\ninitialize_active_orders_table: ')
        for x in range(num_orders):
            x += 1
            self.dcamp_create_new_empty_orders_row(self.active_orders_table_name, grid_pos, x)

    def initialize_filled_orders_table(self, grid_pos: int, num_orders: int):
        print(f'\ninitialize_slipped_orders_table: ')
        for x in range(num_orders):
            x += 1
            self.dcamp_create_new_empty_orders_row(self.filled_orders_table_name, grid_pos, x)

    # replace active / filled / slipped orders:
    def dcamp_replace_active_order(self, order):
        self.replace_order(self.active_orders_table_name, order)

    # slipped orders:
    def dcamp_replace_slipped_order(self, order):
        self.replace_order(self.slipped_orders_table_name, order)
    
    # filled orders:
    def dcamp_replace_filled_order(self, order):
        self.replace_order(self.filled_orders_table_name, order)

    # create trade record:
    def commit_trade_record(self, coin_gain, dollar_gain, entry_price, exit_price, percent_gain, input_quantity):
        global trade_record_id

        print('IN TRADE RECORDS')
        self.trade_record_id += 1
        self.replace_trade_data_value('closed_orders', self.trade_record_id)
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
    
    def dcamp_create_new_dcamp_trade_data_table(self, table_name: str, trade_id: str):
        try:
            print(f'creating new {table_name} orders table')
            self.mycursor.execute(f"CREATE TABLE {table_name} (trade_id VARCHAR(16), active_grid_pos INT UNSIGNED, grid_price_range FLOAT UNSIGNED, closed_orders INT UNSIGNED, active_orders INT UNSIGNED, total_pos_size FLOAT UNSIGNED, time VARCHAR(50))")

            time = str(self.time_stamp())
            
            query = (f"INSERT INTO {table_name} () VALUES (%s, %s, %s, %s, %s, %s, %s)")
            vals = (self.trade_id, 0,  0.0, 0, 0, 0.0, time)
            print(query)
            self.mycursor.execute(query, vals)
            self.db.commit()

        except mysql.connector.Error as error:
            print("Failed to update record to database: {}".format(error))


    def dcamp_create_new_grids_table(self, table_name):
        try:
            print(f'creating new {table_name} orders table')
            self.mycursor.execute(f"CREATE TABLE {table_name} (grid_pos INT UNSIGNED, grid_price_range FLOAT UNSIGNED, pos_size FLOAT UNSIGNED, time VARCHAR(50))")

            time = str(self.time_stamp())
            
            query = (f"INSERT INTO {table_name} () VALUES (%s, %s, %s, %s)")
            vals = (0, 0.0, 0, 0, 0.0, time)

            print(query)
            self.mycursor.execute(query, vals)
            self.db.commit()

        except mysql.connector.Error as error:
            print("Failed to update record to database: {}".format(error))


    def dcamp_create_new_grid_row(self):
        try:
            time = str(self.time_stamp())
            query = (f"INSERT INTO {table_name} () VALUES (%s, %s, %s, %s)")
            vals = (0, 0.0, 0, 0, 0.0, time)
            print(query)
            self.mycursor.execute(query, vals)
            self.db.commit()
        except mysql.connector.Error as error:
            print("Failed to update record to database: {}".format(error))


    #TODO: MAKE WORK 
    def replace_trade_data_value(self, position, value):
        try:
            table_name = self.trade_data_table_name
            trade_id = self.trade_id

            query = (f"UPDATE {self.trade_data_table_name} SET {position} = %s WHERE trade_id = %s")
            vals = (value, trade_id)
    
            print(query)
            self.mycursor.execute(query, vals)
            self.db.commit()
        except mysql.connector.Error as error:
            print("Failed to update record to database: {}".format(error))
            
    # create / delete tables:
    def dcamp_create_orders_table(self, table_name):
        try:
            print(f'creating new {table_name} orders table')
            self.mycursor.execute(f"CREATE TABLE {table_name} (trade_id VARCHAR(16), id VARCHAR(8), grid_pos INT UNSIGNED, link_id_pos INT UNSIGNED, link_name VARCHAR(8), side VARCHAR(8), status VARCHAR(12), input_quantity INT UNSIGNED, price FLOAT UNSIGNED, profit_percent FLOAT UNSIGNED, link_id VARCHAR(50), order_id VARCHAR(50), time VARCHAR(50))")
        except mysql.connector.Error as error:
            print("Failed to update record to database: {}".format(error))

    def delete_table(self, table_name):
        try:
            print(f'dropping table: {table_name}')
            query = "DROP TABLE " + str(table_name)
            self.mycursor.execute(query)
            self.db.commit()
        except mysql.connector.Error as error:
            print("Failed to update record to database: {}".format(error))

    # orders: 
    def replace_order(self, table_name, order):
        try:
            grid_pos = order['grid_pos']
            link_id_pos = order['order_pos']
            grid_id = (f'{grid_pos}{link_id_pos}')
            link_name = order['link_name']
            side = order['side']
            status = order['order_status']
            input_quantity = order['input_quantity']
            price = order['price']
            profit_percent = order['profit_percent']
            link_id = order['order_link_id']
            order_id = order['order_id']
            time = str(self.time_stamp())

            query = (f"UPDATE {table_name} SET grid_pos = %s, link_id_pos = %s, link_name = %s, side = %s, profit_percent = %s, status = %s, input_quantity = %s, price = %s, profit_percent = %s, link_id = %s, order_id = %s, time = %s WHERE id = %s")
            vals = (grid_pos, link_id_pos, link_name, side, profit_percent, status, input_quantity, price, profit_percent, link_id, order_id, time, grid_id)

            print(query, vals)
            print('')
            self.mycursor.execute(query, vals)
            self.db.commit()
        except mysql.connector.Error as error:
            print("Failed to update record to database: {}".format(error))

    def dcamp_create_new_empty_orders_row(self, table_name: str, grid_pos: int, link_id_pos: int):
        try:
            grid_id = (f'{grid_pos}{link_id_pos}')
            query = (f"INSERT INTO {table_name} () VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")
            print(query)
            self.mycursor.execute(query,(self.trade_id, grid_id, grid_pos, link_id_pos, 'empty', 'empty', 'empty', 0, 0, 0, 'empty', 'empty', 'empty'))
            self.db.commit()
        except mysql.connector.Error as error:
            print("Failed to update record to database: {}".format(error))

    def dcamp_create_new_order_row(self, order):
        try:
            grid_pos = order['grid_pos']
            link_id_pos = order['order_pos']
            grid_id = (f'{grid_pos}{link_id_pos}')
            link_name = order['link_name']
            side = order['side']
            status = order['order_status']
            input_quantity = order['input_quantity']
            price = order['price']
            profit_percent = order['profit_percent']
            link_id = order['order_link_id']
            order_id = order['order_id']
            time = str(self.time_stamp())

            if (status == 'Cancelled'):
                table_name = self.slipped_orders_table_name
            elif (status == 'Filled'):
                table_name = self.filled_orders_table_name

            query = (f"INSERT INTO {table_name} () VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")
            vals = (self.trade_id, grid_id, grid_pos, link_id_pos, link_name, side, status, input_quantity, price,  profit_percent, link_id, order_id, time)

            print(query)

            self.mycursor.execute(query, vals)
            self.db.commit()
        except mysql.connector.Error as error:
            print("Failed to update record to database: {}".format(error))

    def dcamp_replace_slipped_order_status(self, order):
        try:
            grid_pos = order['grid_pos']
            link_id_pos = order['order_pos']
            grid_id = (f'{grid_pos}{link_id_pos}')
            status = 'resolved'
            link_id = order['order_link_id']
            time = str(self.time_stamp())

            query = (f"UPDATE {self.slipped_orders_table_name} SET status = %s, time = %s WHERE link_id = %s")
            vals = (status, time,link_id)

            print(query, vals)
            print('')
            self.mycursor.execute(query, vals)
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
