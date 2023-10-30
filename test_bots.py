import asyncio
import os

from fastapi_poe.client import get_bot_response
from fastapi_poe.types import ProtocolMessage

BOTS_AND_TEST_MESSAGE = {}

BOTS_AND_TEST_MESSAGE["CatBotDemo"] = ProtocolMessage(
    role="user", content="Hello world"
)

BOTS_AND_TEST_MESSAGE["CmdLine"] = ProtocolMessage(role="user", content="pwd")

BOTS_AND_TEST_MESSAGE["EnglishDiffBot"] = ProtocolMessage(
    role="user", content="Please corect this massage."
)

# BOTS_AND_TEST_MESSAGE["LeetCodeAgent"] =  ProtocolMessage(
#     role="user", content="(insert question here"
# )

BOTS_AND_TEST_MESSAGE["LinkAwareBot"] = ProtocolMessage(
    role="user",
    content="What is the difference between https://arxiv.org/pdf/2201.11903.pdf and https://arxiv.org/pdf/2305.10601.pdf",
)

BOTS_AND_TEST_MESSAGE["matplotlib"] = ProtocolMessage(
    role="user", content="Plot USA map."
)

BOTS_AND_TEST_MESSAGE["MeguminWizardEx"] = ProtocolMessage(
    role="user", content="Count to 10."
)

# BOTS_AND_TEST_MESSAGE["nougatOCR"] =  ProtocolMessage(
#     role="user", content="(get one pdf paper)"
# )

BOTS_AND_TEST_MESSAGE["PromotedAnswer"] = ProtocolMessage(
    role="user", content="neverssl.com"
)

BOTS_AND_TEST_MESSAGE["PythonAgent"] = ProtocolMessage(
    role="user", content="Draw USA map."
)

# BOTS_AND_TEST_MESSAGE["TesseractOCR"] =  ProtocolMessage(
#     role="user", content="(get one pdf paper)"
# )

BOTS_AND_TEST_MESSAGE["tiktoken"] = ProtocolMessage(role="user", content="ChatGPT")


async def test_bot(bot_name, message):
    print(bot_name)
    print(message)
    async for partial in get_bot_response(
        messages=[message], bot_name=bot_name, api_key=os.environ["POE_API_KEY"]
    ):
        print(partial)


# currently do not work
for bot_name, message in BOTS_AND_TEST_MESSAGE.items():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_bot(bot_name, message))
    loop.close()
