#Scraper for FIA docs
#URL: https://www.fia.com/documents/championships/fia-formula-one-world-championship-14/season

url = "https://www.fia.com/documents/championships/fia-formula-one-world-championship-14/season"
import requests
from bs4 import BeautifulSoup
import selenium
from contextlib import closing

def get_fia_docs():
    response = requests.get(url)
    print(response.status_code)

    if response.status_code != 200:
        print(f"Failed to retrieve the page: {response.status_code}")
        return []
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    #print(soup)

    # Find all links to the documents
    links = soup.find_all('a', class_='event-title')
    #https://www.fia.com/system/files/decision-document/2025_spanish_grand_prix_-_p1_and_p2_scrutineering.pdf

    print(f"Found {len(links)} document links.")
    if not links:
        print("No document links found.")
        return []
    
    # Extract the href attribute from each link
    doc_links = [link['href'] for link in links if 'href' in link.attrs]
    
    return doc_links

get_fia_docs()
exit(0)