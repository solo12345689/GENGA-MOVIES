import moviebox_api
import os
import sys

path = os.path.dirname(moviebox_api.__file__)
with open("mb_path.txt", "w") as f:
    f.write(path)
print(f"Path: {path}")
