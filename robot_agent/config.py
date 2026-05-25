import os
from pathlib import Path

# Cache location
current_working_directory = Path(os.getcwd())

SYSTEM_PROMPT_PATH = os.path.join(
    current_working_directory, "resource","1011.md"
)
SYSTEM_PROMPT_VL_PATH = os.path.join(
    current_working_directory, "resource", "1.md"
)

IMAGE_DIR = os.path.join(current_working_directory, "uploads", "images")
