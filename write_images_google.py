import os
from io import BytesIO

import aiohttp
import asyncio
import re

import requests
from PIL.Image import Image
from bs4 import BeautifulSoup
from lxml import html as lx_html


async def search_images(prompt):
    async with aiohttp.ClientSession() as session:
        print("sending search request", f"https://www.google.com/search?q={prompt}&tbm=isch&tbs=sur:fmc")
        async with session.get(f'https://www.google.com/search?q={prompt}&tbm=isch&tbs=sur:fmc') as response:
            html_text = await response.text()

    # Parse the HTML response to get the image URLs and dimensions using lxml
    tree = lx_html.fromstring(html_text)
    img_divs = tree.xpath('//div[@class="rg_i"]')
    if not img_divs:
        print("no image divs")
        return None
    img_div = img_divs[0]
    url = img_div.xpath('.//img/@src')[0]
    height = int(img_div.xpath('.//img/@height')[0])
    width = int(img_div.xpath('.//img/@width')[0])

    # Check if there are multiple images
    # and select the best one based on size and aspect ratio
    if 'id="isr_mc"' in html_text:
        print("sending image request", f"https://www.google.com/search?q={prompt}&tbm=isch&tbs=iar:s,tba:sur,fmc")
        async with session.get(f'https://www.google.com/search?q={prompt}&tbm=isch&tbs=iar:s,tba:sur,fmc') as response:
            html = await response.text()
        soup = BeautifulSoup(html, 'html.parser')
        img_divs = soup.find_all('div', {'class': 'rg_i'})
        if not img_divs:
            return None
        # Select the first image with a width > 300 pixels and a squarish aspect ratio
        for img_div in img_divs:
            url = img_div.find('img')['src']
            height = int(img_div.find('img')['height'])
            width = int(img_div.find('img')['width'])
            ratio = width / height
            if width > 300 and (1/1.2 <= ratio <= 1.2/1):

                download_images(prompt, url)
    else:
        # Return the first image if there is only one
        download_images(prompt, url)


def download_images(animal_name: str, image_url: str):
    """Download and crop the image."""

    # download and crop the image
    response = requests.get(image_url)
    print("response", response)
    image = Image.open(BytesIO(response.content))
    print("image", image)
    image_width, image_height = image.size
    aspect_ratio = image_width / image_height
    target_aspect_ratio = 1

    # crop the image horizontally
    if target_aspect_ratio < aspect_ratio:
        crop_width = int(image_height * target_aspect_ratio)
        crop_height = image_height
        x0 = (image_width - crop_width) // 2
        y0 = 0

    # crop the image vertically
    else:
        crop_width = image_width
        crop_height = int(image_width / target_aspect_ratio)
        x0 = 0
        y0 = (image_height - crop_height) // 2

    # crop the image
    image = image.crop((x0, y0, x0 + crop_width, y0 + crop_height))
    image_width, image_height = image.size
    cover = image.resize((min(1000, image_width), min(1000, image_height)))
    thumbnail = image.resize((min(150, image_width), min(150, image_height)))

    # save the cropped image
    file_path = os.path.join(os.getcwd() + "\\images\\", animal_name + "_cover.jpg")
    cover.save(file_path)
    file_path = os.path.join(os.getcwd() + "\\images\\", animal_name + "_thumbnail.jpg")
    thumbnail.save(file_path)

    return cover, thumbnail


async def main():
    animals = ['dog'] #, 'cat', 'bird', 'elephant']  # Replace with your list of animal names
    tasks = []
    for animal in animals:
        tasks.append(asyncio.create_task(search_images(animal)))
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    asyncio.run(main())
