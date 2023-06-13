import os
from pathlib import Path
from typing import List, Tuple

import psycopg2
import sqlite3

import supabase
from dotenv import load_dotenv

load_dotenv()


sqlite_db_path = Path(os.getenv("SQLITE_DB_PATH"))
supabase_app_url = os.getenv("SUPABASE_APP_URL")
supabase_app_s_key = os.getenv("SUPABASE_APP_S_KEY")


def run_query():

    # create supabase client
    client_app = supabase.create_client(supabase_app_url, supabase_app_s_key)

    # Get first 10 species from species_name table where name is not null
    result = client_app.from_("species_name").select("species_id, english").order("species_id").range(29000, 30000).execute()

    # For each species, find the first species with same name in sqlite 'english'table
    conn = sqlite3.connect(sqlite_db_path)
    cur = conn.cursor()
    for species in result.data:

        # If no english name, skip
        if species['english'] is None:
            continue

        # Get first species with same name in sqlite 'english' table
        cur.execute("SELECT * FROM english WHERE vernacularName = ? LIMIT 1", (species['english'],))
        result_en = cur.fetchone()

        # If no species with same name, skip
        if result_en is None:
            continue

        # Get first species in sqlite 'dutch' table with same id
        cur.execute("SELECT * FROM dutch WHERE id = ? LIMIT 1", (result_en[0],))
        result_nl = cur.fetchone()
        if result_nl:

            print(species['species_id'], result_en[1], result_nl[1])

            # Write dutch name to species_name table in supabase
            client_app.from_("species_name").update({"dutch": result_nl[1]}).eq("species_id", species['species_id']).execute()



    cur.close()
    conn.close()


if __name__ == "__main__":
    run_query()


