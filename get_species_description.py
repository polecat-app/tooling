import asyncio
import re
import wikipedia
import wikipediaapi
import os
import openai
import tiktoken
from dotenv import load_dotenv
from supabase import create_client, Client
import aiohttp

load_dotenv()

# Environment variables
api_key = os.getenv("OPENAI_API_KEY")
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')

MAX_RETURN_WORD_COUNT = 100

import aiohttp

async def get_descriptive_text_from_wiki_async(animal_searchname, max_words=500, min_words = 100, language='en'):
    async with aiohttp.ClientSession() as session:
        # Search for the query
        search_url = f'https://{language}.wikipedia.org/w/api.php'
        search_params = {
            'action': 'query',
            'list': 'search',
            'format': 'json',
            'srsearch': animal_searchname
        }

        search_results = []

        async def connect_to_wiki(counter):
            try:
                async with session.get(search_url, params=search_params) as search_response:
                    search_results = await search_response.json()
                    search_results = search_results['query']['search']
                    return search_results
            except Exception as e:
                counter += 1
                print(f"Retrying to connect to wiki, error: {e}")
                if counter > 5:
                    return
                await asyncio.sleep(2)
                connect_to_wiki(counter)

        search_results = await connect_to_wiki(0)

        # async with session.get(search_url, params=search_params) as search_response:
        #     search_results = await search_response.json()
        #     search_results = search_results['query']['search']

        # Check if there are any results
        if not search_results:
            print(f"No results found for '{animal_searchname}' in '{language}' Wikipedia.")
            return None, None

        # Fetch the most likely page
        most_likely_page_title = search_results[0]['title']

        # Get the page content
        content_url = f'https://{language}.wikipedia.org/w/api.php'
        content_params = {
            'action': 'query',
            'prop': 'extracts',
            'format': 'json',
            'exsectionformat': 'wiki',
            'explaintext': 1,
            'titles': most_likely_page_title
        }
        async with session.get(content_url, params=content_params) as content_response:
            content_results = await content_response.json()
            page_id = list(content_results['query']['pages'].keys())[0]
            full_text = content_results['query']['pages'][page_id]['extract']

        # Extract summary and description sections
        # get a list of the different secitons
        sections = full_text.split('\n\n\n')
        section_dict = {}
        # split each section in a title and a body and add to the dict
        pattern = '==\s*(.*?)\s*=='
        section_dict['Summary'] = sections[0]
        exclude_titles = ['== External links ==', '== References ==']
        
        for section in sections[1:]: 
            match = re.search(pattern, section)
            if match:
                key = match.group(0)
                if key not in exclude_titles: 
                    content = section.split(key,1)
                    section_dict[key] = ''.join(content)
        
        
        description = ""
        # Combine summary and description
        for key, item in section_dict.items():
            if "description" in key.lower():
                description = item
                break
        
        gpt_input_text = section_dict['Summary'] + " " + description
        words = gpt_input_text.split()
        word_count = len(words)

        # if the summary + description are less than min_words, 
        # get all the other text and take max_words

        if word_count < min_words:
            gpt_input_text = " ".join(section_dict.values)
            words = gpt_input_text.split()
            word_count = len(words)
            result = " ".join(words[: min(word_count, max_words)])
            word_count = min(word_count, max_words)

        # Description and summary are good length
        elif word_count < max_words:
            result = " ".join(words)

        # Description and summary are too long
        else:
            result = " ".join(words[:max_words])
            word_count = max_words

        return result, word_count

def num_tokens_from_messages(messages, model="gpt-3.5-turbo-0301"):
  """Returns the number of tokens used by a list of messages."""
  try:
      encoding = tiktoken.encoding_for_model(model)
  except KeyError:
      encoding = tiktoken.get_encoding("cl100k_base")
  if model == "gpt-3.5-turbo-0301":  # note: future models may deviate from this
      num_tokens = 0
      for message in messages:
          num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
          for key, value in message.items():
              num_tokens += len(encoding.encode(value))
              if key == "name":  # if there's a name, the role is omitted
                  num_tokens += -1  # role is always required and always 1 token
      num_tokens += 2  # every reply is primed with <im_start>assistant
      return num_tokens
  else:
      raise NotImplementedError(f"""num_tokens_from_messages() is not presently implemented for model {model}.
  See https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted to tokens.""")


