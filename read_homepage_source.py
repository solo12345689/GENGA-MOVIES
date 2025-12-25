from moviebox_api import Homepage
import inspect
import sys

try:
    with open('homepage_source.txt', 'w', encoding='utf-8') as f:
        f.write(inspect.getsource(Homepage))
    print("Source written to homepage_source.txt")
except Exception as e:
    with open('homepage_source.txt', 'w', encoding='utf-8') as f:
        f.write(f"Error: {e}")
    print(f"Error: {e}")
