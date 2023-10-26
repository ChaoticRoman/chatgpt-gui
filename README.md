# ChatGPT Python Clients

This repository contains Python command-line interface (CLI) and graphical user interface (GUI) clients
for OpenAI's ChatGPT. The clients are designed to be simple and easy to use, with no arguments required
to run the commands.

## Dependencies

The clients depend on the following Python packages:

- `openai`: This package is used to interact with the OpenAI API and send requests to the ChatGPT model.
- `tkhtmlview`: This package is used in the GUI client to display the chat history in a user-friendly format.

## Installation

To install the dependencies, run the following command:

```bash
pip install openai tkhtmlview
```

## Usage

### CLI Client

To use the CLI client, run the following command:

```bash
python cli.py
```

The CLI client will prompt you to enter your input. The response from ChatGPT will be printed in the console.

Quit with either `q`, `x`, `exit` or `quit` as the input.

### GUI Client

To use the GUI client, run the following command:

```bash
python gui.py
```

The GUI client will open a new window where you can enter your input and see the responses from ChatGPT.

## Contributing

Contributions are welcome! Please feel free to submit a pull request.

## Support

If you encounter any issues or have any questions, please open an issue on GitHub.
