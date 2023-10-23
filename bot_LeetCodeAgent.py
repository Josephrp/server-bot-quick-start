"""

modal deploy --name LeetCodeAgent bot_LeetCodeAgent.py
curl -X POST https://api.poe.com/bot/fetch_settings/LeetCodeAgent/$POE_API_KEY

Test message:
copy some leetcode question

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
from fastapi_poe.types import PartialResponse, QueryRequest, SettingsResponse, ProtocolMessage
from modal import Image, Stub, asgi_app


def extract_code(reply):
    pattern = r"```python([\s\S]*?)```"
    matches = re.findall(pattern, reply)
    return "\n\n".join(matches)


def wrap_session(code, conversation_id):
    code = "\n".join(" "*12 + line for line in code.split("\n"))

    # there might be issues with multiline string
    # maybe exec resolves this issue
    return textwrap.dedent(
        f"""\
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
        try:
            {code}
        except Exception as e:
            with open('{conversation_id}.dill', 'wb') as f:
                dill.dump_session(f)
            raise e
        with open('{conversation_id}.dill', 'wb') as f:
            dill.dump_session(f)
        """
    )


class EchoBot(PoeBot):
    async def get_response(
        self, request: QueryRequest
    ) -> AsyncIterable[PartialResponse]:
        last_message = request.query[-1].content
        request.logit_bias = {"21362": -10}  # censor "![", but does this work?

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
                query.content += f"\n\nThe user has provided {attachment.name} in the current directory."

        for code_iteration_count in range(10):
            print("code_iteration_count", code_iteration_count)
            current_message = ""
                    
            async for msg in stream_request(request, "LeetCodeAgentTool", request.api_key):
                # Note: See https://poe.com/CheckPythonTool for the prompt
                if isinstance(msg, MetaMessage):
                    continue
                elif msg.is_suggested_reply:
                    yield self.suggested_reply_event(msg.text)
                elif msg.is_replace_response:
                    yield self.replace_response_event(msg.text)
                else:
                    current_message += msg.text
                    yield self.text_event(msg.text)
                    if extract_code(current_message):
                        break

            code = extract_code(current_message)
            if not code:
                return
            code = wrap_session(code, conversation_id=request.conversation_id)

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

            print("len(output)", len(output))
            print("len(error)", len(error))

            nothing_returned = True

            message = ProtocolMessage(role="bot", content=current_message)
            request.query.append(message)

            user_automated_message = ""

            if output:
                output_string = f"""\n\nThis is the output of the code. \n\n```output\n{output}\n```\n\n"""
                yield PartialResponse(text=output_string)
                user_automated_message += output_string
                nothing_returned = False
            if error:
                error_string = f"""\n\nThis is the error logs while executing the code. \n\n```error\n{error}\n```\n\n"""
                yield PartialResponse(text=error_string)
                user_automated_message += error_string + "\n\nPlease fix the error.\n\n"
                nothing_returned = False

            user_automated_message += textwrap.dedent("""
                Please check if your code passes the test cases.
                If the output is correct, report success.
                If the solution is wrong, detail a plan to fix the solution.
                You can use print statements to debug.
            """)
            
            message = ProtocolMessage(role="bot", content=user_automated_message)
            request.query.append(message)


    async def get_settings(self, setting: SettingsRequest) -> SettingsResponse:
        return SettingsResponse(
            server_bot_dependencies={"LeetCodeAgentTool": 10},
            allow_attachments=True,  # to update when ready
        )


# specific to hosting with modal.com
image = Image.debian_slim().pip_install_from_requirements("requirements_PythonAgentEx.txt").env(
    {
        "POE_API_KEY": os.environ["POE_API_KEY"],
    }
)
image_exec = Image.debian_slim().pip_install(
    "fastapi-poe==0.0.23",
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
