import sys
sys.path.append("..")
import config # type: ignore
# from time import time, sleep
import json
import time
# import asyncio
# from database.database import Database as db # type: ignore
from strategies.dca_db import DCA_DB as dca_db # type: ignore
from sanic import Sanic # type: ignore
# from sanic import response # type: ignore
# from sanic.request import Request # type: ignore
from sanic.response import json # type: ignore
from sanic_jinja2 import SanicJinja2 # type: ignore
# import asyncio

##TO DO UPDATE IMPORTS / CHECK STRAT

app = Sanic(__name__)
jinja = SanicJinja2(app, pkg_name="listener")

myTime = int(time.time() * 1000)
trendFlag = False

@app.route('/')
async def index(request):
    return jinja.render("index.html", request)


@app.route('/webhook', methods=['POST'])
async def webhook(request):

    data = request.json

    # persistent_data = data['persistent_data']

    if data['passphrase'] != config.WEBHOOK_PASSPHRASE:
        print("invalid passphrase")
        return json({
            "code": "error",
            "message": "Invalid Passphrase"
        })
    else:
        # if(persistent_data == 'True'):

        #     table_id = data['input_name']
        #     last_candle_high = data['last_candle_high']
        #     last_candle_low = data['last_candle_low']
        #     last_candle_vwap = data['last_candle_vwap']
        #     wt1 = data['wt1']
        #     wt2 = data['wt2']

        #     db().update_strat_values(table_id, wt1, wt2, last_candle_high, last_candle_low, last_candle_vwap)        

        # else:

        print(data)
        await dca_db.replace_tf_trigger_values(data)


        return json({
            "code": "success",
            "message": "json updated"
        })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
