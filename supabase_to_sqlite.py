import os
from pathlib import Path
from typing import List, Tuple

import psycopg2
import sqlite3
from dotenv import load_dotenv

load_dotenv()


sqlite_db_path = Path(os.getenv("SQLITE_DB_PATH"))



def adjust_data_and_load_into_sqlite(rows: List[Tuple]):
    try:
        print(sqlite_db_path)
        # create a connection to sqlite
        conn = sqlite3.connect(sqlite_db_path)
        cur = conn.cursor()

        # Adjust data and insert into SQLite
        for i, row in enumerate(rows, 1):

            # Adjust your data here as necessary
            adjusted_row = row

            # Insert data into SQLite
            with open('queries/sqlite_query.sql', 'r') as sql_file:
                sql_query = sql_file.read()
                cur.execute(sql_query, adjusted_row)

        # commit the transaction
        conn.commit()

        # close cursor and connection
        cur.close()
        conn.close()

        print("Data adjusted and imported successfully into SQLite")

    except sqlite3.Error as error:
        print("Error while creating a SQLite table", error)


def export_from_supabase():
    try:
        # create a new connection to supabase
        conn = psycopg2.connect(
            dbname=os.getenv("DB"),
            user=os.getenv("USER"),
            password=os.getenv("PW"),
            host=os.getenv("HOST"),
            port=os.getenv("PORT")
        )

        cur = conn.cursor()

        # replace 'table_name' with your table name
        with open('queries/supabase_get_ecoregion_shapes.sql', 'r') as sql_file:
            sql_query = sql_file.read()
            cur.execute(sql_query)

        # fetch all rows from table
        rows = cur.fetchall()

        # adjust data and load into sqlite
        adjust_data_and_load_into_sqlite(rows)

        # close cursor and connection
        cur.close()
        conn.close()

        print("Data exported successfully from Supabase")

    except (Exception, psycopg2.Error) as error:
        print("Error while fetching data from Supabase", error)


def main():
    export_from_supabase()


if __name__ == "__main__":
    main()
