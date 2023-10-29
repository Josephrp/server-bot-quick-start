"""

BOT_NAME="tiktoken"; modal deploy --name $BOT_NAME bot_${BOT_NAME}.py; curl -X POST https://api.poe.com/bot/fetch_settings/$BOT_NAME/$POE_ACCESS_KEY

Test message:
ChatGPT

"""
from __future__ import annotations

from typing import AsyncIterable

import fastapi_poe.client
import tiktoken
from fastapi_poe import PoeBot, make_app
from fastapi_poe.types import QueryRequest
from modal import Image, Stub, asgi_app
from sse_starlette.sse import ServerSentEvent

fastapi_poe.client.MAX_EVENT_COUNT = 10000


encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")


class EchoBot(PoeBot):
    async def get_response(self, query: QueryRequest) -> AsyncIterable[ServerSentEvent]:
        last_message = query.query[-1].content
        tokens = encoding.encode(last_message)
        last_message = " | ".join(
            [
                str((encoding.decode_single_token_bytes(token), token))[2:-1]
                for token in tokens
            ]
        )
        yield self.text_event(last_message)


# Welcome to the Poe API tutorial. The starter code provided provides you with a quick way to get
# a bot running. By default, the starter code uses the EchoBot, which is a simple bot that echos
# a message back at its user and is a good starting point for your bot, but you can
# comment/uncomment any of the following code to try out other example bots.

# Echo bot is a very simple bot that just echoes back the user's last message.
bot = EchoBot()

# A sample bot that showcases the capabilities the protocol provides. Please see the
# following link for the full set of available message commands:
# https://github.com/poe-platform/api-bot-tutorial/blob/main/catbot/catbot.md
# bot = CatBot()

# A bot that wraps Poe's ChatGPT bot, but makes all messages ALL CAPS.
# Good simple example of calling on another bot using Poe's API.
# bot = ChatGPTAllCapsBot()

# A bot that calls two different bots (by default Sage and Claude-Instant) and
# shows the results. Can customize what bots to call by including in message a string
# of the form (botname1 vs botname2)
# bot = BattleBot()

# Optionally add your Poe API key here. You can go to https://poe.com/create_bot?api=1 to generate
# one. We strongly recommend adding this key for a production bot to prevent abuse,
# but the starter example disables the key check for convenience.
# POE_ACCESS_KEY = ""
# app = make_app(bot, api_key=POE_ACCESS_KEY)

# specific to hosting with modal.com
image = Image.debian_slim().pip_install("fastapi-poe==0.0.23", "tiktoken")
stub = Stub("poe-bot-quickstart")


@stub.function(image=image)
@asgi_app()
def fastapi_app():
    app = make_app(bot, allow_without_key=True)
    return app
