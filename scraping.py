import requests
import pyodbc
from bs4 import BeautifulSoup
import urllib
import PIL
import numpy as np
import matplotlib.pyplot as plt
from selenium import webdriver


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

# as an example, scrape wikipedia page for polecat

webpage = "https://en.wikipedia.org/wiki/Polecat"
result = requests.get(webpage)

# if successful parse the download into a BeautifulSoup object
if result.status_code == 200:
    print("parsed!")
    soup = BeautifulSoup(result.content, "html.parser")

# find the class of the object that you want to find, in our case, it is an image
image_url = 'https:' + soup.find('img', {'class': 'thumbimage'})['src']
# show the image

image = PIL.Image.open(urllib.request.urlopen(image_url))
plt.imshow(image)
plt.show()

# scraping google images website interactively
# this is done using selenium and chrome. For this an install of chromedriver is needed.

# This is the path I use
# DRIVER_PATH = '.../Desktop/Scraping/chromedriver 2'
# Put the path for your ChromeDriver here
#DRIVER_PATH = "data\chromedriver.exe"
#wd = webdriver.Chrome(executable_path=DRIVER_PATH)

# see https://medium.com/geekculture/scraping-images-using-selenium-f35fab26b122
