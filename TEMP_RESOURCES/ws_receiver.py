import asyncio
import websockets

async def main():

    # websockets.serve(update_webhook, 'localhost', 8765)
    task_count = asyncio.create_task(count())
    # task_update = asyncio.create_task(update_webhook('localhost', 8765))

    await task_count
    # await task_update

async def update_webhook(websocket, path):
    
    while True:
        # await asyncio.sleep(0)
        data = await websocket.recv()
        print(data)
        # if data:
        #     print("< {}".format(data))

    # greeting = "webhook_data: {}".format(data)
    # await websocket.send(greeting)
    # print("> {}".format(greeting))

async def count():
    counter = 0
    clock = 30

    while True:
        counter += 1
        if (counter == clock):
            counter = 0

        await asyncio.sleep(1)
        print(f'counter: {counter}')



if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        start_server = websockets.serve(update_webhook, 'localhost', 8765)
        loop.run_until_complete(asyncio.gather(start_server, main()))
        loop.run_forever()
    except KeyboardInterrupt:
        print("closed by interrupt")