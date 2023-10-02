"""

modal deploy --name nougatOCR bot_nougatOCR.py
curl -X POST https://api.poe.com/bot/fetch_settings/TesseractOCR/$POE_API_KEY

Test message:
https://pjreddie.com/static/Redmon%20Resume.pdf

"""
from __future__ import annotations

from collections import defaultdict
from io import BytesIO
from typing import AsyncIterable

import openai
import pdftotext
import pytesseract
import requests

from docx import Document
from fastapi_poe import PoeBot, run
from fastapi_poe.types import QueryRequest, SettingsResponse
from PIL import Image as PILImage
from sse_starlette.sse import ServerSentEvent


# not working need to fix

class EchoBot(PoeBot):
    async def get_response(self, query: QueryRequest) -> AsyncIterable[ServerSentEvent]:
        user_statement: str = query.query[-1].content
        print(query.conversation_id, user_statement)

        image_data = None
        filename = "image.png"
        if os.path.isfile(filename):
            with open(filename, "rb") as f:
                image_data = f.read()
            os.remove(filename)

        if query.conversation_id not in url_cache:
            # TODO: validate user_statement is not malicious
            if len(user_statement.strip().split()) > 1:
                yield self.text_event(MULTIWORD_FAILURE_REPLY)
                return

            captured_output = f.call(code)

    async def get_settings(self, setting: SettingsRequest) -> SettingsResponse:
        return SettingsResponse(
            server_bot_dependencies={},
            allow_attachments=True,
            introduction_message="Please upload a pdf."
        )


# Welcome to the Poe server bot quick start. This repo includes starter code that allows you to
# quickly get a bot running. By default, the code uses the EchoBot, which is a simple bot that
# echos a message back at its user and is a good starting point for your bot, but you can
# comment/uncomment any of the following code to try out other example bots or build on top
# of the EchoBot.

import os

from fastapi_poe import make_app
from modal import Image, Stub, asgi_app

from catbot import CatBot
from huggingface_bot import HuggingFaceBot

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
    .pip_install_from_requirements("requirements_TesseractOCR.txt")
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
