"""

BOT_NAME="PythonAgent"; modal deploy --name $BOT_NAME bot_${BOT_NAME}.py; curl -X POST https://api.poe.com/bot/fetch_settings/$BOT_NAME/$POE_ACCESS_KEY

Test message:
download and save wine dataset
list directory

"""

from __future__ import annotations

import os
import re
import textwrap
from typing import AsyncIterable

import modal
import requests
from fastapi_poe import PoeBot, make_app
from fastapi_poe.client import MetaMessage, stream_request
from fastapi_poe.types import (
    PartialResponse,
    ProtocolMessage,
    QueryRequest,
    SettingsRequest,
    SettingsResponse,
)
from modal import Image, Stub, asgi_app


def extract_code(reply):
    pattern = r"```python([\s\S]*?)```"
    matches = re.findall(pattern, reply)
    return "\n\n".join(matches)


PYTHON_AGENT_SYSTEM_PROMPT = """
You write the Python code for me

When you return Python code
- Encapsulate all Python code within triple backticks (i.e ```python) with newlines.
- The Python code should either print something or plot something
- The Python code should not use input().

Python packages already installed
numpy
scipy
matplotlib
scikit-learn
pandas
ortools
torch
torchvision
tensorflow
transformers
opencv-python-headless
nltk
openai
requests
beautifulsoup4
newspaper3k
feedparser
sympy
yfinance
basemap (in mpl_toolkits.basemap)
"""

PYTHON_AGENT_SYSTEM_MESSAGE = ProtocolMessage(
    role="system", content=PYTHON_AGENT_SYSTEM_PROMPT
)

CODE_WITH_WRAPPERS = """\
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.pyplot import savefig

def save_image(filename):
    def decorator(func):
        def wrapper(*args, **kwargs):
            func(*args, **kwargs)
            savefig(filename)
        return wrapper
    return decorator

plt.show = save_image('image.png')(plt.show)
plt.savefig = save_image('image.png')(plt.savefig)

import dill, os, pickle
if os.path.exists("{conversation_id}.dill"):
    try:
        with open("{conversation_id}.dill", 'rb') as f:
            dill.load_session(f)
    except:
        pass

{code}

with open('{conversation_id}.dill', 'wb') as f:
    dill.dump_session(f)
"""

SIMULATED_USER_REPLY_OUTPUT_ONLY = """\
The code was executed and this is the output.
```output
{output}
```
"""

SIMULATED_USER_REPLY_ERROR_ONLY = """\
The code was executed and this is the error.
```error
{error}
```
"""

SIMULATED_USER_REPLY_OUTPUT_AND_ERROR = """\
The code was executed and this is the error.
```output
{output}
```

```error
{error}
```
"""

SIMULATED_USER_REPLY_NO_OUTPUT_OR_ERROR = """\
The code was executed without issues, without any standard output.
"""

SIMULATED_USER_SUFFIX_IMAGE_FOUND = """

The code executed returned an image.
"""

SIMULATED_USER_SUFFIX_IMAGE_NOT_FOUND = """

The code executed did not return any image.
"""

SIMULATED_USER_SUFFIX_PROMPT = """

Carefully read the output and error to check if my request is fulfilled.
If there is an issue, you will write Python code to fix it without involving me at all.
"""


def wrap_session(code, conversation_id):
    # the wrapper code
    # - load session with dill (for the same conversation)
    # - execute the code
    # - save to image.png on plt.plot() and plt.show()
    # - save session with dill (if execution is successful)

    return CODE_WITH_WRAPPERS.format(code=code, conversation_id=conversation_id)


