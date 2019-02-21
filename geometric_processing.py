from osgeo import ogr
from osgeo import osr

from shapely.geometry import shape, JOIN_STYLE
from shapely import wkb
from shapely.ops import nearest_points, snap

def remove_slivers(ogr_geometry, epsilon):
    wkb_buffer = ogr_geometry.ExportToWkb()
    shapely_geom = wkb.loads(wkb_buffer)
    result = shapely_geom.buffer(epsilon, 1, join_style=JOIN_STYLE.mitre).buffer(-epsilon, 1, join_style=JOIN_STYLE.mitre)
    result_wkb = wkb.dumps(result)
    return ogr.CreateGeometryFromWkb(result_wkb)

def snap_shapely_geometries(geom_list, tolerance):
    for i in range(len(geom_list)):
        geom = geom_list[i]
        for j in range(len(geom_list)):
            target_geom = geom_list[j]
            if target_geom != geom:
                nearest =  nearest_points(geom, target_geom)
                if nearest[0].distance(nearest[1]) <= tolerance:
                    snapped = snap(geom, target_geom, tolerance)
                    geom = snapped
                    geom_list[i] = snapped

def snap_ogr_features(layer, tolerance):
    feature_geom_list = []
    for feature in layer:
        ogr_geometry = feature.GetGeometryRef()
        wkb_buffer = ogr_geometry.ExportToWkb()
        shapely_geom = wkb.loads(wkb_buffer)
        feature_geom_list.append((feature, shapely_geom))
    geom_list = [x[1] for x in feature_geom_list]
    snap_shapely_geometries(geom_list, tolerance)
    
    for i in range(len(geom_list)):
        feature = feature_geom_list[i][0]
        wkb_buf =  wkb.dumps(geom_list[i])
        feature.SetGeometry(ogr.CreateGeometryFromWkb(wkb_buf))
    layer.ResetReading()