def get_supabase_species(client, species_id):
    """Get records from the species table in the supabase database."""

    species_view = 'species_view'

    # Retrieve the record from the view
    response = client.from_(species_view).select('*').eq('species_id', species_id).execute()
    return response

def species_description_exists(client, check_id):
    """Check is a species already has a description."""
   
    view_name = 'species_descriptions'

    # Retrieve the record from the view
    check = client.from_(view_name).select('species_id').eq('species_id', check_id).execute()
    return bool(check.data)

def check_missing_species_ids(client, start_id, end_id):
    """Check what species_id don't have a description yet."""
    result = client.rpc("__find_missing_species_descriptions", {'start_id': start_id, 'end_id': end_id }).execute()
    ids = [record['missing_id'] for record in result.data]
    success = len(ids) == 0
    return success, ids


async def coroutine_for_getting_and_writing_description(species: dict, client: Client):
    """Get the description for a species and write it to the database."""

    # Determine input prompt
    latin_name = species['genus'] + " " + species['species']

    common_name = species['common_name']
    if not bool(common_name):
        common_name = latin_name

    species_id = species['species_id']
    wiki_text, in_word_count = await get_descriptive_text_from_wiki_async(latin_name)
    
    description = None

    if wiki_text: 
        # Set up the OpenAI API client
        openai.api_key = api_key
        return_word_count = min(MAX_RETURN_WORD_COUNT, in_word_count)
        params = {
            'model': 'gpt-3.5-turbo',
            'messages' : [
                {"role": "system", "content": f"You are an {common_name} talking about your life"},
                {"role": "user", "content": f'Act as if you are an {common_name}. Write a description (max {return_word_count} words) of your life based on the following text:\n\n "{wiki_text}"\n.'}
            ],
            'temperature': 0.2,
            'max_tokens' : 250,
            'presence_penalty' : 1.0,
            'frequency_penalty' : 1.0
        }

        # Asynchronously generate description
        max_retries = 10
        retry_delay = 0.5

        for i in range(max_retries):
            try:
                response = await openai.ChatCompletion.acreate(**params)
                break  # exit the loop if the request succeeds
            except:
                await asyncio.sleep(retry_delay * (i+1))  # sleep for longer each time
        else:
            response = None  # all retries failed
            print(f"no response from openai for id {species_id}: {common_name}")
            return

        if response:
            description = response.choices[0].message.content
            print(f"generated description for id {species_id}: {common_name}")

    
    if not wiki_text: print(f"no wiki found for id  {species_id} : {common_name}")

    # Write to db
    record = {
        'description_id': species["species_id"],
        'species_id': species["species_id"],
        'description': description
    }
    data = client.table('species_descriptions').insert(record).execute()
    print("wrote into db: ", latin_name)


async def main():

    # Define the range of species to generate descriptions for
    #10000 to 100000
    start_id = 13004
    end_id = 13010
    step_size = 500

    def sequence_ids(start_id, end_id ,step_size):
        sequences = []
        
        for i in range(start_id, end_id, step_size):
            current_end_id = min(i + step_size, end_id)
            sequences.append((i, current_end_id))
        return sequences
    
    for start_sequence_id, end_sequence_id in sequence_ids(start_id, end_id, step_size):

        # Set up a Supabase client instance
        client = create_client(supabase_url, supabase_key)

        tasks = []

        for species_id in range(start_sequence_id, end_sequence_id):
            if species_description_exists(client, species_id):
                print(f'skipped id {species_id}, description exists')
                continue
        
            record = get_supabase_species(client, species_id).data
            if not record: 
                continue
            record = record[0]

            print(f"making coroutine for id: {species_id}")
            
            tasks.append(
                coroutine_for_getting_and_writing_description(record, client)
            )

        # Asynchronously run all coroutinesff
        await asyncio.gather(*tasks)

        check = True
        if check: 
            if check_missing_species_ids(client, start_id,end_id)[0]: 
                print(f'success! All descriptions between species id {start_id} and {end_id} are on the database!')
            else:
                print(f'Descriptions with species id {check_missing_species_ids(client, start_id,end_id)[1]} are not yet generated!')
            

if __name__ == "__main__":
    asyncio.run(main())
