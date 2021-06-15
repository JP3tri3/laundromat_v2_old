import sys
sys.path.append("..")
import asyncio
import websockets # type: ignore
from api.bybit_ws import Bybit_WS # type: ignore
import config

ws = Bybit_WS(config.BYBIT_TESTNET_API_KEY, config.BYBIT_TESTNET_API_SECRET, 'ETHUSD', True)

async def main():

    task_collect_orders = asyncio.create_task(collect_orders())

    await task_collect_orders

# collect orders via ws
async def collect_orders():

    print('collecting orders')
    while True:
        await asyncio.sleep(0)
        order = await ws.get_order()
        # print(type(order))
        # str_order = str(order)
        # print(type(str_order))
        # print(str_order)
        # eval_order = eval(str_order)
        # print(type(eval_order))

        # test_encode = order.encode('utf-8')

        # print(test_encode)
        await test_send_message(order)

async def test_send_message(message):
    async with websockets.connect('ws://localhost:8765') as websocket:
        str_message = str(message)
        await websocket.send(str_message)
        print(f'message_sent')        

if __name__ == "__main__":  
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("closed by interrupt")
