"""

modal deploy --name PythonAgentEx bot_PythonAgentEx.py
curl -X POST https://api.poe.com/bot/fetch_settings/PythonAgentEx/$POE_API_KEY

Test message:
download and save wine dataset
list directory

"""

from __future__ import annotations

from typing import AsyncIterable

import os
import re
import requests

import textwrap
import modal
from fastapi_poe import PoeBot, make_app
from fastapi_poe.client import MetaMessage, stream_request
from fastapi_poe.types import PartialResponse, QueryRequest, SettingsResponse
from modal import Image, Stub, asgi_app


def extract_code(reply):
    pattern = r"```python([\s\S]*?)```"
    matches = re.findall(pattern, reply)
    return "\n\n".join(matches)


def wrap_session(code):
    code = "\n".join(" "*12 + line for line in code.split("\n"))

    # there might be issues with multiline string
    # maybe exec resolves this issue
    return textwrap.dedent(
        f"""\
        import dill, os
        if os.path.exists("state.dill"):
            with open("state.dill", 'rb') as f:
                dill.load_session(f)
        try:
            {code}
        except Exception as e:
            with open('state.dill', 'wb') as f:
                dill.dump_session(f)
            raise e
        with open('state.dill', 'wb') as f:
            dill.dump_session(f)
        """
    )


class EchoBot(PoeBot):
    async def get_response(
        self, request: QueryRequest
    ) -> AsyncIterable[PartialResponse]:
        last_message = request.query[-1].content

        # procedure to create volume if it does not exist
        # tried other ways to write a code but has hydration issues
        try:
            vol = modal.NetworkFileSystem.lookup(f"vol-{request.user_id}")
        except:
            stub.nfs = modal.NetworkFileSystem.persisted(f"vol-{request.user_id}")
            sb = stub.spawn_sandbox(
                "bash",
                "-c",
                "cd /cache",
                network_file_systems={f"/cache": stub.nfs})
            sb.wait()
            vol = modal.NetworkFileSystem.lookup(f"vol-{request.user_id}")

        for query in request.query:
            for attachment in query.attachments:
                query.content += f"\n\nThe user has provided {attachment.name}"

        current_message = ""
        async for msg in stream_request(request, "CheckPythonTool", request.api_key):
            # Note: See https://poe.com/CheckPythonTool for the prompt
            if isinstance(msg, MetaMessage):
                continue
            elif msg.is_suggested_reply:
                yield self.suggested_reply_event(msg.text)
            elif msg.is_replace_response:
                yield self.replace_response_event(msg.text)
            else:
                current_message += msg.text
                yield self.replace_response_event(current_message)
                if extract_code(current_message):
                    break

        code = extract_code(current_message)
        if not code:
            return
        code = wrap_session(code)

        print("code")
        print(code)


        vol = modal.NetworkFileSystem.lookup(f"vol-{request.user_id}")

        for attachment in request.query[-1].attachments:
            r = requests.get(attachment.url)
            with open(attachment.name, 'wb') as f:
                f.write(r.content)
            vol.add_local_file(attachment.name)

        with open(f"{request.user_id}.py", 'w') as f:
            f.write(code)

        vol.add_local_file(f"{request.user_id}.py", f"{request.user_id}.py")

        stub.nfs = modal.NetworkFileSystem.persisted(f"vol-{request.user_id}")
        sb = stub.spawn_sandbox(
            "bash",
            "-c",
            f"cd /cache && python {request.user_id}.py",
            image=image_exec,
            network_file_systems={f"/cache": stub.nfs})
        sb.wait()

        output = sb.stdout.read()
        error = sb.stderr.read()

        nothing_returned = True

        if output:
            yield PartialResponse(text=f"""\n\n```output\n{output}\n```""")
            nothing_returned = False
        if error:
            yield PartialResponse(text=f"""\n\n```error\n{error}\n```""")
            nothing_returned = False

        if nothing_returned:
            yield PartialResponse(text=f"""\n\nNo output or error returned.""")


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
image_exec = Image.debian_slim().pip_install(
    "fastapi-poe==0.0.19",
    "huggingface-hub==0.16.4",
    "ipython",
    "scipy",
    "matplotlib",
    "scikit-learn",
    "pandas",
    "ortools",
    "torch",
    "torchvision",
    "tensorflow",
    "spacy",
    "transformers",
    "opencv-python-headless",
    "nltk",
    "openai",
    "requests",
    "beautifulsoup4",
    "newspaper3k",
    "feedparser",
    "sympy",
    "tensorflow",
    "cartopy",
    "wordcloud",
    "gensim",
    "keras",
    "librosa",
    "XlsxWriter",
    "docx2txt",
    "markdownify",
    "pdfminer.six",
    "Pillow",
    "opencv-python",
    "sortedcontainers",
    "intervaltree",
    "geopandas",
    "basemap",
    "tiktoken",
    "basemap-data-hires",
    "cartopy",
    "yfinance",
    "dill",
)
stub = Stub("poe-bot-quickstart")

bot = EchoBot()

@stub.function(image=image)
@asgi_app()
def fastapi_app():
    app = make_app(bot, api_key=os.environ["POE_API_KEY"])
    return app
