import urllib
import PIL
from PIL import Image
from selenium import webdriver
from selenium.webdriver.common.by import By
import time
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# to prevent the following error we change the options of the web driver:
# ERROR:device_event_log_impl.cc(215)] [17:16:46.922] 
# USB: usb_device_handle_win.cc:1046 Failed to read descriptor from node connection: 
# A device attached to the system is not functioning. (0x1F)

#selenium 4 - updated way of getting the web driver
options = Options()
options.add_argument("start-maximized")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver.get("https://www.google.com")
options.add_experimental_option('excludeSwitches', ['enable-logging'])

def scrape_google_image(searchterm, max_links_to_fetch, sleep_between_interactions):

    # get the url + the driver to search
    google_url = "https://www.google.com/search?safe=off&site=&tbm=isch&source=hp&q={q}&oq={q}&gs_l=img".format(q = searchterm)
    driver.get(google_url)

    # surpass "accept all" in the "Before you continue to Google" page
    driver.find_element(By.XPATH,
     '//*[@id="yDmH0d"]/c-wiz/div/div/div/div[2]/div[1]/div[3]/div[1]/div[1]/form[2]/div/div/button').click()

    # on the google image page
    image_urls = []
    image_count = 0 
    results_start =0

    while image_count < max_links_to_fetch:
        # scroll to page end so that all images can be seen
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(sleep_between_interactions)

        # get all elements that are a thumbnail image
        thumbnail_results = driver.find_elements(By.CSS_SELECTOR, '.bRMDJf')
        number_results = len(thumbnail_results)
        print(f"Found: {number_results} search results. Extracting links from {number_results}:{number_results}")

        # click on the thumbnail images to be able to extract the urls
        for img in thumbnail_results[results_start:number_results]:
            try:
                img.click()
                time.sleep(sleep_between_interactions)
            except Exception:
                continue
            # Extract image urls from elements
            actual_images = driver.find_elements(By.CSS_SELECTOR, '.n3VNCb.KAlRDb')
            if not actual_images:
                continue
            actual_img = actual_images[0]
            if actual_img.get_attribute('src') and 'http' in actual_img.get_attribute('src'):
                image_urls.append(actual_img.get_attribute('src'))
                image_count = len(image_urls)
                if image_count >= max_links_to_fetch:
                    print(f"Found: {image_count} image links, done!")
                    time.sleep(sleep_between_interactions)
                    return(image_urls)
                else:
                    print("Found:", len(image_urls), "image links, looking for more ...")
                    time.sleep(sleep_between_interactions)
        # if there are not enough pictures on this page, 
        # go to the next by clicking the load more button
        try:
            driver.execute_script("document.querySelector('.mye4qd').click();")
            results_start = len(thumbnail_results)
        except Exception as e:
            print(e) 
    return(image_urls)

image_urls = scrape_google_image("polecat", 50, 1)

for i in range(len(image_urls)):
    image = PIL.Image.open(urllib.request.urlopen(image_urls[i]))
    image.save("data/images/polecat_" + str(i) + '.jpg')

