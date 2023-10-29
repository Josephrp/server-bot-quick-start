"""

BOT_NAME="PythonAgent"; modal deploy --name $BOT_NAME bot_${BOT_NAME}.py; curl -X POST https://api.poe.com/bot/fetch_settings/$BOT_NAME/$POE_API_KEY

Test message:
download and save wine dataset
list directory

"""

import os

from modal import Stub, asgi_app

from bot_PythonAgent import PythonAgentBot

bot = PythonAgentBot()
bot.prompt_bot = "PythonAgentExTool"

stub = Stub()
bot = PythonAgentBot()


@stub.function(image=image_bot)
@asgi_app()
def fastapi_app():
    app = make_app(bot, api_key=os.environ["POE_API_KEY"])
    return app
