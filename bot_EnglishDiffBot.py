"""

BOT_NAME="EnglishDiffBot"; modal deploy --name $BOT_NAME bot_${BOT_NAME}.py; curl -X POST https://api.poe.com/bot/fetch_settings/$BOT_NAME/$POE_ACCESS_KEY

Test message:
Please corect this massage.

"""
from __future__ import annotations

import difflib
from typing import AsyncIterable

import fastapi_poe.client
from fastapi_poe import PoeBot, make_app
from fastapi_poe.client import MetaMessage, stream_request
from fastapi_poe.types import QueryRequest, SettingsRequest, SettingsResponse
from modal import Image, Stub, asgi_app
from sse_starlette.sse import ServerSentEvent

fastapi_poe.client.MAX_EVENT_COUNT = 10000

LANGUAGE_PROMPT_TEMPLATE = """
You will follow the instructions from the user and fix the spelling, grammar and improve the style.

Please fix the following statement.

The statement begins.

```
{user_statement}
```

The statement has ended.

Only reply the fixed quoted text. Do not explain.
Do not begin or end your reply with inverted commas.
""".strip()


def markdown_diff(str1, str2):
    diff = difflib.ndiff(str1.split(), str2.split())
    result = []

    for token in diff:
        if token[0] == "-":
            result.append(f"~~{token[2:]}~~")  # strikethrough
        elif token[0] == "+":
            result.append(f"**{token[2:]}**")  # bold
        elif token[0] == " ":
            result.append(token[2:])

    return " ".join(result)


class EchoBot(PoeBot):
    async def get_response(self, query: QueryRequest) -> AsyncIterable[ServerSentEvent]:
        user_statement = query.query[-1].content
        print("user_statement", user_statement)

        wrapped_message = LANGUAGE_PROMPT_TEMPLATE.format(user_statement=user_statement)
        query.query[-1].content = wrapped_message
        query.query = [query.query[-1]]

        character_reply = ""
        async for msg in stream_request(query, "EnglishDiffTool", query.api_key):
            # Note: See https://poe.com/EnglishDiffTool for the system prompt
            if isinstance(msg, MetaMessage):
                continue
            elif msg.is_suggested_reply:
                yield self.suggested_reply_event(msg.text)
            elif msg.is_replace_response:
                yield self.replace_response_event(msg.text)
            else:
                character_reply += msg.text
                rendered_text = markdown_diff(user_statement, character_reply)
                yield self.replace_response_event(rendered_text)

        print("character_reply", character_reply)

    async def get_settings(self, setting: SettingsRequest) -> SettingsResponse:
        return SettingsResponse(
            server_bot_dependencies={"EnglishDiffTool": 1},
            allow_attachments=False,
            introduction_message="This bot will reply you the statement you made, with the language corrected.",
        )


bot = EchoBot()

image = Image.debian_slim().pip_install(
    "fastapi-poe==0.0.23", "huggingface-hub==0.16.4"
)

stub = Stub("poe-bot-quickstart")


@stub.function(image=image)
@asgi_app()
def fastapi_app():
    app = make_app(bot, allow_without_key=True)
    return app
