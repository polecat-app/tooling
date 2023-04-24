import asyncio
import aiohttp


async def send_request_to_wiki_api(number):  # Number is just to demonstrate it's async
    """Asynchronously send a request to the wiki API."""

    # Determine input prompt

    # Define get request parameters
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "prop": "extracts",
        "titles": "Python_(programming_language)",
        "exintro": "",
        "explaintext": "",
    }

    # Asynchronously send request, and return coroutine
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            result = await response.json()

            # Write result to db
            print(f"Result for {number}: {result}")
            return result


async def main():
    """Asynchronously run all coroutines."""

    # Create a list of coroutines
    tasks = [send_request_to_wiki_api(nr) for nr in range(10)]

    # Asynchronously run all coroutines
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
