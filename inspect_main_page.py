from scraper import make_driver, wait_for_page
from selenium.webdriver.common.by import By
import time

driver = make_driver()
try:
    from scraper import START_URL
    driver.get(START_URL)
    wait_for_page(driver)
    time.sleep(2)
    # print active event title and parent HTML
    active = driver.find_elements(By.CSS_SELECTOR, '.event-title.active')
    print('active count', len(active))
    for a in active:
        print('active text', a.text, 'outer', a.get_attribute('outerHTML'))
        p = a.find_element(By.XPATH, 'ancestor::div[1]')
        print('parent class', p.get_attribute('class'), 'outer', p.get_attribute('outerHTML')[:1000])

    # find event links anchor list
    events = driver.find_elements(By.CSS_SELECTOR, 'a.event-title')
    print('all event links', len(events))
    for e in events[:10]:
        print('event href', e.get_attribute('href'), 'text', e.text)

    # find any pdf links currently on main page
    pdf_links = driver.find_elements(By.CSS_SELECTOR, 'a[href$=".pdf"]')
    print('pdf links on main page', len(pdf_links))
    # for docs that are visible in container maybe with id
    # If there's a specific list in .document-rows etc
    for d in driver.find_elements(By.CSS_SELECTOR, '[class*="document"], [class*="item"], [id*="document"]')[:30]:
        print('maybe', d.get_attribute('class'), d.get_attribute('id'), d.get_attribute('outerHTML')[:300])

finally:
    driver.quit()
