import requests
import os
import io
from PIL import Image
from selenium import webdriver
from selenium.webdriver.common.by import By
import time
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

def get_driver():
    #selenium 4 - updated way of getting the web driver
    # to prevent the following error we change the options of the web driver:
    # ERROR:device_event_log_impl.cc(215)] [17:16:46.922] 
    # USB: usb_device_handle_win.cc:1046 Failed to read descriptor from node connection: 
    # A device attached to the system is not functioning. (0x1F)

    options = Options()
    options.add_argument("start-maximized")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get("https://www.google.com")
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    return driver

def get_image_urls(searchterm:str, driver, max_links_to_fetch:int, sleep_between_interactions:float):
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

def save_image(folder_path:str, name:str, url:str, counter):
    # open the url
    try:
        response = requests.get(url)
    except Exception as e:
        print(f"could not download {url} - {e}")
        return
    # save the image
    try:
        im = Image.open(io.BytesIO(response.content))
        im.save(folder_path + "/" + name + "_" + str(counter) +'.jpg')
        print(f"succes! saved image {url} as {folder_path}")
    except Exception as e:
        print(f"could not save {url} - {e}")


def scrape_images_from_google(search_term: str, target_path = './images', number_images = 10):  
    # search term
    search_term_underscores = search_term.replace(" ", "_")
    # make folder by search term name
    target_folder = target_path + "/" + search_term_underscores
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)
    
    # open driver and scrape the URLS
    with get_driver() as driver:
        res = get_image_urls(search_term, driver, number_images, 1.0)
    
    # save images in the target folder with increasing index
    count = 0 
    for url in res:
        save_image(target_folder, search_term_underscores, url, count)
        count += 1 
    
scrape_images_from_google("polecat") # inputs for target path and number of images are optional


