import asyncio

import wikipedia
import wikipediaapi
import os
import openai
import tiktoken
from dotenv import load_dotenv
from supabase import create_client, Client


load_dotenv()

# Environment variables
api_key = os.getenv("OPENAI_API_KEY")
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')

MAX_RETURN_WORD_COUNT = 100


def get_descriptive_text_from_wiki(animal_searchname, max_words, min_words, language='en' ):
    # Set the language for the wikipedia library
    wikipedia.set_lang(language)

    # Search for the query
    search_results = wikipedia.search(animal_searchname)

    # Check if there are any results
    if not search_results:
        print(f"No results found for '{animal_searchname}' in '{language}' Wikipedia.")
        return None

    # Fetch the most likely page using wikipediaapi
    wiki = wikipediaapi.Wikipedia(language)
    most_likely_page_title = search_results[0]
    page = wiki.page(most_likely_page_title)

    # Check if the page exists
    if not page.exists():
        print(f"The page '{most_likely_page_title}' does not exist in '{language}' Wikipedia.")
        return None

    # Extract the text from the page
    summary = page.summary
    total_text = summary
   
    # Check if there is a 'description' header in the page
    sections = page.sections
    for section in sections:
        if section.title.lower() == 'description':
            description_text = section.text
            total_text += '\n' + description_text
            break
    
    words = total_text.split()
    word_count = len(words)

    if word_count < min_words:
        total_text = page.text.replace('\n', ' ').split('== References ==')[0].strip()
        words = total_text.split()
        word_count = len(words)

    # Limit the text to x words
    if word_count > max_words:
        total_text = ' '.join(words[:max_words]) + '...'

    return total_text, word_count


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


def get_records_from_supabase_species(client, from_species_id, to_species_id):
    """Get records from the species table in the supabase database."""

    # Define the name of the view and the ID of the record to retrieve
    view_name = 'species_view'

    # Retrieve the record from the view
    response = client.from_(view_name).select('*').gte('species_id', from_species_id).lt('species_id', to_species_id).execute()
    
    return response


async def coroutine_for_getting_and_writing_description(species: dict, client: Client):
    """Get the description for a species and write it to the database."""

    # Determine input prompt
    latin_name = species['genus'] + " " + species['species']
    wiki_text, in_word_count = get_descriptive_text_from_wiki(latin_name, 500, 100)

    # Set up the OpenAI API client
    openai.api_key = api_key
    return_word_count = min(MAX_RETURN_WORD_COUNT, in_word_count)
    params = {
        'model': 'gpt-3.5-turbo',
        'messages' : [
            {"role": "system", "content": f"You are an {latin_name} talking about your life"},
            {"role": "user", "content": f'Act as if you are an {latin_name}. Write a description (max {return_word_count} words) of your life based on the following text:\n\n "{wiki_text}"\n.'}
        ],
        'temperature': 0.2,
        'max_tokens' : 250,
        'presence_penalty' : 1.0,
        'frequency_penalty' : 1.0
    }

    # Asynchronously generate description
    response = await openai.ChatCompletion.acreate(**params)
    description = response.choices[0].message.content
    print("generated description for: ", latin_name)

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
    start_id = 3
    end_id = 20
    
    # Set up a Supabase client instance
    client = create_client(supabase_url, supabase_key)

    species_records = get_records_from_supabase_species(client, start_id, end_id).data

    # Define the tasks to run asynchronously
    tasks = []
    for species in species_records:
        tasks.append(
            coroutine_for_getting_and_writing_description(species, client)
        )

    # Asynchronously run all coroutines
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
