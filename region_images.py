import ast

from dotenv import load_dotenv
import os
import pandas as pd
import psycopg2
from matplotlib import pyplot as plt
from shapely.geometry import shape
import geopandas as gpd
from PIL import Image


load_dotenv()


def overlay_images(image_paths, output_path, compress=True, quality=85):
    if len(image_paths) == 1:

        # Save the first image
        base_image = Image.open(image_paths[0]).convert("RGBA")

        # Save the resulting image
        base_image.save(output_path, "PNG")

    if len(image_paths) == 0:
        raise ValueError("No images provided")

    # Open the first image
    base_image = Image.open(image_paths[0]).convert("RGBA")
    base_width, base_height = base_image.size

    # Create a white background image with transparency
    white_background = Image.new("RGBA", (base_width, base_height), (255, 255, 255, 255))

    # Paste the base image onto the white background
    white_background.paste(base_image, (0, 0), mask=base_image)

    for image_path in image_paths[1:]:
        # Open the next image
        overlay_image = Image.open(image_path).convert("RGBA")

        # Ensure both images have the same size
        if base_image.size != overlay_image.size:
            raise ValueError("Images must have the same size")

        # Overlay the images
        white_background = Image.alpha_composite(white_background, overlay_image)

    # Convert the image to RGB mode for saving as JPEG
    white_background = white_background.convert("RGB")

    # Save the resulting image with compression
    if compress:
        white_background.save(output_path, "JPEG", quality=quality, optimize=True)
    else:
        white_background.save(output_path, "PNG")



def overlay_all():

    # Open the first image
    base_image = Image.open('images//regions//AA0101.png').convert("RGBA")

    for image_path in os.listdir('images//regions'):

        # Open the next image
        overlay_image = Image.open(f'images//regions//{image_path}').convert("RGBA")

        # Ensure both images have the same size
        if base_image.size != overlay_image.size:
            raise ValueError("Images must have the same size")

        # Overlay the images
        base_image = Image.alpha_composite(base_image, overlay_image)

    # Save the resulting image
    base_image.save('images//world//world.png', "PNG")


def save_distribution_per_animal():

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
    with open('queries/supabase_get_species_regions.sql', 'r') as sql_file:
        sql_query = sql_file.read()
        cur.execute(sql_query)

    # fetch all rows from table
    rows = cur.fetchall()

    for row in rows:
        print(row)
        species_id = row[0]
        eco_codes = row[1]

        png_paths = ['images//world//world.png']
        for eco_code in eco_codes:
            png_paths.append(f'images//regions//{eco_code}.png')

        overlay_images(png_paths, f'images//distribution_2//{species_id}.jpg')


def get_ecoregion_image():

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

    for row in rows:

        # Create figure and axes
        fig, ax = plt.subplots(figsize=(1, 1), dpi=500)

        # Simplify the geometry
        geometry_simplified = shape(ast.literal_eval(row[1]))

        # Convert the Shapely object to a GeoDataFrame
        gdf = gpd.GeoDataFrame(pd.DataFrame(index=[0]), geometry=[geometry_simplified])

        # # Set the GeoDataFrame's CRS to EPSG:4326
        # gdf.set_crs("EPSG:4326", inplace=True)

        # Plot the GeoDataFrame
        gdf.plot(ax=ax, color='black')

        # Set axes limits to cover the whole world
        ax.set_xlim([-180, 180])
        ax.set_ylim([-90, 90])

        ax.axis('off')

        # Remove margins
        plt.margins(0)

        # Save as PNG and SVG
        plt.savefig(f'images//regions//{row[0]}.png', transparent=True)

        # Close the figure
        plt.close(fig)


if __name__ == "__main__":
    save_distribution_per_animal()