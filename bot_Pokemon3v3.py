"""

BOT_NAME="Pokemon3v3"; modal deploy --name $BOT_NAME bot_${BOT_NAME}.py; curl -X POST https://api.poe.com/bot/fetch_settings/$BOT_NAME/$POE_ACCESS_KEY

Test message:
Start

"""
from __future__ import annotations

from typing import AsyncIterable

from fastapi_poe import PoeBot
from fastapi_poe.client import stream_request
from fastapi_poe.types import (
    PartialResponse,
    QueryRequest,
    SettingsRequest,
    SettingsResponse,
)

from modal import Image, Stub, asgi_app
from fastapi_poe import make_app


class EchoBot(PoeBot):
    async def get_response(
        self, request: QueryRequest
    ) -> AsyncIterable[PartialResponse]:
        character_reply = ""
        async for msg in stream_request(request, "ChatGPT", request.access_key):
            yield msg

    async def get_settings(self, setting: SettingsRequest) -> SettingsResponse:
        return SettingsResponse(
            server_bot_dependencies={"ChatGPT": 1},
            introduction_message='Say "start".'
        )


bot = EchoBot()

image = Image.debian_slim().pip_install(
    "fastapi-poe==0.0.23",
)

stub = Stub("poe-bot-quickstart")


@stub.function(image=image)
@asgi_app()
def fastapi_app():
    app = make_app(bot, allow_without_key=True)
    return app