class PythonAgentBot(PoeBot):
    prompt_bot = "GPT-3.5-Turbo-Instruct"

    async def get_response(
        self, request: QueryRequest
    ) -> AsyncIterable[PartialResponse]:
        last_message = request.query[-1].content
        print("user_message")
        print(last_message)

        request.query = [PYTHON_AGENT_SYSTEM_MESSAGE] + request.query
        request.logit_bias = {"21362": -10}  # censor "![", but does this work?
        request.temperature = 0.1  # does this work?

        # procedure to create volume if it does not exist
        # tried other ways to write a code but has hydration issues
        try:
            vol = modal.NetworkFileSystem.lookup(f"vol-{request.user_id}")
        except:
            stub.nfs = modal.NetworkFileSystem.persisted(f"vol-{request.user_id}")
            sb = stub.spawn_sandbox(
                "bash", "-c", "cd /cache", network_file_systems={"/cache": stub.nfs}
            )
            sb.wait()
            vol = modal.NetworkFileSystem.lookup(f"vol-{request.user_id}")

        for query in request.query:
            for attachment in query.attachments:
                query.content += f"\n\nThe user has provided {attachment.name} in the current directory."
            query.attachments = []

        # upload files in latest user message
        for attachment in request.query[-1].attachments:
            r = requests.get(attachment.url)
            with open(attachment.name, "wb") as f:
                f.write(r.content)
            vol.add_local_file(attachment.name)

        for code_iteration_count in range(5):
            print("code_iteration_count", code_iteration_count)

            current_bot_reply = ""
            async for msg in stream_request(
                request, self.prompt_bot, request.api_key
            ):
                if isinstance(msg, MetaMessage):
                    continue
                elif msg.is_suggested_reply:
                    yield self.suggested_reply_event(msg.text)
                elif msg.is_replace_response:
                    yield self.replace_response_event(msg.text)
                else:
                    current_bot_reply += msg.text
                    yield self.text_event(msg.text)
                    if extract_code(current_bot_reply):
                        # break when a Python code block is detected
                        break

            message = ProtocolMessage(role="bot", content=current_bot_reply)
            request.query.append(message)

            # if the bot output does not have code, terminate
            code = extract_code(current_bot_reply)
            if not code:
                return

            # prepare code for execution
            print("code")
            print(code)
            code = wrap_session(code, conversation_id=request.conversation_id)

            # upload python script
            with open(f"{request.user_id}.py", "w") as f:
                f.write(code)
            vol.add_local_file(f"{request.user_id}.py", f"{request.user_id}.py")

            # execute code
            stub.nfs = modal.NetworkFileSystem.persisted(f"vol-{request.user_id}")
            sb = stub.spawn_sandbox(
                "bash",
                "-c",
                f"cd /cache && python {request.user_id}.py",
                image=image_exec,
                network_file_systems={"/cache": stub.nfs},
            )
            sb.wait()

            output = sb.stdout.read()
            error = sb.stderr.read()

            print("len(output)", len(output))
            print("len(error)", len(error))
            if error:  # for monitoring
                print("error")
                print(error)

            current_user_simulated_reply = ""
            if output and error:
                yield PartialResponse(
                    text=textwrap.dedent(f"\n\n```output\n{output}```\n\n")
                )
                yield PartialResponse(
                    text=textwrap.dedent(f"\n\n```error\n{error}```\n\n")
                )
                current_user_simulated_reply = (
                    SIMULATED_USER_REPLY_OUTPUT_AND_ERROR.format(output=output, error=error)
                )
            elif output:
                yield PartialResponse(
                    text=textwrap.dedent(f"\n\n```output\n{output}```\n\n")
                )
                current_user_simulated_reply = SIMULATED_USER_REPLY_OUTPUT_ONLY.format(
                    output=output
                )
            elif error:
                yield PartialResponse(
                    text=textwrap.dedent(f"\n\n```error\n{error}```\n\n")
                )
                current_user_simulated_reply = SIMULATED_USER_REPLY_ERROR_ONLY.format(
                    error=error
                )
            else:
                current_user_simulated_reply = SIMULATED_USER_REPLY_NO_OUTPUT_OR_ERROR

            # upload image and get image url
            image_url = None
            if any("image.png" in str(entry) for entry in vol.listdir("*")):
                # some roundabout way to check if image file is in directory
                with open("image.png", "wb") as f:
                    for chunk in vol.read_file("image.png"):
                        f.write(chunk)

                image_data = None
                with open("image.png", "rb") as f:
                    image_data = f.read()

                print("len(image_data)", len(image_data))
                if image_data:
                    f = modal.Function.lookup("image-upload-shared", "upload_file")
                    image_url = f.remote(image_data, "image.png")
                    yield PartialResponse(
                        text=textwrap.dedent(f"\n\n![plot]({image_url})")
                    )
                    vol.remove_file("image.png")

            if image_url:
                # wishlist - call an API that describes what is going on in the image
                current_user_simulated_reply += SIMULATED_USER_SUFFIX_IMAGE_FOUND
            else:
                if "matplotlib" in code:
                    current_user_simulated_reply += SIMULATED_USER_SUFFIX_IMAGE_NOT_FOUND

            current_user_simulated_reply += SIMULATED_USER_SUFFIX_PROMPT

            message = ProtocolMessage(role="bot", content=current_user_simulated_reply)
            request.query.append(message)

    async def get_settings(self, setting: SettingsRequest) -> SettingsResponse:
        return SettingsResponse(
            server_bot_dependencies={self.prompt_bot: 10},
            allow_attachments=True,
            introduction_message="",
        )


image_bot = (
    Image.debian_slim()
    .pip_install("fastapi-poe==0.0.23", "requests==2.28.2")
    .env({"POE_ACCESS_KEY": os.environ["POE_ACCESS_KEY"]})
)

image_exec = Image.debian_slim().pip_install(
    "fastapi-poe==0.0.23",
    "huggingface-hub==0.16.4",
    "ipython",
    "scipy",
    "matplotlib",
    "scikit-learn",
    "pandas==1.3.2",
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
    "yfinance",
    "dill",
    "seaborn",
)

stub = Stub("poe-bot-quickstart")

bot = PythonAgentBot()


@stub.function(image=image_bot)
@asgi_app()
def fastapi_app():
    app = make_app(bot, api_key=os.environ["POE_ACCESS_KEY"])
    return app
