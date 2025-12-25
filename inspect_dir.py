import moviebox_api
import sys

try:
    with open('dir_output.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(dir(moviebox_api)))
        f.write('\n\n--- Attributes of Homepage if exists ---\n')
        if hasattr(moviebox_api, 'Homepage'):
            f.write('Homepage found\n')
        else:
            f.write('Homepage NOT found\n')
except Exception as e:
    with open('dir_output.txt', 'w', encoding='utf-8') as f:
        f.write(f"Error: {e}")
