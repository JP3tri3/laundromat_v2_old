import sys
sys.path.append("..")
import config # type: ignore
import json
# from database.database import Database as db # type: ignore
from database import database as mdb # type: ignore
from sanic import Sanic # type: ignore
# from sanic import response # type: ignore
# from sanic.request import Request # type: ignore
from sanic.response import json # type: ignore
from sanic_jinja2 import SanicJinja2 # type: ignore
# import asyncio

class Listener_Test:
    app = Sanic(__name__)
    jinja = SanicJinja2(app, pkg_name="listener")


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

            await mdb.replace_tf_trigger_values(data)

            return json({
                "code": "success",
                "message": "json updated"
            })

    if __name__ == "__main__":
        app.run(host="0.0.0.0", port=8000, debug=True)
