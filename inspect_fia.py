from scraper import make_driver, wait_for_page, START_URL
from selenium.webdriver.common.by import By

driver = make_driver()
try:
    driver.get(START_URL)
    wait_for_page(driver)
    anchors = driver.find_elements(By.TAG_NAME, 'a')
    print('a count', len(anchors))
    found=[]
    for a in anchors:
        href=a.get_attribute('href')
        text=a.text.strip()
        if href and '/documents/' in href and href!=START_URL:
            found.append((href, text))
    print('found /documents/', len(found))
    for i,e in enumerate(found[:20]):
        print(i,e)
    print('--- prefix START_URL links ---')
    for i,a in enumerate(anchors[:300]):
        href=a.get_attribute('href')
        if href and href.startswith(START_URL) and href!=START_URL:
            print('S',i,href,a.text.strip())
    print('--- event cards ---')
    rows = driver.find_elements(By.CSS_SELECTOR, '.views-row, .event-card, .event-title, .season-document-event')
    print('rows', len(rows))
    for i,r in enumerate(rows[:20]):
        print('ROW',i,r.get_attribute('outerHTML')[:500])
finally:
    driver.quit()
