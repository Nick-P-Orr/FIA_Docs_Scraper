from scraper import make_driver, get_event_links, get_document_links

d = make_driver()
try:
    events = get_event_links(d)
    print('events found:', len(events))
    if events:
        e = events[0]
        print('first event:', e['title'], e['data_id'])
        docs = get_document_links(d, e)
        print('docs for first event:', len(docs))
        if docs:
            print('first doc url:', docs[0]['url'])
            print('first doc title:', docs[0]['title'])
finally:
    d.quit()
