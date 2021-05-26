from BybitWebsocket import BybitWebsocket # type: ignore
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
        while (True):
            await asyncio.sleep(self.interval)
            data = self.ws.get_data("position")
            if data:
                return data[0]

    async def get_pos_size(self):
        self.ws.subscribe_position()
        while (True):
            await asyncio.sleep(self.interval)
            data = self.ws.get_data("position")
            if data:
                pos_size = data[0]['size']
                return pos_size


    async def get_order(self):
        self.ws.subscribe_order()
        while True:
            await asyncio.sleep(self.interval)
            data = self.ws.get_data("order")
            if data:
                # print(pprint.pprint(data))
                return data

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
        last_price_key = 'last_price_e4'
        
        while True:
            await asyncio.sleep(self.interval)
            data = self.ws.get_data(f"instrument_info.100ms.{self.symbol_pair}")
            if data:
                if 'update' in data:
                    new_data = data['update'][0]
                    if last_price_key in new_data:
                        last_price = new_data[last_price_key]
                        calc_last_price = float(last_price) / 10000
                        return calc_last_price

    async def get_mark_price(self):
        self.ws.subscribe_instrument_info(symbol=self.symbol_pair)
        mark_price_key = 'mark_price_e4'
        
        while True:
            await asyncio.sleep(self.interval)
            data = self.ws.get_data(f"instrument_info.100ms.{self.symbol_pair}")
            if data:
                if 'update' in data:
                    new_data = data['update'][0]
                    if mark_price_key in new_data:
                        mark_price = new_data[mark_price_key]
                        calc_mark_price = float(mark_price) / 10000
                        return calc_mark_price

    async def get_index_price(self):
        self.ws.subscribe_instrument_info(symbol=self.symbol_pair)
        index_price_key = 'index_price_e4'
        
        while True:
            await asyncio.sleep(self.interval)
            data = self.ws.get_data(f"instrument_info.100ms.{self.symbol_pair}")
            if data:
                if 'update' in data:
                    new_data = data['update'][0]
                    if index_price_key in new_data:
                        index_price = new_data[index_price_key]
                        calc_index_price = float(index_price) / 10000
                        return calc_index_price