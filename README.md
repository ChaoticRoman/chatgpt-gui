# ChatGPT Python Clients

This repository contains Python command-line interface (CLI) and graphical user interface (GUI) clients
for OpenAI's ChatGPT. The clients are designed to be simple and easy to use, with no arguments required
to run the commands.

## Dependencies

The clients depend on the following Python packages:

- `openai`: This package is used to interact with the OpenAI API and send requests to the ChatGPT model.

## Installation

To install the dependencies, run the following command:

```bash
pip install openai
```

## Usage

### API key

Expects `.api_key` file in the repo directory with your OpenAI API key in there. Don't worry to contribute,
the filename is in `.gitignore` already.

### CLI Client

To use the CLI client, run the following command:

```bash
python cli.py
```

The CLI client will prompt you to enter your input. The response from ChatGPT will be printed in the console.

You can also enable multiline mode with the `-m` or `--multiline` option. In this mode, you can input multiple
lines and input "SEND" when you are done.

Quit with either `q`, `x`, `exit` or `quit` as the input.

### GUI Client

For now, GUI client is just a browser of past conversations with nice rendering.

## Contributing

Contributions are welcome! Please feel free to submit a pull request.

## Support

If you encounter any issues or have any questions, please open an issue on GitHub.
