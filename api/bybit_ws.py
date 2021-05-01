from BybitWebsocket import BybitWebsocket
import asyncio
import pprint

class Bybit_WS:

    def __init__(self, api_key, api_secret, symbol_pair, test_true_false):
        self.api_key = api_key
        self.api_secret = api_secret
        self.symbol_pair = symbol_pair
        self.interval = 0.5

        if (test_true_false == True):
            wsURL = "wss://stream-testnet.bybit.com/realtime"
        else:
            wsURL = "wss://stream.bybit.com/realtime"

        self.ws = BybitWebsocket(wsURL=wsURL,
                        api_key=self.api_key, 
                        api_secret=self.api_secret)

        print('... Bybit_WS initialized ...')

    async def ping(self, interval, timer):
        ticker = 0
        while True:
            await asyncio.sleep(interval)
            if int(ticker) == int(timer):
                self.ws.ping()
                data = self.ws.get_data("pong")
                # if data:
                #     print(data)
                ticker = 0

            ticker += interval

    async def get_execution(self):
        self.ws.subscribe_execution()
        while True:
            await asyncio.sleep(self.interval)
            data = self.ws.get_data("execution")
            if data:
                print('')
                print('get_execution')
                print(pprint.pprint(data))


    async def get_pos_info(self):
        self.ws.subscribe_position()
        flag = True
        while (flag == True):
            await asyncio.sleep(self.interval)
            data = self.ws.get_data("position")
            if data:
                new_data = data
                # print(pprint.pprint(new_data))
                flag = False
        print(pprint.pprint(new_data))
        return new_data

    async def get_pos_size(self, pos_size_api):
        self.ws.subscribe_position()
        flag = True
        while (flag == True):
            await asyncio.sleep(self.interval)
            data = self.ws.get_data("position")
            # pos_size = data[0]
            if data:
                pos_size = data[0]['size']
                if (pos_size != pos_size_api):
                    flag = False
        # print(pos_size)
        # return pos_size       


    async def get_order(self):
        self.ws.subscribe_order()
        while True:
            await asyncio.sleep(self.interval)
            data = self.ws.get_data("order")
            if data:
                print(pprint.pprint(data))
                return data
                    
    # async def get_filled_order(self):
    #     self.ws.subscribe_order()
    #     while True:
    #         await asyncio.sleep(self.interval)
    #         data = self.ws.get_data("order")
    #         if data:
    #             filled_order = data[0]
    #             order_link_id = filled_order['order_link_id']
    #             order_status = filled_order['order_status']
    #             if (order_status == 'Filled'):
    #                 print(f'filled order: {order_link_id}')
    #                 return filled_order

    async def instrument_info(self):
        self.ws.subscribe_instrument_info(symbol=self.symbol_pair)
        print('subscribed instrument info')
        while True:
            await asyncio.sleep(self.interval)
            data = self.ws.get_data("instrument_info.100ms.BTCUSD")
            if data:
                print(pprint.pprint(data))

    async def get_last_price(self):
        self.ws.subscribe_instrument_info(symbol=self.symbol_pair)
        index_price_key = 'index_price_e4'
        last_price_key = 'last_price_e4'
        mark_price_key = 'mark_price_e4'
        while True:
            await asyncio.sleep(self.interval)
            data = self.ws.get_data("instrument_info.100ms.BTCUSD")
            if data:
                if 'update' in data:
                    new_data = data['update'][0]
                    if index_price_key in new_data:
                        index_price = new_data[index_price_key]
                        print('index_price: ')
                        print(float(index_price) / 10000)   
                        print('')

                    if last_price_key in new_data:
                        last_price = new_data[last_price_key]
                        print('last_price: ')
                        print(float(last_price) / 10000) 
                        print('')

                    if mark_price_key in new_data:
                        mark_price_key = new_data[mark_price_key]
                        print('mark_price: ')
                        print(float(mark_price_key) / 10000) 
                        print('')
