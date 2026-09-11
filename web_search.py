#!/usr/bin/env python3
"""Web scraper using BeautifulSoup to fetch quick answers from the web."""
import requests
from bs4 import BeautifulSoup

def search_web(query):
    # We use DuckDuckGo's Lite version because the HTML is very clean and easy to scrape
    url = "https://lite.duckduckgo.com/lite/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    data = {"q": query}
    
    try:
        # Send the search query
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        
        # Parse the HTML with BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract the result snippets
        results = []
        for tr in soup.find_all('tr'):
            td = tr.find('td', class_='result-snippet')
            if td:
                results.append(td.text.strip())
                if len(results) >= 2:  # Limit to the top 2 results for brevity
                    break
        
        if results:
            return " ".join(results)
        return "I searched the web, but I couldn't find a clear answer."
        
    except requests.exceptions.RequestException as e:
        return f"I had trouble connecting to the internet. Error: {e}"
    except Exception as e:
        return f"An error occurred while parsing the web page. Error: {e}"

if __name__ == "__main__":
    # Test the script directly
    test_query = "What is the capital of Japan?"
    print(f"Searching for: {test_query}\n")
    print(search_web(test_query))
