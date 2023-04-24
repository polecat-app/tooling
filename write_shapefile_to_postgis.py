import geopandas as gpd
from supabase import create_client, Client
import supabase
import csv
import pandas as pd
from geoalchemy2 import WKTElement
from geoalchemy2 import func as ga_func
from sqlalchemy import create_engine

def write_shapefile_to_supabase(database_url, shapefile_path, tablename):
    engine = create_engine(database_url)
    df = gpd.read_file(shapefile_path)
    df.to_postgis(tablename, engine)

