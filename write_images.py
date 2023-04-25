import asyncio
import os
from io import BytesIO
from typing import Tuple
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
    response = requests.get(image_url)
    image = Image.open(BytesIO(response.content))
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
    cover = image.resize((min(1000, image_width), min(1000, image_height)))
    thumbnail = image.resize((min(150, image_width), min(150, image_height)))

    # # save the cropped image
    # file_path = os.path.join(os.getcwd() + "\\images\\", animal_name + "_cover.jpg")
    # cover.save(file_path)
    # file_path = os.path.join(os.getcwd() + "\\images\\", animal_name + "_thumbnail.jpg")
    # thumbnail.save(file_path)

    return cover, thumbnail


def get_file_info(filename: str):
    """Get file infor for a given wiki image file. Returns url, license."""

    api_url = "https://commons.wikimedia.org/w/api.php"

    # Prepare the query parameters for the API request
    params = {
        "action": "query",
        "format": "json",
        "prop": "imageinfo",
        "titles": filename,
        "iiprop": "url|extmetadata"
    }

    response = requests.get(api_url, params=params)
    data = response.json()

    # Extract the relevant information from the JSON response
    page_id = list(data["query"]["pages"].keys())[0]
    image_info = data["query"]["pages"][page_id]["imageinfo"][0]

    original_url = image_info["url"]
    license = image_info["extmetadata"]["LicenseShortName"]["value"]

    return original_url, license


async def get_animal_image_url_async(animal_name):
    """Asynchronously send a request for an animal image to the wiki commons API.
    Limits the results to only images with a creative commons license, and with
    squarish proportions."""

    print(animal_name)


    #
    # base_url = "https://commons.wikimedia.org/w/api.php"
    # license = "&haslicense=attribution-same-license"
    # other = "&prop=imageinfo&iiprop=url|size&format=json&gsrlimit=10&iiurlwidth=500&iiurlheight=500&iiurlparam=thumb|square&redirects=1"
    #
    # url = f"{base_url}?action=query&generator=search&gsrsearch={animal_name}"
    # url = f"https://commons.wikimedia.org/w/api.php?action=query&iiprop=extmetadata&generator=images&prop=imageinfo&redirects=1&generator=search&gsrsearch={animal_name}&iiprop=timestamp|user|userid|comment|canonicaltitle|url|size|dimensions|sha1|mime|thumbmime|mediatype|bitdepth"
    # print(url)
    #

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
        'iiprop': 'timestamp|user|userid|comment|canonicaltitle|url|size|dimensions|sha1|mime|thumbmime|mediatype|bitdepth|extmetadata'
    }
    headers = {
        'Content-Type': 'application/json;charset=UTF-8'}
    params = urlencode(payload, quote_via=quote)
    response = requests.get(base_url, params=params, headers=headers)
    response_dict = response.json()

    # Get the first image with a CC license and squarish proportions
    img_url = None
    for img_result in response_dict["query"]["search"]:
        img_url, license = get_file_info(img_result["title"])
        if not "CC" in license and not "Public Domain" in license:
            continue
        print("url", img_url)
        break

    if not img_url:
        return None

    async with aiohttp.ClientSession() as session:
        async with session.get(img_url) as response:
            response = await response.json()
    print(response)
    for page_id, page_info in response["query"]["pages"].items():
        if "imageinfo" in page_info:
            image_info = page_info["imageinfo"][0]
            width = image_info["width"]
            height = image_info["height"]
            if (
                    1 <= width / height <= 1.2 or 1 <= height / width <= 1.2) and width >= 300:
                return image_info["url"]

    return None


async def main():
    """Main function."""
    species = supabase_client.from_("species_view").select("*").limit(5)
    result = species.execute()

    tasks = []
    for record in result.data:

        # Get thumbnail and cover image
        animal_name = record.get("common_name") or record.get("genus") + " " + record.get("species")
        tasks.append(get_animal_image_url_async(animal_name))
        # cover, thumbnail = get_animal_image(animal_name)

    return await asyncio.gather(*tasks)


if __name__ == "__main__":
    results = asyncio.run(main())
    print(results)