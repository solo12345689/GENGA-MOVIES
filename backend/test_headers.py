
import sys
import os

# Add the current directory to sys.path so we can import api
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

output_file = "test_output.txt"

def log(msg):
    print(msg)
    with open(output_file, "a") as f:
        f.write(msg + "\n")

# Clear output file
with open(output_file, "w") as f:
    f.write("")

try:
    from api import get_source_headers
    
    def test_headers():
        test_url = "https://sunburst93.live/video.m3u8"
        log(f"Testing URL: {test_url}")
        
        headers_list = get_source_headers(test_url, source="hianime")
        
        log(f"Generated {len(headers_list)} header configurations.")
        
        found_megacloud = False
        for i, h in enumerate(headers_list):
            ref = h.get('Referer', 'None')
            origin = h.get('Origin', 'None')
            log(f"Config {i+1}: Referer={ref}, Origin={origin}")
            
            if ref == "https://megacloud.tv/" and origin == "https://megacloud.tv":
                found_megacloud = True

        if found_megacloud:
            log("\nSUCCESS: Found Megacloud.tv strategy for Sunburst domain.")
        else:
            log("\nFAILURE: Did not find Megacloud.tv strategy.")

    if __name__ == "__main__":
        test_headers()

except Exception as e:
    log(f"CRITICAL ERROR: {e}")
    import traceback
    with open(output_file, "a") as f:
        traceback.print_exc(file=f)
