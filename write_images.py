import os
from io import BytesIO

from supabase import create_client
from dotenv import load_dotenv
import requests
from PIL import Image


load_dotenv()


supabase_client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


def get_animal_image(animal_name):
    # perform a search on the Wikipedia API
    search_url = f"https://en.wikipedia.org/w/api.php?action=query&format=json&list=search&srsearch={animal_name}&srprop=size&srinfo=suggestion&srwhat=text"
    search_response = requests.get(search_url).json()

    # extract the page title of the first search result
    search_results = search_response['query']['search']
    if not search_results:
        print(f"No search results found for '{animal_name}'")
        return None
    page_title = search_results[0]['title']

    # retrieve the page information from the Wikipedia API
    page_url = f"https://en.wikipedia.org/w/api.php?action=query&format=json&prop=pageimages&titles={page_title}&pithumbsize=500"
    page_response = requests.get(page_url).json()

    # extract the image URL from the page information
    pages = page_response['query']['pages']
    page_id = next(iter(pages))
    if 'thumbnail' not in pages[page_id]:
        print(f"No image found for '{animal_name}'")
        return None, None
    image_url = pages[page_id]['thumbnail']['source']
    print(image_url)

    # download and crop the image
    response = requests.get(image_url)
    print(response)
    image = Image.open(BytesIO(response.content))
    image_width, image_height = image.size
    aspect_ratio = image_width / image_height
    target_aspect_ratio = 1
    if target_aspect_ratio < aspect_ratio:
        # crop the image horizontally
        crop_width = int(image_height * target_aspect_ratio)
        crop_height = image_height
        x0 = (image_width - crop_width) // 2
        y0 = 0
    else:
        # crop the image vertically
        crop_width = image_width
        crop_height = int(image_width / target_aspect_ratio)
        x0 = 0
        y0 = (image_height - crop_height) // 2
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


if __name__ == "__main__":
    species = supabase_client.from_("species_view").select("*").limit(10)
    result = species.execute()

    for record in result.data:

        # Get thumbnail and cover image
        animal_name = record.get("common_name") or record.get("genus") + " " + record.get("species")
        cover, thumbnail = get_animal_image(animal_name)
