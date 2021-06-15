import asyncio
import websockets

async def update_webhook(websocket, path):
    data = await websocket.recv()
    print("< {}".format(data))

    # greeting = "webhook_data: {}".format(data)
    # await websocket.send(greeting)
    # print("> {}".format(greeting))

start_server = websockets.serve(update_webhook, 'localhost', 8765)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()