from scraper import make_driver, wait_for_page
from selenium.webdriver.common.by import By
import time


driver = make_driver()
try:
    driver.get('https://www.fia.com/documents/championships/fia-formula-one-world-championship-14/season')
    wait_for_page(driver)
    time.sleep(2)
    event_elements = driver.find_elements(By.CSS_SELECTOR, 'a.event-title, div.event-title')
    print('total events', len(event_elements))
    for i,e in enumerate(event_elements[:15]):
        text = e.text.strip()
        print('event', i, text, e.get_attribute('class'), e.get_attribute('href'))

    event_links = driver.find_elements(By.CSS_SELECTOR, 'a.event-title.use-ajax')
    print('ajax event links', len(event_links))
    for i, e in enumerate(event_links[:10]):
        print('ajax', i, e.text.strip(), e.get_attribute('href'))

    # click second (Chinese) event to load docs
    chinese = next((e for e in event_links if 'Chinese' in e.text), None)
    if chinese:
        print('click chinese')
        driver.execute_script('arguments[0].click();', chinese)
        time.sleep(3)
        # now find docs in this opened event section
        # event element is now maybe has following ul.document-type-wrapper
        wrapper = chinese.find_element(By.XPATH, 'following-sibling::ul[contains(@class, "document-type-wrapper")]')
        pdfs = wrapper.find_elements(By.CSS_SELECTOR, 'a[href$=".pdf"]')
        print('chinese pdf count', len(pdfs))
        for p in pdfs[:10]:
            print('pdf', p.get_attribute('href'), p.text)
    else:
        print('no chinese found')
finally:
    driver.quit()
