import subprocess
import sys

def run_server():
    print("Starting uvicorn wrapper...")
    with open("uvicorn_debug.log", "w") as f:
        process = subprocess.Popen(
            ["uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8080", "--timeout-keep-alive", "65"],
            cwd="c:\\Users\\akshi\\.gemini\\antigravity\\scratch\\moviebox_web_app\\backend",
            stdout=f,
            stderr=subprocess.STDOUT,
            text=True
        )
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            print("Server is still running after 10 seconds (Success?)")
            return
    print(f"Process exited with code {process.returncode}")

if __name__ == "__main__":
    run_server()
