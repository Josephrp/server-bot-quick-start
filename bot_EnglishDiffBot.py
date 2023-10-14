"""

modal deploy --name EnglishDiffBot bot_EnglishDiffBot.py
curl -X POST https://api.poe.com/bot/fetch_settings/EnglishDiffBot/$POE_API_KEY

Test message:
Please corect this massage.

"""
from __future__ import annotations

import difflib
from typing import AsyncIterable

from fastapi_poe import PoeBot, run
from fastapi_poe.client import MetaMessage, stream_request
from fastapi_poe.types import QueryRequest, SettingsRequest, SettingsResponse
from sse_starlette.sse import ServerSentEvent

import fastapi_poe
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
            introduction_message="This bot will reply you the statement you made, with the language corrected."
        )

# Welcome to the Poe API tutorial. The starter code provided provides you with a quick way to get
# a bot running. By default, the starter code uses the EchoBot, which is a simple bot that echos
# a message back at its user and is a good starting point for your bot, but you can
# comment/uncomment any of the following code to try out other example bots.

from fastapi_poe import make_app
from modal import Image, Stub, asgi_app

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

# A chatbot based on a model hosted on HuggingFace.
# bot = HuggingFaceBot("microsoft/DialoGPT-medium")

# The following is setup code that is required to host with modal.com
image = Image.debian_slim().pip_install_from_requirements("requirements_EnglishDiffBot.txt")
# Rename "poe-bot-quickstart" to your preferred app name.
stub = Stub("poe-bot-quickstart")


@stub.function(image=image)
@asgi_app()
def fastapi_app():
    # Optionally, add your Poe API key here:
    # 1. You can go to https://poe.com/create_bot?api=1 to generate an API key.
    # 2. We strongly recommend using a key for a production bot to prevent abuse,
    # but the starter example disables the key check for convenience.
    # 3. You can also store your API key on modal.com and retrieve it in this function
    # by following the instructions at: https://modal.com/docs/guide/secrets
    # POE_API_KEY = ""
    # app = make_app(bot, api_key=POE_API_KEY)
    app = make_app(bot, allow_without_key=True)
    return app
