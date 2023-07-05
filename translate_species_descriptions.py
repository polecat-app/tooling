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
)
import time

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

def sequence_ids(start_id, end_id ,step_size):
    sequences = []
    
    for i in range(start_id, end_id, step_size):
        current_end_id = min(i + step_size, end_id)
        sequences.append((i, current_end_id))
    return sequences

#def check_dutch_descriptions(conn, start_id, end_id):



def species_dutch_description_exists(conn, species_id):
    cur = conn.cursor()

    # Define your SQL query with placeholders
    query = """
    SELECT dutch
    FROM species_description
    WHERE species_id = %s;
    """

    # Execute the query with the provided species_id
    cur.execute(query, (str(species_id),))

    # Fetch the results
    result = cur.fetchone()

    # Close the cursor and connection
    cur.close()

    try:
        text = result[0]
        if isinstance(text, str):
            return True
    except TypeError:
        return False

    return False
    



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


async def coroutine_for_translating_description(conn, species:dict):
    # Determine input prompt    
    dutch_description = None

    latin_name = species['genus'] + ' ' +species['species']
    english_description = species['description']
    dutch_name = species['dutch_name']
    english_name = species['english_name']

    common_name = dutch_name if dutch_name else latin_name
    species_id = species['species_id']

    prompt = f'Translate the following description to dutch: [{english_description}].'
       
    if dutch_name:
        prompt += f'Use {dutch_name} as the name of the animal'
        if english_name:
            prompt += f'as the translation for {english_name}. do not translate {english_name}.'
        else: 
            prompt += f'as the translation for {latin_name}.'
    else: 
        prompt += f'Use "{latin_name}" as the name of the animal in dutch.'
        if english_name: 
            prompt += f'Do not use {english_name} in the dutch description and also do not translate {english_name} to dutch.'
    
    prompt+= ' Convert imperial units to metric units.'

    params = {

        'model': 'gpt-3.5-turbo',
        'messages' : [
            {"role": "system", "content": f"You are an {common_name} talking about your life"},
            {"role": "user", "content": prompt}
        ],
        'temperature': 0.3,
        'max_tokens' : 400,
        'presence_penalty' : 0.1,
        'frequency_penalty' : 0.1
    }

    # # Asynchronously generate description
    # max_retries = 10
    # retry_delay = 2.0

    # for i in range(max_retries):
    #     try:
    #         response = await openai.ChatCompletion.acreate(**params)
    #         break  # exit the loop if the request succeeds
    #     except:
    #         await asyncio.sleep(retry_delay * (i+1))  # sleep for longer each time
    # else:
    #     response = None  # all retries failed
    #     print(f"no response from openai for id {species_id}: {common_name}")
    #     return

    @retry(wait=wait_random_exponential(min=10, max=60), stop=stop_after_attempt(10))
    def completion_with_backoff(**kwargs):
        return openai.ChatCompletion.acreate(**kwargs)
 
    response = await completion_with_backoff(**params)

    if response:
        dutch_description = response.choices[0].message.content
        print(f"generated description for id {species_id}: {common_name}")

        try:
            # Write to the database
            cur = conn.cursor()

            # Define your SQL query with placeholders
            query = """
            UPDATE species_description
            SET dutch = %s
            WHERE species_id = %s;
            """

            # Execute the query with the provided species_id and dutch_description
            cur.execute(query, (dutch_description, species_id))

            # Commit the changes to the database
            conn.commit()

            # Close the cursor
            cur.close()
            print("Wrote dutch translation into the database:", latin_name)
        except Exception as e: 
            print('An error occured writing to the database:', e)


async def main():

    # Set up the OpenAI API client
    openai.api_key = api_key

    # Define the range of species to translate descriptions for

    start_id = 4000
    end_id = 5000
    step_size = 100
    
    for start_sequence_id, end_sequence_id in sequence_ids(start_id, end_id, step_size):

        # set up connection to supabase
        conn_supabase = psycopg2.connect(
        dbname=os.getenv("DB"),
        user=os.getenv("USER"),
        password=os.getenv("PW"),
        host=os.getenv("HOST"),
        port=os.getenv("PORT"))

        tasks = []

        for species_id in range(start_sequence_id, end_sequence_id):
            if species_dutch_description_exists(conn_supabase, species_id):
                print(f'skipped id {species_id}, dutch description exists')
                continue
        
            record = get_species_details_from_supabase(conn_supabase, species_id)
            if not record:
                print(f'no species found with id: {species_id}, continuing')
                continue

            species = { 'species_id': record[0], 'english_name': record[1], 'dutch_name': record[2], 'genus': record[3], 'species': record[4], 'description': record[5]}
            
            print(f"making coroutine for id: {species_id}")
            
            tasks.append(
                coroutine_for_translating_description(conn_supabase, species)
            )

        # Asynchronously run all coroutinesff
        await asyncio.gather(*tasks)

        conn_supabase.close()

        time.sleep(5)
   
if __name__ == "__main__":
    asyncio.run(main())