"""

Sample bot that echoes back messages.

modal deploy --name CommandShell bot_CommandShell.py
curl -X POST https://api.poe.com/bot/fetch_settings/CommandShell/$POE_API_KEY

Test message:
What is the difference between https://arxiv.org/pdf/2201.11903.pdf and https://arxiv.org/pdf/2305.10601.pdf

"""
from __future__ import annotations

from typing import AsyncIterable

from fastapi_poe import PoeBot, make_app
from fastapi_poe.types import PartialResponse, QueryRequest
from modal import Image, Stub, asgi_app
import modal


class EchoBot(PoeBot):
    async def get_response(
        self, request: QueryRequest
    ) -> AsyncIterable[PartialResponse]:
        last_message = request.query[-1].content
        stub.nfs = modal.NetworkFileSystem.persisted(f"vol-{request.conversation_id}")
        sb = stub.spawn_sandbox(last_message, network_file_systems={"/cache": stub.nfs})
        sb.wait()

        output = sb.stdout.read()
        error = sb.stderr.read()
        yield PartialResponse(text=f"""```output\n{output}\n```\n\n""")
        yield PartialResponse(text=f"""```error\n{error}\n```""")


# specific to hosting with modal.com
image = Image.debian_slim().pip_install_from_requirements("requirements_CommandShell.txt")
stub = Stub("poe-bot-quickstart")

bot = EchoBot()

@stub.function(image=image)
@asgi_app()
def fastapi_app():
    app = make_app(bot, allow_without_key=True)
    return app
