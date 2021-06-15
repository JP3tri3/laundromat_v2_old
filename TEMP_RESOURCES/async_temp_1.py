import asyncio
import time


async def say1(what, when):
    x = 0

    asyncio.ensure_future(say2('say2()', 1)) 
    while (x < 7):
        await asyncio.sleep(when)
        x += 1
        print('what: {}, x: {}'.format(what, x))
    return x

async def say2(what, when):
    i = 0
    while (i < 5):
        await asyncio.sleep(when)
        i += 1
        print('what: {}, i: {}'.format(what, i))
    return i

# def main():
#     loop = asyncio.get_event_loop()
#     asyncio.ensure_future(say1('say1()', 1))

#     loop.run_forever()

# try:
#     if __name__ == "__main__":               
#         main()    
# except KeyboardInterrupt:
#     print('closing loop')
#     pass

async def main():
    # asyncio.ensure_future(say1('say1()', 1))
    test1 = loop.create_task(say1('test1', 1))
    test2 = loop.create_task(say1('test2', 1))
    await asyncio.wait([test1, test2])
    return test1, test2

if __name__ == "__main__": 
    try:
        loop = asyncio.get_event_loop()
        # loop.set_debug(1)
        # asyncio.ensure_future(main())       
        # loop.run_forever()
        t1, t2 = loop.run_until_complete(main())
        print('t1: {}'.format(t1.result()))
        print('t2: {}'.format(t2.result()))
    except KeyboardInterrupt:
        print('closing loop')
        pass
    finally:
        loop.close()


# print("input1: {}, input2: {} ".format(var1, var2))