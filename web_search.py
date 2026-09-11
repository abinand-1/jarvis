#!/usr/bin/env python3
"""Web scraper using BeautifulSoup to fetch quick answers from the web."""
import requests
from bs4 import BeautifulSoup

def _scrape_ddg_lite(query):
    """Try DuckDuckGo's Lite HTML page. Returns a string of snippets, or
    None if nothing usable came back (so the caller can try a fallback)."""
    url = "https://lite.duckduckgo.com/lite/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    data = {"q": query}

    try:
        response = requests.post(url, headers=headers, data=data, timeout=8)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        results = []
        for tr in soup.find_all('tr'):
            td = tr.find('td', class_='result-snippet')
            if td:
                results.append(td.text.strip())
                if len(results) >= 2:  # Limit to the top 2 results for brevity
                    break

        if results:
            return " ".join(results)
        return None

    except requests.exceptions.RequestException:
        return None
    except Exception:
        return None


def _ddg_instant_answer(query):
    """Fallback: DuckDuckGo's Instant Answer JSON API. Covers factual/
    definitional queries that the Lite HTML scrape sometimes misses."""
    try:
        resp = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            timeout=8
        )
        resp.raise_for_status()
        data = resp.json()
        text = data.get("AbstractText") or data.get("Answer") or ""
        if text:
            return text.strip()
    except requests.exceptions.RequestException:
        pass
    except Exception:
        pass
    return None


def search_web(query):
    result = _scrape_ddg_lite(query)
    if result:
        return result

    result = _ddg_instant_answer(query)
    if result:
        return result

    return "I searched the web, but I couldn't find a clear answer."

if __name__ == "__main__":
    # Test the script directly
    test_query = "What is the capital of Japan?"
    print(f"Searching for: {test_query}\n")
    print(search_web(test_query))
