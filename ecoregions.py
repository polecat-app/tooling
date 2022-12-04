import fiona
import matplotlib.pyplot as plt
from descartes import PolygonPatch
#from shapely.geometry import Polygpipon, MultiPolygon, shape

with fiona.collection('data\ecoregions\Ecoregions2017.shp', "r") as input:
    BLUE = '#6699cc'
    fig = plt.figure(1, figsize=(6, 6), dpi=90)
    ax = fig.add_subplot(111)
    for f in input[:100]:
            patch = PolygonPatch(f['geometry'],fc=BLUE ,ec='black',alpha=0.5)
            ax.add_patch(patch)
    plt.autoscale()
    plt.show()

