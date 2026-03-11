import os
import sys

# Ensure the root directory is at the beginning of sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# The IDE might show an error here, but it works at runtime on Vercel
from main import app  # type: ignore
