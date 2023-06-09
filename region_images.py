import ast

from dotenv import load_dotenv
import os
import pandas as pd
import psycopg2
from supabase import create_client
from matplotlib import pyplot as plt
from shapely.geometry import shape
import geopandas as gpd

load_dotenv()


def run_query():

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
    with open('queries/supabase_query.sql', 'r') as sql_file:
        sql_query = sql_file.read()
        cur.execute(sql_query)

    # fetch all rows from table
    rows = cur.fetchall()

    for row in rows:

        # Create figure and axes
        fig, ax = plt.subplots(figsize=(1, 1), dpi=500)

        # Simplify the geometry
        geometry_simplified = shape(ast.literal_eval(row[1]))

        # Convert the Shapely object to a GeoDataFrame
        gdf = gpd.GeoDataFrame(pd.DataFrame(index=[0]), geometry=[geometry_simplified])

        # Set the GeoDataFrame's CRS to EPSG:4326
        gdf.set_crs("EPSG:4326", inplace=True)

        # Plot the GeoDataFrame
        gdf.plot(ax=ax, color='black')

        # Set axes limits to cover the whole world
        ax.set_xlim([-180, 180])
        ax.set_ylim([-90, 90])

        ax.axis('off')

        # Remove margins
        plt.margins(0)

        # Save as PNG and SVG
        plt.savefig(f'images//{row[0]}.png', transparent=True)

        # Close the figure
        plt.close(fig)


if __name__ == "__main__":
    run_query()