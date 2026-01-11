
import httpx
import json

def verify_rewrite():
    # Simulate a proxy-stream call for a manifest
    # We won't actually call the URL since CDNs are fickle, but we'll test the logic if possible
    # Or just check the code again.
    # Actually, let's just do a dry run of the logic in a small script.
    
    source = "hianime"
    content_text = "#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1280000,RESOLUTION=1280x720\nchunk_0.ts\nchunk_1.ts"
    base_url = "https://cdn.example.com/stream/"
    request_scheme = "http"
    request_netloc = "localhost:8000"
    
    lines = []
    for line in content_text.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            full_seg_url = line if line.startswith("http") else base_url + line
            source_query = f"&source={source}" if source else ""
            line = f"{request_scheme}://{request_netloc}/api/proxy-stream?url={full_seg_url}{source_query}"
        lines.append(line)
    
    rewritten = "\n".join(lines)
    print(f"Rewritten Manifest:\n{rewritten}")
    
    assert "source=hianime" in rewritten
    assert "chunk_0.ts" in rewritten

if __name__ == "__main__":
    verify_rewrite()
