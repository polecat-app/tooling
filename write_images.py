import asyncio
import os
import time
from io import BytesIO
from random import random
from typing import Tuple, Optional

import aiohttp
from PIL import Image
from PIL import ImageFile
from dotenv import load_dotenv
from storage3.utils import StorageException
from supabase import create_client

ImageFile.LOAD_TRUNCATED_IMAGES = True


load_dotenv()


supabase_client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


async def adjust_image(image_url: str, session) -> Image.Image:
    """Adjust image at given url to specified sizes."""

    # download the image
    headers = {"User-Agent": "Thumbnail collection animal app; yannmcken@gmail.com"}
    async with session.get(image_url, headers=headers) as response:
        data = await response.read()
        image = Image.open(BytesIO(data))
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
    # cover = image.resize((min(800, image_width), min(800, image_height)))
    thumbnail = image.resize((min(150, image_width), min(150, image_height)))

    return thumbnail


async def get_file_info(filename: str, session) -> Optional[Tuple[str, str, int, int]]:
    """Get file info for a given wiki image file. Returns url, license."""

    api_url = "https://commons.wikimedia.org/w/api.php"

    # Prepare the query parameters for the API request
    params = {
        "action": "query",
        "format": "json",
        "prop": "imageinfo",
        "titles": filename,
        "iiprop": "url|extmetadata|dimensions"
    }

    async with session.get(api_url, params=params) as response:
        data = await response.json()

    # Extract the relevant information from the JSON response
    page_id = list(data["query"]["pages"].keys())[0]
    image_info = data["query"]["pages"][page_id]["imageinfo"][0]

    try:
        original_url = image_info["url"]
        license = image_info["extmetadata"]["LicenseShortName"]["value"]
        width = image_info["width"]
        height = image_info["height"]
    except KeyError:
        return None

    return original_url, license, width, height


async def get_animal_image_url(species_id: int, animal_name: str, session, fill_null=False):
    """Asynchronously send a request for an animal image to the wiki commons API.
    Limits the results to only images with a creative commons license, and with
    squarish proportions."""

    # Check if image url not already in db
    existing_url = supabase_client.table("species_images").select("*").eq("species_id", species_id).execute()
    record = existing_url.data[0] if existing_url.data else None
    if record:
        if fill_null and None in [record.get("thumbnail_name"), record.get("cover_url")]:
            print(f"{species_id}: Try to fill record with null values")
        else:
            print(f"{species_id}: Record already exists")
            return None

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
    }
    headers = {
        'Content-Type': 'application/json;charset=UTF-8',
    }

    # Send the request
    async with session.get(base_url, params=payload, headers=headers) as response:
        await asyncio.sleep(random())
        response_dict = await response.json()

    # Get first image that conforms to the requirements
    img_url = None
    for i, img_result in enumerate(response_dict["query"]["search"]):

        # Check if image is a jpg
        title = img_result["title"]
        if not title.startswith("File:") or not "jpg" in title:
            continue

        # Get image info
        print(f"{species_id}: Sending requests for file info")
        file_info = await get_file_info(title, session)
        if not file_info:
            continue
        temp_url, license, width, height = file_info
        print(f"{species_id}: Got requests for file info:")

        # Check if image has a CC license and squarish proportions
        if not "CC" in license and not "Public Domain" in license:
            continue
        if abs(width - height) > width * 0.4:
            continue

        # If so, save the image url and break the loop
        img_url = temp_url
        print(f"{species_id}: found url:", img_url, license, width, height)
        break

    # If no image found, save nulls on new record
    if not img_url:
        supabase_client.table("species_images").upsert({
            "species_id": species_id,
            "cover_url": None,
            "thumbnail_name": None,
        }).execute()
        print(f"{species_id}: No url found, empty record added")
        return None

    # Adjust the image to the desired sizes
    thumbnail = await adjust_image(img_url, session)

    # Upload the image file
    bytestream = BytesIO()
    thumbnail.save(bytestream, format='JPEG')
    bucket = supabase_client.storage.from_("animal-images")
    try:
        image_path = f"/thumbnail/{animal_name}.jpg"
        file_type = "image/jpeg"
        response = bucket.upload(image_path, bytestream.getvalue(),
                                 {"content-type": file_type})
        print(f"{species_id}: Image uploaded")
        supabase_client.table("species_images").upsert({
            "species_id": species_id,
            "cover_url": img_url,
            "thumbnail_name": image_path,
        }).execute()
        print(f"{species_id}: Record added")
        return img_url
    except StorageException:
        print(f"{species_id}: Image already exists")
    finally:
        bytestream.close()
        return


async def main(range_start: int, range_end: int):
    """Main function."""

    tasks = []
    async with aiohttp.ClientSession() as session:
        for i in range(range_start, range_end):
            species = supabase_client.from_("species_view").select(
                "species_id",
                "common_name",
                "genus",
                "species"
            ).eq("species_id", i)
            result = species.execute()
            if not result.data:
                continue

            # Get thumbnail and cover image
            record = result.data[0]
            binomial = (record.get("genus") or "") + " " + (record.get("species") or "")
            animal_name = record.get("common_name") or binomial
            species_id = record.get("species_id")
            print('\n', species_id, ": starting task for ", animal_name)
            task = asyncio.create_task(get_animal_image_url(species_id, animal_name, session, fill_null=True))
            tasks.append(task)

        await asyncio.gather(*tasks)


if __name__ == "__main__":
    start = time.time()
    start_range = 90000
    end_range = 95800
    step_size = 50
    for i in range(start_range, end_range, step_size):
        asyncio.run(main(i, i + step_size))
    print("TIME", start - time.time())
