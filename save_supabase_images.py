import os
from pathlib import Path

import psycopg2
import sqlite3
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()


sqlite_db_path = Path(os.getenv("SQLITE_DB_PATH"))
images_path = Path(os.getenv("IMAGES_PATH"))
supabase_client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))



def export_from_supabase():
    try:
        # create a new connection to supabase
        conn_supabase = psycopg2.connect(
            dbname=os.getenv("DB"),
            user=os.getenv("USER"),
            password=os.getenv("PW"),
            host=os.getenv("HOST"),
            port=os.getenv("PORT")
        )

        cur_supabase = conn_supabase.cursor()

        # replace 'table_name' with your table name
        with open('queries/supabase_get_ecoregion_shapes.sql', 'r') as sql_file:
            sql_query = sql_file.read()
            cur_supabase.execute(sql_query)

        # fetch all rows from table
        rows = cur_supabase.fetchall()
        bucket = supabase_client.storage.from_("animal-images")

        for row in rows:

            # create a connection to sqlite
            conn_sqlite = sqlite3.connect(sqlite_db_path)
            cur_sqlite = conn_sqlite.cursor()

            # Check if image is saved in sqlite
            no_thumbnail = False
            with open('queries/sqlite_query.sql', 'r') as sql_file:
                sql_query = sql_file.read()
                cur_sqlite.execute(sql_query, (row[0],))
                result = cur_sqlite.fetchone()
                if not bool(result[0]):
                    no_thumbnail = True

            # commit the transaction
            conn_sqlite.commit()

            # close cursor and connection
            cur_sqlite.close()
            conn_sqlite.close()

            # Continue if image not in sqlite
            if no_thumbnail:
                print("NO THUMBNAIL", row[0])
                continue

            try:
                response_bytes = bucket.download(row[1])

                # Save response as jpeg with species_id as filename
                filename = f"{row[0]}.jpg"
                print(Path(images_path / filename))
                with open(images_path / filename, "wb") as file:
                    file.write(response_bytes)
                    print(f"{row[0]}: Image downloaded")
            except Exception as e:
                print(f"{row[0]}: {e}")

        # close cursor and connection
        cur_supabase.close()
        conn_supabase.close()

    except (Exception, psycopg2.Error) as error:
        print("Error while fetching data from Supabase", error)


def remove_urls_if_no_image():

    # List all files in the folder
    files = os.listdir(images_path)

    # create a connection to sqlite
    conn_sqlite = sqlite3.connect(sqlite_db_path)
    cur_sqlite = conn_sqlite.cursor()

    # Get all species ids
    cur_sqlite.execute("SELECT species_id FROM species WHERE thumbnail IS 1")
    rows = cur_sqlite.fetchall()

    # Iterate through the files
    file_ids = []
    for file in files:

        # Check if the item is a file (not a subfolder)
        if os.path.isfile(os.path.join(images_path, file)):

            # Remove the file extension
            file_name = os.path.splitext(file)[0]
            file_ids.append(int(file_name))

    # Get set difference
    set1 = set(file_ids)
    print('file ids', len(set1))
    print(file_ids[0])

    set2 = set(row[0] for row in rows)
    print('rows', len(set2))
    difference = set2 - set1

    for index in list(difference):
        print(index)
        # cur_sqlite.execute("UPDATE species SET thumbnail = 0 WHERE species_id = ?", (index,))
        # cur_sqlite.execute("UPDATE species SET cover_url = NULL WHERE species_id = ?", (index,))

    # close cursor and connection
    conn_sqlite.commit()
    cur_sqlite.close()
    conn_sqlite.close()


def main():
    remove_urls_if_no_image()


if __name__ == "__main__":
    main()
