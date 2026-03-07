import httpx
from bs4 import BeautifulSoup

def test_ddg(query):
    search_query = f"{query} novel read online"
    print(f"Searching: {search_query}")
    data = {"q": search_query}
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0"}
    res = httpx.post("https://html.duckduckgo.com/html/", data=data, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")
    results = []
    for a in soup.find_all("a", class_="result__a", href=True):
        results.append({
            "title": a.text.strip(),
            "href": a["href"]
        })
    return results

if __name__ == "__main__":
    import json
    res = test_ddg("Solo Leveling")
    print(json.dumps(res, indent=2))
