from BybitWebsocket import BybitWebsocket
import config
import asyncio
import time
import pprint
import json

def print_hi():
    print('test')

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

async def timer2(interval, clock, func, *args):
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



def func_timer(fnc, arg):
    t0 = time.time()
    fnc()
    t1 = time.time()
    return (t1 - t0)

def ping(ws):
    ws.ping()
    # while True:
    data = ws.get_data("pong")
    if data:
        print(data)

async def subscribe_pos(interval, ws):
    ws.subscribe_position()
    while True:
        await asyncio.sleep(interval)
        data = ws.get_data("position")
        if data:
            new_data = data
            print(new_data[0]['liq_price'])
            print('')

async def get_order(interval, ws):
    ws.subscribe_order()
    while True:
        await asyncio.sleep(interval)
        data = ws.get_data("order")
        if data:
            print(data)



async def main():

    ws = BybitWebsocket(wsURL="wss://stream-testnet.bybit.com/realtime",
                        api_key=config.API_KEY, api_secret=config.API_SECRET)

    # timer_task_1 = asyncio.create_task(timer2(0.05, 7, print_hi))
    # timer_task_2 = asyncio.create_task(timer(0.05, 5, ping, ws))
    # pos_task = asyncio.create_task(subscribe_pos(0.05, ws))
    # order_task = asyncio.create_task(get_order(0.05, ws))

    ws.subscribe_execution()
    while True:
        data = ws.get_data("execution")
        if data:
            print(data)
            continue

    # await pos_task

    # print(timer2(ping, ws))
    # ping_1 = loop.create_task(timer(1, 5, ping(ws)))

    # await asyncio.wait(ping_1)

try:
    loop = asyncio.get_event_loop();  
    loop.run_until_complete(main())
except KeyboardInterrupt:
    print("keyboard input manual close")
# finally:
#     loop.close()