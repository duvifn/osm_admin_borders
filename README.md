### A small script to process asministrative boundaries layers for loading into OSM.

Run `python admin_boundaries_to_osm.py` for help.

Depends on `gdal/ogr` python binding and `shapely` library.

It's recommended to ensure that input polygons are snapped together.
If the input layer has small gaps between polygons you can run 'QGis -> Processing Toolbox -> Vector Geometry -> Snap geometries to layer' on the input layer before running this script. 
After that run 'QGis ->  Vector -> Geometry Tools -> Check validity' and fix problems with 'QGis -> Processing Toolbox -> Vector Geometry -> Fix geometries'