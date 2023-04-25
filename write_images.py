import asyncio
import os
from io import BytesIO
from typing import Tuple
from urllib import request
from urllib.parse import urlencode, quote

import aiohttp
from bs4 import BeautifulSoup
from supabase import create_client
from dotenv import load_dotenv
import requests
from PIL import Image


load_dotenv()


supabase_client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


def adjust_image(image_url: str) -> Tuple[Image, Image]:
    """Adjust image at given url to specified sizes."""

    # download the image
    r = request.urlopen(image_url)
    image = Image.open(r)
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

    # Define large image and thumbnail
    image = image.crop((x0, y0, x0 + crop_width, y0 + crop_height))
    image_width, image_height = image.size
    cover = image.resize((min(800, image_width), min(800, image_height)))
    thumbnail = image.resize((min(150, image_width), min(150, image_height)))

    return cover, thumbnail


def get_file_info(filename: str) -> Tuple[str, str, int, int]:
    """Get file infor for a given wiki image file. Returns url, license."""

    api_url = "https://commons.wikimedia.org/w/api.php"

    # Prepare the query parameters for the API request
    params = {
        "action": "query",
        "format": "json",
        "prop": "imageinfo",
        "titles": filename,
        "iiprop": "url|extmetadata|dimensions"
    }

    response = requests.get(api_url, params=params)
    data = response.json()

    # Extract the relevant information from the JSON response
    page_id = list(data["query"]["pages"].keys())[0]
    image_info = data["query"]["pages"][page_id]["imageinfo"][0]

    original_url = image_info["url"]
    license = image_info["extmetadata"]["LicenseShortName"]["value"]
    width = image_info["width"]
    height = image_info["height"]

    return original_url, license, width, height


def get_animal_image_url(animal_name: str):
    """Asynchronously send a request for an animal image to the wiki commons API.
    Limits the results to only images with a creative commons license, and with
    squarish proportions."""

    # Search query for images with the animal name
    base_url = "https://commons.wikimedia.org/w/api.php"
    payload = {
        'action': 'query',
        'list': 'search',
        'srsearch': animal_name,
        'srlimit': '10',
        'prop': 'imageinfo',
        'srnamespace': '6',
        'format': 'json',
        # 'iiprop': 'timestamp|user|userid|comment|canonicaltitle|url|size|dimensions|sha1|mime|thumbmime|mediatype|bitdepth|extmetadata'
    }
    headers = {
        'Content-Type': 'application/json;charset=UTF-8'}
    params = urlencode(payload, quote_via=quote)
    response = requests.get(base_url, params=params, headers=headers)
    response_dict = response.json()

    # Get the first image with a CC license and squarish proportions
    img_url = None
    for img_result in response_dict["query"]["search"]:
        title = img_result["title"]
        if not title.startswith("File:") or not "jpg" in title:
            continue
        temp_url, license, width, height = get_file_info(title)
        if not "CC" in license and not "Public Domain" in license:
            continue
        img_url = temp_url
        print("url", img_url, license, width, height)
        break

    if not img_url:
        return None

    # Adjust the image to the desired sizes
    cover, thumbnail = adjust_image(img_url)

    # save the cropped image
    file_path = os.path.join(os.getcwd() + "\\images\\", animal_name + "_cover.jpg")
    cover.save(file_path)
    file_path = os.path.join(os.getcwd() + "\\images\\", animal_name + "_thumbnail.jpg")
    thumbnail.save(file_path)

    return img_url


def main():
    """Main function."""
    species = supabase_client.from_("species_view").select("*").limit(20)
    result = species.execute()

    tasks = []
    for record in result.data:

        # Get thumbnail and cover image
        binomial = record.get("genus") + " " + record.get("species")
        animal_name = record.get("common_name") or binomial
        url = get_animal_image_url(animal_name)
        print(url)


if __name__ == "__main__":
    main()