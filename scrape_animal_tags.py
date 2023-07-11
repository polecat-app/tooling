from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import ElementNotInteractableException
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import pandas as pd
import time
import re

def scrape_animal_names(url):
    # Set up WebDriver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    driver.get(url)

    time.sleep(2)  # wait for the page to load

    # Handle cookie pop-up
    try:
        cookie_popup = driver.find_element(By.CSS_SELECTOR, 'body > div.stpd_cmp > div > div > div:nth-child(2) > div > button')
        cookie_popup.click()
    except NoSuchElementException:
        pass  # if there is no pop-up, continue the script

    animal_data = []

    while True:
        try:
            # Scroll to the bottom of the page
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.5)  # wait for the page to load

            # Find the next button
            next_button = driver.find_element(By.CSS_SELECTOR, 'body > div.f-page.container > div.f-page__content > div > div.animals-list-with-ads > div.animals.table > div.paginator > div.load-more-container > span')

            # If the next button is not clickable, break the loop
            if 'disabled' in next_button.get_attribute('class'):
                break

            # Scroll to the next button
            driver.execute_script("arguments[0].scrollIntoView();", next_button)
            time.sleep(0.5)  # small delay after scrolling
            print('Going to next page...')
            next_button.click()

            time.sleep(0.5)  # wait for the next page to load
        except ElementNotInteractableException: 
            print('at end of page..')
            break

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # Find the animal names and latin names
    animal_names = soup.select('div.animals-invert__item-content > h2')
    latin_names = soup.select('div.animals-invert__item-content > span')

    # Loop over the animals and append the name and latin name to animal_data
    for animal, latin in zip(animal_names, latin_names):
        animal_name = re.sub(r'^\s*([A-Za-z\s]+)\s*$', r'\1', animal.get_text())
        latin_name = re.sub(r'^\s*([A-Za-z\s]+)\s*$', r'\1', latin.get_text())
        animal_data.append((animal_name, latin_name))

    driver.quit()

    return animal_data

if __name__ == "__main__":
    tag_name = 'nocturnal'
    url = "http://animalia.bio/nocturnal"
    animal_data = scrape_animal_names(url)

    # Create a DataFrame from the animal datap
    df = pd.DataFrame(animal_data, columns=['Animal Name', 'Latin Name'])

    # Save the DataFrame as a Parquet file
    df.to_parquet(f'{tag_name}.parquet', index=False)

    print(f"Animal data for {df.shape[0]} {tag_name} animals saved as '{tag_name}.parquet'")
