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

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

def get_species_ids_with_missing_dutch_description(conn, start_id: int, end_id: int):
    cur = conn.cursor()

    # Define your SQL query with placeholders
    query = """
    SELECT species_id
    FROM species_description
    INNER JOIN species USING(species_id)
    WHERE species_id BETWEEN %s AND %s AND (dutch IS NULL OR dutch = '');
    """

    # Execute the query with the provided start_id and end_id
    cur.execute(query, (start_id, end_id))

    # Fetch the results
    results = cur.fetchall()

    # Close the cursor
    cur.close()

    # Extract the species_ids from the results
    missing_ids = [result[0] for result in results]

    # # If the missing_ids list is empty, print a success message
    # if not missing_ids:
    #     print("Success! All species_ids have a Dutch description.")
    # # Otherwise, print the species_ids that are missing dutch descriptions
    # else:
    #     print(f"The following species_ids are missing a Dutch description: {missing_ids}")

    # Return the list of species_ids that are missing dutch descriptions
    return missing_ids



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
 
    try:
        response = await openai.ChatCompletion.acreate(**params)  
    except Exception as e:
        print(f"Unexpected error occurred: {e}")
        response = None

    if response:
        dutch_description = response.choices[0].message.content

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
            print(f"Wrote dutch translation into the database for id: {species_id}")
        except Exception as e:
            print(f'An error occured writing to the database for species id: {species_id}', e)
        return True
    else: return False


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

    # find the species_ids for which we should still generate a dutch description
    missing_ids = get_species_ids_with_missing_dutch_description(conn_supabase, start_id, end_id)

    if not missing_ids:
        print(f'all species have a dutch description for id {start_id} to {end_id}')
        return
        
    def chunks(ids: list, step_size: int):
        return [ids[i:i+step_size] for i in range(0, len(ids), step_size)]
    
    for chunk in chunks(missing_ids, step_size):
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
                coroutine_for_translating_description(conn_supabase, species)
            )

        # Asynchronously run all coroutinesff
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check which tasks failed
        for i, success in enumerate(results):
            if not success:
                failed_species_id = chunk[i]
                print(f"Task for species_id {failed_species_id} failed")
                failed_tasks.append(failed_species_id)
        
        # Retry the failed tasks
        if failed_tasks:

            print(f"Retrying failed tasks for species_ids: {failed_tasks}")
            await asyncio.sleep(30)
            
            tasks = []
            for species_id in failed_tasks:
                record = get_species_details_from_supabase(conn_supabase, species_id)
                if not record:
                    print(f'no species found with id: {species_id}, continuing')
                    continue

                species = { 'species_id': record[0], 'english_name': record[1], 'dutch_name': record[2], 'genus': record[3], 'species': record[4], 'description': record[5]}
                
                print(f"making coroutine for id: {species_id}")
                
                task = coroutine_for_translating_description(conn_supabase, species)
                tasks.append(task)

            await asyncio.gather(*tasks)

    missing_ids = get_species_ids_with_missing_dutch_description(conn_supabase, start_id, end_id)
    if not missing_ids: 
        print(f'all done! all species have a dutch description for id {start_id} to {end_id}')
    else:
        print(f'all done! but dutch translation missing for species_ids {missing_ids}')

    conn_supabase.close()
    
if __name__ == "__main__":
    asyncio.run(main(0, 30000, 100))