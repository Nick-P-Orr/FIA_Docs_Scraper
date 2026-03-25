from scraper import make_driver, wait_for_page, BASE_URL
from selenium.webdriver.common.by import By

driver = make_driver()
try:
    url = BASE_URL + '/decision-document-list/nojs/60296'
    driver.get(url)
    wait_for_page(driver)
    print('title', driver.title)
    links = driver.find_elements(By.TAG_NAME, 'a')
    print('total a', len(links))
    pdfs = []
    for a in links:
        href = a.get_attribute('href')
        txt = a.text.strip()
        if href and href.lower().endswith('.pdf'):
            pdfs.append((href, txt))
    print('pdfs', len(pdfs))
    for i, p in enumerate(pdfs[:20]):
        print(i, p)

    print('--- first container with pdf or document text ---')
    for selector in ['article', 'div', 'table', 'ul', 'li']:
        elems = driver.find_elements(By.CSS_SELECTOR, selector)
        for e in elems:
            outer = e.get_attribute('outerHTML')
            if 'pdf' in outer.lower() or 'document' in outer.lower():
                print('S', selector, outer[:500])
                raise SystemExit
finally:
    driver.quit()
