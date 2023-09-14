"""

Helper function to execute Python code

modal deploy helper.py
"""

import os
import sys
import textwrap
from io import StringIO

from modal import Image, Stub

image = Image.debian_slim().pip_install_from_requirements("requirements_exec.txt")
stub = Stub("run-python-code-shared")


@stub.function(image=image, timeout=30)
def execute_code(code):
    import traitlets.config
    from IPython.terminal.embed import InteractiveShellEmbed

    config = traitlets.config.Config()
    config.InteractiveShell.colors = "NoColor"
    # config.PlainTextFormatter.max_width = 40  # not working
    # config.InteractiveShell.width = 40  # not working
    ipython = InteractiveShellEmbed(config=config)

    # Redirect stdout temporarily to capture the output of the code snippet
    old_stdout = sys.stdout
    sys.stdout = StringIO()

    # Execute the code with the silent parameter set to True
    _ = ipython.run_cell(code, silent=True, store_history=False, shell_futures=False)

    # Restore the original stdout and retrieve the captured output
    captured_output = sys.stdout.getvalue()
    sys.stdout = old_stdout

    return captured_output


@stub.function(image=image, timeout=30)
def execute_code_matplotlib(code):
    MATPLOTLIB_SHOW_OVERRIDE = textwrap.dedent(
        """\
    import matplotlib.pyplot as plt

    def save_image(filename):
        def decorator(func):
            def wrapper(*args, **kwargs):
                func(*args, **kwargs)
                plt.savefig(filename)
            return wrapper
        return decorator

    plt.show = save_image('image.png')(plt.show)
    """
    )

    code = MATPLOTLIB_SHOW_OVERRIDE + code

    import traitlets.config
    from IPython.terminal.embed import InteractiveShellEmbed

    config = traitlets.config.Config()
    config.InteractiveShell.colors = "NoColor"
    # config.PlainTextFormatter.max_width = 40  # not working
    # config.InteractiveShell.width = 40  # not working
    ipython = InteractiveShellEmbed(config=config)

    # Redirect stdout temporarily to capture the output of the code snippet
    old_stdout = sys.stdout
    sys.stdout = StringIO()

    # Execute the code with the silent parameter set to True
    _ = ipython.run_cell(code, silent=True, store_history=False, shell_futures=False)

    # Restore the original stdout and retrieve the captured output
    captured_output = sys.stdout.getvalue()
    sys.stdout = old_stdout

    image_data = None
    filename = "image.png"
    if os.path.isfile(filename):
        with open(filename, "rb") as f:
            image_data = f.read()
        os.remove(filename)

    return captured_output, image_data
