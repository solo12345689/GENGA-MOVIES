import os
import moviebox_api

path = os.path.dirname(moviebox_api.__file__)
print(f"Listing {path}:")
for root, dirs, files in os.walk(path):
    for file in files:
        print(os.path.join(root, file))
