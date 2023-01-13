import requests
import pyodbc
from bs4 import BeautifulSoup
import urllib
import PIL
import numpy as np
import matplotlib.pyplot as plt
from selenium import webdriver
from selenium.webdriver.common.by import By
import os
import time
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
# driver.get("https://www.google.com")

# in this file 

# as an example, function to scrape image on wikipage for polecat

def scrape_wiki_polecat_image():
    webpage = "https://en.wikipedia.org/wiki/Polecat"
    result = requests.get(webpage)

    # if successful parse the download into a BeautifulSoup object
    if result.status_code == 200:
        print("parsed!")
        soup = BeautifulSoup(result.content, "html.parser")
    else:
        return "no wiki-page found"

    # find the class of the object that you want to find, in our case, it is an image
    image_url = 'https:' + soup.find('img', {'class': 'thumbimage'})['src']
    image = PIL.Image.open(urllib.request.urlopen(image_url))
    # make the directory to save the image to and save to that directory
    im_path = "data/images"
    if not os.path.exists(im_path):
        os.makedirs(im_path)
    image.save(im_path + "/polecat.jpg", "JPEG")
    return "image saved!"


# SCRAPING IMGAGES FROM GOOGLE IMAGES using selenium and chrome
# For this an install of chromedriver is needed.
# This is the path I use
# DRIVER_PATH = '.../Desktop/Scraping/chromedriver 2'
# Put the path for your ChromeDriver here


# DRIVER_PATH = "data\chromedriver.exe"
# wd = webdriver.Chrome(executable_path=DRIVER_PATH)

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


# options = webdriver.ChromeOptions()
# options.add_experimental_option('excludeSwitches', ['enable-logging'])
# driver = webdriver.Chrome(options=options)

sleep_between_interactions = 0.01
max_links_to_fetch = 5

def scroll_to_page_end(wd):
    wd.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(sleep_between_interactions)


def scroll_to_page_top(wd):
    wd.execute_script("window.scrollTo(0,0)")

def scrape_google_image(searchterm):
    google_url = "https://www.google.com/search?safe=off&site=&tbm=isch&source=hp&q={q}&oq={q}&gs_l=img".format(q = searchterm)
    driver.get(google_url)
    # click "accept all" in the "Before you continue to Google" page
    driver.find_element(By.XPATH, '//*[@id="yDmH0d"]/c-wiz/div/div/div/div[2]/div[1]/div[3]/div[1]/div[1]/form[2]/div/div/button').click()

    # on the google images page, 


    image_urls = set()
    image_count = 0 
    results_start = 0

    while image_count < max_links_to_fetch:
        scroll_to_page_end(driver)
        scroll_to_page_top(driver)

        thumbnail_results = driver.find_elements(By.CSS_SELECTOR, '.bRMDJf')
        number_results = len(thumbnail_results)

        print(f"Found: {number_results} search results. Extracting links from {results_start}:{number_results}")

        for img in thumbnail_results[results_start:number_results]:
            try:
                img.click()
                time.sleep(sleep_between_interactions)
            except Exception:
                continue
        
        # Extract image urls
        actual_images = driver.find_elements(By.CSS_SELECTOR, '.n3VNCb.KAlRDb')
        for actual_image in actual_images:
            if actual_image.get_attribute('src') and 'http' in actual_image.get_attribute('src'):
                image_urls.add(actual_image.get_attribute('src'))
                image_count = len(image_urls)
                if image_count >= max_links_to_fetch:
                    print(f"Found: {len(image_urls)} image links, done!")
                    break
                else:
                    time.sleep(30)
                    return

    load_more_button = driver.find_element_by_css_selector(".mye4qd")
    if load_more_button:
        driver.execute_script("document.querySelector('.mye4qd').click();")

        # move the result startpoint further down
        results_start = len(thumbnail_results)

    return image_urls


scrape_google_image("polecat")


# see https://medium.com/geekculture/scraping-images-using-selenium-f35fab26b122


# get a list of animals from the ecoregion database to find images for 
# connect to db
# set up some constants

# conn_string = 'Driver={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=data\WildfinderUpdate.mdb'

# # connect to db
# con = pyodbc.connect(conn_string)
# cur = con.cursor()

# # run a query and get the results 
# SQL = 'SELECT MSysObjects.Name AS table_name FROM MSysObjects;' 
# results = cur.execute(SQL).fetchall()

# print(results)

