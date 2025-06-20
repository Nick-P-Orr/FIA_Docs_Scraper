#Scraper for FIA docs

url = "https://www.fia.com/documents/championships/fia-formula-one-world-championship-14/season"
import requests
from bs4 import BeautifulSoup
import selenium
from contextlib import closing

def get_fia_docs():
    response = requests.get(url)
    print(response.status_code)

    if response.status_code != 200:
        with closing(Firefox()) as driver:
            driver.get(url)
            button = driver.find_element_by_id('event-title')
            button.click()
            element = WebDriverWait(driver, 10).until(
                EC.invisibility_of_element_located((By.ID, "deviceShowAllLink"))
            )
    # store it to string variable
            page_source = driver.page_source
    # wait for the page to load
        
        0=0
    return 0
        
    

get_fia_docs()
exit(0)