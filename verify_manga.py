import requests
import os

BASE_URL = "http://localhost:8000/api/manga"

def test_search():
    print("Testing Manga Search...")
    resp = requests.get(f"{BASE_URL}/search?query=naruto")
    if resp.status_code == 200:
        results = resp.json().get('results', [])
        print(f"  Success: Found {len(results)} results")
        return results[0]['id'] if results else None
    else:
        print(f"  Failed: {resp.status_code}")
        return None

def test_details(manga_id):
    if not manga_id: return None
    print(f"Testing Manga Details for ID: {manga_id}...")
    resp = requests.get(f"{BASE_URL}/details/{manga_id}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"  Success: Title: {data.get('title')}")
        # Get first chapter from first volume
        vols = data.get('volumes', {})
        if vols:
            first_vol = list(vols.keys())[0]
            if vols[first_vol]:
                return vols[first_vol][0]['id']
    else:
        print(f"  Failed: {resp.status_code}")
    return None

def test_pdf(chapter_id):
    if not chapter_id: return
    print(f"Testing Manga PDF for Chapter: {chapter_id}...")
    resp = requests.get(f"{BASE_URL}/pdf/{chapter_id}")
    if resp.status_code == 200:
        print(f"  Success: Received {len(resp.content)} bytes (PDF)")
    else:
        print(f"  Failed: {resp.status_code}")

def test_download(chapter_id):
    if not chapter_id: return
    print(f"Testing Manga Download for Chapter: {chapter_id}...")
    resp = requests.get(f"{BASE_URL}/download/{chapter_id}?title=test")
    if resp.status_code == 200:
        print(f"  Success: Received {len(resp.content)} bytes (ZIP)")
    else:
        print(f"  Failed: {resp.status_code}")

if __name__ == "__main__":
    m_id = test_search()
    if m_id:
        c_id = test_details(m_id)
        if c_id:
            test_pdf(c_id)
            test_download(c_id)
