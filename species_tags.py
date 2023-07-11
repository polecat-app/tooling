import os
from pathlib import Path
import psycopg2
from dotenv import load_dotenv
from supabase import create_client
import openai
import asyncio
from supabase import create_client, Client
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
    retry_if_exception_type, 
    retry_if_exception
)
import time
import json
import random

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

schema = {
        
    }


def get_species_details_from_supabase(conn, species_id):
    # create a new connection to supabase

    cur = conn.cursor()

    # Define your SQL query with placeholders
    query = """
    SELECT species_id, species_name.english as english_name, species_name.dutch as dutch_name, genus, species, species_description.english as description
    FROM species_description
    LEFT JOIN species USING(species_id)
    LEFT JOIN genus USING(genus_id)
    LEFT JOIN species_name USING(species_id)
    WHERE species_id = %s;
    """

    # Execute the query with the provided species_id
    cur.execute(query, (str(species_id),))

    # Fetch the results
    result = cur.fetchone()

    # Close the cursor and connection
    cur.close()

    # Return the species details
    return result

async def coroutine_for_getting_tags(conn, species:dict):
    
    latin_name = species['genus'] + ' ' +species['species']
    english_name = species['english_name']

    name_prompt = f"{english_name} ({latin_name})" if english_name else latin_name
    
    english_description = species['description']

    prompt = f'I am a {name_prompt}. Between the square brackets is some information about my life: [{english_description}].\
        Based on this information, return all 3 informational tags for my species (nocturnal, poisonous, migratory) as true or false.\
        Only answer true if you can conclude it from the description and you are very sure. Otherwise answer false. Also return the reason behind your answers for the tags (reasoning).'
    

    params = {
        'model': 'gpt-3.5-turbo-0613',
        'messages': [
            {"role": "system", "content": "You are an animal expert"},
            {"role": "user", "content": prompt}
        ],
        'temperature': 0.3,
        'max_tokens': 400,
        'presence_penalty': 0.1,
        'frequency_penalty': 0.1,
        'functions': [
            {
                'name': 'get_animal_tags', 
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'tags': {
                            'type': 'object',
                            'properties': {
                                'nocturnal': {
                                    'type': 'boolean',
                                    'description': 'is it nocturnal?'
                                },
                                'migratory': {
                                    'type': 'boolean',
                                    'description': 'is it migratory?'
                                },
                                'poisonous': {
                                    'type': 'boolean',
                                    'description': 'is it poisonous?'
                                },
                                'reasoning': {
                                    'type': 'string',
                                    'description': 'explain the reason for the true/false values of the tags poisonous, migratory, nocturnal'
                                }
                            }
                        }
                    }
                }
            }
        ],
        'function_call': {'name': 'get_animal_tags'}
    }

 
    try:
        response = await openai.ChatCompletion.acreate(**params)  
    except Exception as e:
        print(f"Unexpected error occurred: {e}")
        response = None

    try:
        animal_tags = json.loads(response['choices'][0]['message']['function_call']['arguments'])
    except (json.JSONDecodeError, KeyError):
        animal_tags = {"error": "Could not parse the animal tags."}
        
    return name_prompt, animal_tags

async def main(start_id, end_id, step_size):

    # Set up the OpenAI API client
    openai.api_key = api_key

    # set up connection to supabase
    conn_supabase = psycopg2.connect(
    dbname=os.getenv("DB"),
    user=os.getenv("USER"),
    password=os.getenv("PW"),
    host=os.getenv("HOST"),
    port=os.getenv("PORT"))

    # # find the species with missing tags
    # missing_ids = get_species_ids_with_missing_tags(conn_supabase, start_id, end_id)

    # if not missing_ids:
    #     print(f'all species have a dutch description for id {start_id} to {end_id}')
    #     return

    # missing_ids = [int(random.random() * 22000) for i in range(3)]

    nocturnal_dict = {'Aardvark': 15085, 'Bobcat': 14755, 'Red-Eyed Treefrog': 860}


    def chunks(ids: list, step_size: int):
        return [ids[i:i+step_size] for i in range(0, len(ids), step_size)]
    
    for chunk in chunks(list(nocturnal_dict.values()), step_size):
        tasks = []
        failed_tasks = []




        for species_id in chunk:
            record = get_species_details_from_supabase(conn_supabase, species_id)
            if not record:
                print(f'no species found with id: {species_id}, continuing')
                continue

            species = { 'species_id': record[0], 'english_name': record[1], 'dutch_name': record[2], 'genus': record[3], 'species': record[4], 'description': record[5]}
            
            print(f"making coroutine for id: {species_id}")
            
            tasks.append(
                coroutine_for_getting_tags(conn_supabase, species)
            )

        # Asynchronously run all coroutinesff
        results = await asyncio.gather(*tasks, return_exceptions=True)
        print(results)

    conn_supabase.close()
    
if __name__ == "__main__":
    asyncio.run(main(0, 30000, 100))