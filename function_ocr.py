"""

Helper function to OCR

modal deploy function_ocr.py
"""

import os
import sys
from io import StringIO

from modal import Image, Stub



image = (
    Image.debian_slim()
    .pip_install_from_requirements("requirements_function_ocr.txt")
)

stub = Stub("ocr-shared")


@stub.function(image=image, timeout=30)
def upload_file(data):
    with open("input.pdf", "wb") as f:
        f.write(data)

    subprocess.run("nougat input.pdf -o output.txt")

    with open("output.txt", "r") as f:
        output = f.read()

    return output
