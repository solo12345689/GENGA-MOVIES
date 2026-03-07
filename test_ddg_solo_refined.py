import httpx
from bs4 import BeautifulSoup

def test_ddg_refined(search_query):
    query_payload = f'"{search_query}" novel read online'
    print(f"Searching: {query_payload}")
    data = {"q": query_payload}
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0"}
    res = httpx.post("https://html.duckduckgo.com/html/", data=data, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")
    
    query_words = [w.lower() for w in search_query.split() if len(w) > 2]
    results = []
    
    for a in soup.find_all("a", class_="result__a", href=True):
        title = a.text.strip()
        title_lower = title.lower()
        
        # Validation logic
        if query_words and not any(w in title_lower for w in query_words):
            print(f"Filtered out: {title}")
            continue
            
        results.append({
            "title": title,
            "href": a["href"]
        })
    return results

if __name__ == "__main__":
    import json
    res = test_ddg_refined("Solo Leveling")
    print("\nRELEVANT RESULTS:")
    print(json.dumps(res, indent=2))
