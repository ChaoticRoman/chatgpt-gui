import os
from pathlib import Path

DEFAULT_MODEL = "gpt-5.5"

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".gif")
USER_DATA_EXTENSIONS = (
    ".csv",
    ".doc",
    ".docx",
    ".html",
    ".json",
    ".md",
    ".odt",
    ".pdf",
    ".ppt",
    ".pptx",
    ".rtf",
    ".txt",
    ".xls",
    ".xlsx",
    ".xml",
)

DATA_DIRECTORY = Path(
    os.environ.get("CHATGPT_GUI_DATA_DIR", Path.home() / ".chatgpt-gui")
).expanduser()
