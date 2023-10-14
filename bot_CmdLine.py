"""

modal deploy --name CmdLine bot_CmdLine.py
curl -X POST https://api.poe.com/bot/fetch_settings/CmdLine/$POE_API_KEY

Test message:
echo z > a.txt
cat a.txt

"""

from __future__ import annotations

from typing import AsyncIterable

from fastapi_poe import PoeBot, make_app
from fastapi_poe.types import PartialResponse, QueryRequest
from modal import Image, Stub, asgi_app
import modal
import os


class EchoBot(PoeBot):
    async def get_response(
        self, request: QueryRequest
    ) -> AsyncIterable[PartialResponse]:
        last_message = request.query[-1].content
        stub.nfs = modal.NetworkFileSystem.persisted(f"vol-{request.user_id}")
        sb = stub.spawn_sandbox(
            "bash",
            "-c",
            f"cd /cache && {last_message}",
            network_file_systems={f"/cache": stub.nfs})
        sb.wait()

        output = sb.stdout.read()
        error = sb.stderr.read()

        nothing_returned = True

        if output:
            yield PartialResponse(text=f"""```output\n{output}\n```""")
            nothing_returned = False
        if output and error:
            yield PartialResponse(text=f"""\n\n""")
        if error:
            yield PartialResponse(text=f"""```error\n{error}\n```""")
            nothing_returned = False

        if nothing_returned:
            yield PartialResponse(text=f"""No output or error returned.""")


# specific to hosting with modal.com
image = Image.debian_slim().pip_install_from_requirements("requirements_CommandShell.txt").env(
    {
        "POE_API_KEY": os.environ["POE_API_KEY"],
    }
)
stub = Stub("poe-bot-quickstart")

bot = EchoBot()

@stub.function(image=image)
@asgi_app()
def fastapi_app():
    app = make_app(bot, api_key=os.environ["POE_API_KEY"])
    return app
