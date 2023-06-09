from dotenv import load_dotenv
import os
import pandas as pd
from supabase import create_client
from matplotlib import pyplot as plt
from shapely.geometry import shape
import geopandas as gpd

load_dotenv()


def run_query():
    supabase = create_client(os.getenv("SUPABASE_APP_URL"), os.getenv("SUPABASE_APP_S_KEY"))

    # Fetch all species
    species_rows = supabase.table('species').select('*').range(18020, 18022).execute().data

    # For each species, fetch ecoregions and draw the map
    for species in species_rows:

        # Fetch all ecoregions of this species
        eco_rows = supabase.table('ecoregion_species') \
            .select('*') \
            .eq('species_id', species['species_id']) \
            .execute().data

        # Fetch the geometries of these ecoregions
        eco_geometries = []
        for eco in eco_rows:
            geometry_rows = supabase.table('ecoregion_shapes') \
                .select('*') \
                .eq('eco_code', eco['eco_code']) \
                .execute().data
            for row in geometry_rows:
                eco_geometries.append(shape(row['geometry']))

        if eco_geometries:
            # Create figure and axes
            fig, ax = plt.subplots(figsize=(1, 1), dpi=100)

            # Loop over each geometry in this eco_code
            for geometry in eco_geometries:
                # Convert the Shapely object to a GeoDataFrame
                gdf = gpd.GeoDataFrame(pd.DataFrame(index=[0]), geometry=[geometry])

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
            plt.savefig(f'images//{species["species_id"]}.png', transparent=True)
            plt.savefig(f'images//{species["species_id"]}.svg', transparent=True)

            # Close the figure
            plt.close(fig)


if __name__ == "__main__":
    run_query()