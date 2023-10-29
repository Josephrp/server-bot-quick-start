"""

modal deploy --name nougatOCR bot_nougatOCR.py
curl -X POST https://api.poe.com/bot/fetch_settings/nougatOCR/$POE_API_KEY

Test message:
https://pjreddie.com/static/Redmon%20Resume.pdf

"""
from __future__ import annotations

from typing import AsyncIterable

import fastapi_poe.client
from fastapi_poe import PoeBot
from fastapi_poe.types import QueryRequest, SettingsRequest, SettingsResponse
from sse_starlette.sse import ServerSentEvent

fastapi_poe.client.MAX_EVENT_COUNT = 10000

import modal

# https://modalbetatesters.slack.com/archives/C031Z7H15DG/p1675177408741889?thread_ts=1675174647.477169&cid=C031Z7H15DG
modal.app._is_container_app = False


class EchoBot(PoeBot):
    async def get_response(self, query: QueryRequest) -> AsyncIterable[ServerSentEvent]:
        if (
            query.query[-1].attachments
            and query.query[-1].attachments[0].content_type == "application/pdf"
        ):
            content_url = query.query[-1].attachments[0].url
            yield self.text_event(
                "PDF attachment received. Please wait while we convert ..."
            )
        else:
            yield self.replace_response_event("PDF attachment not found.")

        try:
            f = modal.Function.lookup("ocr-shared", "nougat_ocr")
            captured_output = f.remote(content_url)  # need async await?
        except modal.exception.TimeoutError:
            yield self.replace_response_event("Time limit exceeded.")
            return

        yield self.replace_response_event(captured_output)

    async def get_settings(self, setting: SettingsRequest) -> SettingsResponse:
        return SettingsResponse(
            server_bot_dependencies={},
            allow_attachments=True,
            introduction_message="Please upload your document (pdf).",
        )


# Welcome to the Poe server bot quick start. This repo includes starter code that allows you to
# quickly get a bot running. By default, the code uses the EchoBot, which is a simple bot that
# echos a message back at its user and is a good starting point for your bot, but you can
# comment/uncomment any of the following code to try out other example bots or build on top
# of the EchoBot.

import os

from fastapi_poe import make_app
from modal import Image, Stub, asgi_app

# Echo bot is a very simple bot that just echoes back the user's last message.
bot = EchoBot()

# A sample bot that showcases the capabilities the protocol provides. Please see the
# following link for the full set of available message commands:
# https://github.com/poe-platform/server-bot-quick-start/blob/main/catbot/catbot.md
# bot = CatBot()

# A bot that uses Poe's ChatGPT bot, but makes all messages ALL CAPS.
# Good simple example of using another bot using Poe's third party bot API.
# For more details, see: https://developer.poe.com/server-bots/accessing-other-bots-on-poe
# bot = ChatGPTAllCapsBot()

# A bot that calls two different bots (default to Assistant and Claude-Instant) and displays the
# results. Users can decide what bots to call by including in the message a string
# of the form (botname1 vs botname2)
# bot = BattleBot()

# A chatbot based on a model hosted on HuggingFace.
# bot = HuggingFaceBot("microsoft/DialoGPT-medium")

# The following is setup code that is required to host with modal.com
image = (
    Image.debian_slim()
    .apt_install("libpoppler-cpp-dev")
    .apt_install("tesseract-ocr-eng")
    .pip_install("fastapi-poe==0.0.23")
).env(
    {
        "OPENAI_API_KEY": os.environ["OPENAI_API_KEY"],
        "POE_API_KEY": os.environ["POE_API_KEY"],
    }
)
stub = Stub("poe-bot-quickstart")


@stub.function(image=image)
@asgi_app()
def fastapi_app():
    # Optionally, provide your Poe access key here:
    # 1. You can go to https://poe.com/create_bot?server=1 to generate an access key.
    # 2. We strongly recommend using a key for a production bot to prevent abuse,
    # but the starter example disables the key check for convenience.
    # 3. You can also store your access key on modal.com and retrieve it in this function
    # by following the instructions at: https://modal.com/docs/guide/secrets
    # POE_ACCESS_KEY = ""
    # app = make_app(bot, access_key=POE_ACCESS_KEY)
    app = make_app(bot, api_key=os.environ["POE_API_KEY"])
    return app
