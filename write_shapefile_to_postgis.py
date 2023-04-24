import geopandas as gpd
from sqlalchemy import create_engine

def write_shapefile_to_supabase(database_url, shapefile_path, tablename):
    engine = create_engine(database_url)
    df = gpd.read_file(shapefile_path)
    df.to_postgis(tablename, engine)

