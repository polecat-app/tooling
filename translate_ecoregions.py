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

def dutch_translations_missing_ids(conn):
    query = """
    SELECT eco_code, english
    FROM ecoregion_name
    WHERE dutch IS NULL OR dutch = '';
    """

    cur = conn.cursor()

    # Execute the query with the provided start_id and end_id
    cur.execute(query)

    # Fetch the results
    results = cur.fetchall()

    # Close the cursor
    cur.close()

    return results



def main():
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
    ecoregions = dutch_translations_missing_ids(conn_supabase)

    for ecoregion in ecoregions:
        eco_code = ecoregion[0]
        eco_english = ecoregion[1]
        
        prompt = f'Translate the ecoregion name between the square brackets to dutch: {eco_english}. Only return the dutch text, no brackets or other signs.'
        params = {

        'model': 'gpt-3.5-turbo',
        'messages' : [
            {"role": "system", "content": f"You are a translator"},
            {"role": "user", "content": prompt}
        ],
        'temperature': 0.3,
        'max_tokens' : 400,
        'presence_penalty' : 0.1,
        'frequency_penalty' : 0.1
        }
 
        try:
            translation = openai.ChatCompletion.create(**params)
        except Exception as e:
            print(f"Unexpected error occurred: {e}")
            translation = None
            raise e
        
        if translation:
            dutch_translation = translation.choices[0].message.content

            try:
                # Write to the database
                cur = conn_supabase.cursor()

                # Define your SQL query with placeholders
                query = """
                UPDATE ecoregion_name
                SET dutch = %s
                WHERE eco_code = %s;
                """

                # Execute the query with the provided species_id and dutch_description
                cur.execute(query, (dutch_translation, eco_code))

                # Commit the changes to the database
                conn_supabase.commit()

                # Close the cursor
                cur.close()
                print(f"Wrote dutch translation into the database for eco: {eco_code, eco_english, dutch_translation}")
            except Exception as e:
                print(f'An error occured writing to the database for eco: {eco_code, eco_english, dutch_translation}', e)

    print('all done!')
    conn_supabase.close()
    
if __name__ == "__main__":
    main()