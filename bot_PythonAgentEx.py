"""

modal deploy --name PythonAgentEx bot_PythonAgentEx.py
curl -X POST https://api.poe.com/bot/fetch_settings/PythonAgentEx/$POE_API_KEY

Test message:
echo z > a.txt
cat a.txt

"""

from __future__ import annotations

from typing import AsyncIterable

import os
import re
import requests

import modal
from fastapi_poe import PoeBot, make_app
from fastapi_poe.types import PartialResponse, QueryRequest, SettingsResponse
from modal import Image, Stub, asgi_app


def strip_code(code):
    if len(code.strip()) < 6:
        return code
    code = code.strip()
    if code.startswith("```") and code.endswith("```"):
        code = code[3:-3]
    return code



class EchoBot(PoeBot):
    async def get_response(
        self, request: QueryRequest
    ) -> AsyncIterable[PartialResponse]:
        last_message = request.query[-1].content
        vol = modal.NetworkFileSystem.lookup(f"vol-{request.user_id}")

        for attachment in request.query[-1].attachments:
            r = requests.get(attachment.url)
            with open(attachment.name, 'wb') as f:
                f.write(r.content)
            vol.add_local_file(attachment.name)

        code = strip_code(last_message)
        with open(f"{request.conversation_id}.py", 'w') as f:
            f.write(code)

        vol.add_local_file(f"{request.conversation_id}.py", f"{request.conversation_id}.py")

        stub.nfs = modal.NetworkFileSystem.persisted(f"vol-{request.user_id}")
        sb = stub.spawn_sandbox(
            "bash",
            "-c",
            f"cd /cache && python {request.conversation_id}.py",
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


    async def get_settings(self, setting: SettingsRequest) -> SettingsResponse:
        return SettingsResponse(
            server_bot_dependencies={"CheckPythonTool": 1},
            allow_attachments=True,  # to update when ready
        )


# specific to hosting with modal.com
image = Image.debian_slim().pip_install_from_requirements("requirements_PythonAgentEx.txt").env(
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
