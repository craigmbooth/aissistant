import os
import sys

import openai
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style

from .config import Config
from .exceptions import AIssistError
from .model import Model, OpenAIMessage
from .spinner import Spinner
from .version import __version__

try:
    openai.api_key = os.environ["OPENAI_API_KEY"]
except KeyError:
    print("Please put your API key in the OPENAI_API_KEY environment variable.")
    sys.exit(1)


def prompt_continuation(width: int, line_number: int, is_soft_wrap: int) -> str: #pylint: disable=W0613
    return "." * (width - 1) + " "


def print_streaming_message(
    model: Model, messages: list[OpenAIMessage], config: Config
) -> OpenAIMessage:
    """Prints a message that is being streamed from the API"""
    new_message_str = ""
    for printable_chunk in model.stream_call(messages, config):
        sys.stdout.write(printable_chunk)
        sys.stdout.flush()
        new_message_str += printable_chunk
    print("\n")
    new_message: OpenAIMessage = {"role": "assistant", "content": new_message_str}
    return new_message


def print_message(
    model: Model, messages: list[OpenAIMessage], config: Config
) -> OpenAIMessage:
    """Prints a message that is being returned from the API"""

    spinner = Spinner()
    spinner.start()

    new_message = model.call(messages, config)
    spinner.stop()
    print(" ")
    config.code_formatter.highlight_codeblocks(new_message["content"])
    print("\n")

    return new_message


def loop(config: Config, model: Model) -> None:
    """Main loop for the program"""

    # Move the fdollowing two lines into config, too
    style = Style.from_dict({"prompt": "#aaaaaa"})
    session: PromptSession = PromptSession(style=style)
    prompt = config.get_prompt()

    messages: list[OpenAIMessage] = [{"role": "system", "content": prompt}]

    while True:
        result = session.prompt(
            ">>> ", multiline=True, prompt_continuation=prompt_continuation
        )
        print()

        messages.append({"role": "user", "content": result})

        if config.parameters["no-stream"].value is True:
            new_message = print_message(model, messages, config)
        else:
            new_message = print_streaming_message(model, messages, config)

        messages.append(new_message)


def main() -> None:
    print(f"AIssist v.{__version__}. ESCAPE followed by ENTER to send. Ctrl-C to quit")
    print("\n")

    config = Config()
    model = Model(config.get("model"))

    try:
        while True:
            loop(config, model)
    except (KeyboardInterrupt, EOFError):
        # Ctrl-C and Ctrl-D
        sys.exit(0)
    except AIssistError as e:
        print(e)
        sys.exit(1)
    except Exception: #pylint: disable=W0706
        # If we didn't catch the error with one of the specific exceptions above,
        # print the stack trace and exit with a non-zero exit code.
        raise


if __name__ == "__main__":
    main()