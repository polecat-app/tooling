import wikipedia
import wikipediaapi
import os
import openai
import tiktoken
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

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

def generate_chatgpt_description(animal_name, input_text, input_word_count, output_word_count):
    # Set up the OpenAI API client
    openai.api_key = api_key

    # use gpt 3.5 turbo, even though it is not made for completion but for chat, because it is 10% of the cost of a davinci model. 
    if input_word_count < output_word_count:
        output_word_count = input_word_count

    params = {
        'model': 'gpt-3.5-turbo',
        'messages' : [
                {"role": "system", "content": f"You are an {animal_name} talking about your life"},
                {"role": "user", "content": f'Act as if you are an {animal_name}. Write a description (max {output_word_count} words) of your life based on the following text:\n\n "{input_text}"\n.'}
            ],
        'temperature': 0.2,
        'max_tokens' : 250,
        'presence_penalty' : 1.0,
        'frequency_penalty' : 1.0
    }

    response = openai.ChatCompletion.create(**params)
    return response.choices[0].message.content

def get_record_from_supabase_species(from_species_id, to_species_id):

    # Set up a Supabase client instance
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_ANON_KEY')
    client = create_client(supabase_url, supabase_key)

    # Define the name of the view and the ID of the record to retrieve
    view_name = 'species_view'

    # Retrieve the record from the view
    response = client.from_(view_name).select('*').gte('species_id', from_species_id).lt('species_id', to_species_id).execute()
    
    return response


def main():
    species_records = get_record_from_supabase_species(1,5).data
    for dict in species_records:
        dict.update({'latin_name':  dict['genus'] + " " + dict['species']})
   
    #query = "Delichon urbica"
    #wiki_text, wordcount = get_descriptive_text_from_wiki(query, 500, 100)
    #chat_gpt_text = generate_chatgpt_description(query, wiki_text, wordcount, 100)
    #print(chat_gpt_text)


if __name__ == "__main__":
    main()


    