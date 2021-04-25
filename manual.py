import sys
import asyncio
from view.ui import Ui


async def main():

    startUi = Ui()

    startUi.start()


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
