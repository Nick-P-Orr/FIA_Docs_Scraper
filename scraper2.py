#Scraper for FIA docs
#URL: https://www.fia.com/documents/championships/fia-formula-one-world-championship-14/season

url = "https://www.fia.com/documents/championships/fia-formula-one-world-championship-14/season"
import requests
from bs4 import BeautifulSoup as bs
from urllib.parse import urlparse

links = []
def get_fia_docs():
    response = requests.get(url)
    print(response.status_code)

    if response.status_code != 200:
        print(f"Failed to retrieve the page: {response.status_code}")
        return []
    
     
    resp = requests.get(url)
    soup = bs(resp.text,'lxml')
    og = soup.find("meta",  property="og:url")
    base = urlparse(url)
    for link in soup.find_all('a'):
        current_link = link.get('href')
        if current_link.endswith('pdf'):
            if og:
                links.append(og["content"] + current_link)
            else:
                links.append(base.scheme+"://"+base.netloc + current_link)
    
    

get_fia_docs()
exit(0)