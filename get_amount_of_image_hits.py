import asyncio
import os
import time
from random import random
import aiohttp
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()


supabase_client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


async def get_animal_image_url(species_id: int, animal_name: str, session, fill_null=False):
    """Asynchronously send a request for an animal image to the wiki commons API.
    Limits the results to only images with a creative commons license, and with
    squarish proportions."""

    # Search query for images with the animal name
    base_url = "https://commons.wikimedia.org/w/api.php"
    payload = {
        'action': 'query',
        'list': 'search',
        'srsearch': animal_name,
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
        total_hits = response_dict["query"]["searchinfo"]["totalhits"]
        print(animal_name, total_hits)
        supabase_client.table("species_popularity").upsert({
            "species_id": species_id,
            "score": total_hits,
        }).execute()


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
            animal_name = binomial
            species_id = record.get("species_id")
            print('\n', species_id, ": starting task for ", animal_name)
            task = asyncio.create_task(get_animal_image_url(species_id, animal_name, session, fill_null=True))
            tasks.append(task)

        await asyncio.gather(*tasks)


if __name__ == "__main__":
    start = time.time()
    start_range = 0
    end_range = 100
    step_size = 50
    for i in range(start_range, end_range, step_size):
        asyncio.run(main(i, i + step_size))
    print("TIME", start - time.time())