import fiona
import matplotlib.pyplot as plt
from descartes import PolygonPatch
import pyodbc
import pandas as pd
import numpy as np
import difflib

#from shapely.geometry import Polygpipon, MultiPolygon, shape

ECO_names_shapefile = []
ECO_names_animals = []

with fiona.collection('data\ecoregions_2012\wwf_terr_ecos.shp', "r") as input:
    names = []
    BLUE = '#6699cc'
    fig = plt.figure(1, figsize=(6, 6), dpi=90)
    ax = fig.add_subplot(111)
    for f in input:
        names.append(f['properties']['ECO_NAME'])
    ECO_names_shapefile = np.array(list(set(names)))
    
    # plotting the shapes
    # for f in input[:1]:
    #     patch = PolygonPatch(f['geometry'],fc=BLUE ,ec='black',alpha=0.5)
    #     ax.add_patch(patch)
    #plt.autoscale()
    #plt.show()

# get the different ecoregions in the animals database

# connect to db
# set up some constants

conn_string = 'Driver={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=data\WildfinderUpdate.mdb'

# connect to db
con = pyodbc.connect(conn_string)
cur = con.cursor()

# run a query and get the results 
SQL = 'SELECT DISTINCT ECOREGION_NAME FROM ecoregions;' 
results = cur.execute(SQL).fetchall()
ECO_names_animals = []
for region in results:
    print(region[0])
    ECO_names_animals.append(region[0])
cur.close()

ECO_names_animals = np.array(ECO_names_animals)
ECO_names_shapefile = np.array(ECO_names_shapefile)

check = np.isin(ECO_names_animals, ECO_names_shapefile)
nr_true = np.count_nonzero(check)
nr_false = np.size(check) - nr_true

missing_eco = ECO_names_animals[~check]

eco_replacement = []
for ecoregion in missing_eco:
    eco_replacement.append((ecoregion, difflib.get_close_matches(ecoregion, ECO_names_shapefile)[0]))

print(eco_replacement)

