import moviebox_api.download as dl
import inspect

# Get source code of the module
src = inspect.getsource(dl)

with open("mb_download_source.py", "w", encoding="utf-8") as f:
    f.write(src)
