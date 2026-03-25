from scraper import make_driver, wait_for_page
from selenium.webdriver.common.by import By
import time


driver = make_driver()
try:
    driver.get('https://www.fia.com/documents/championships/fia-formula-one-world-championship-14/season')
    wait_for_page(driver)
    time.sleep(2)
    # print first 5 event wrappers
    items = driver.find_elements(By.CSS_SELECTOR, 'li')
    count = 0
    for item in items:
        title_elem = item.find_elements(By.CSS_SELECTOR, 'div.event-title, a.event-title')
        wrapper = item.find_elements(By.CSS_SELECTOR, 'ul.document-type-wrapper')
        if title_elem:
            title = title_elem[0].text.strip()
            href = title_elem[0].get_attribute('href')
            cls = title_elem[0].get_attribute('class')
            style = wrapper[0].get_attribute('style') if wrapper else None
            print('item', count, title, href, cls, style, 'wrapper length', len(wrapper))
            count += 1
            if count>=10:
                break
    # click Chinese
    chinese = driver.find_element(By.XPATH, "//a[contains(@class,'event-title') and contains(normalize-space(.),'Chinese')]")
    driver.execute_script('arguments[0].click();', chinese)
    time.sleep(3)
    wrapper = driver.find_element(By.CSS_SELECTOR, 'ul.document-type-wrapper.data-id-60296')
    print('after click style', wrapper.get_attribute('style'), 'children', len(wrapper.find_elements(By.CSS_SELECTOR, 'a[href$=".pdf"]')))
    for a in wrapper.find_elements(By.CSS_SELECTOR, 'a[href$=".pdf"]'):
        print('pdf', a.get_attribute('href'), a.text.strip())
finally:
    driver.quit()
