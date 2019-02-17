import sys
import os
import optparse
from osgeo import ogr
from osgeo import osr


import tags
from osm_admin_boundary_builder import OsmAdminBoundaryBuilder
import global_id
usage = """%prog SRCFILE

SRCFILE can be a file path or a PostgreSQL connection string such as:
"PG:dbname=pdx_bldgs user=emma host=localhost" (including the quotes).
This scripts assumes that the input file contains ONLY the deepest level (smallest polygons).
"""
parser = optparse.OptionParser(usage=usage)

parser.add_option("-o", "--output_file", dest="output_file", metavar="OUTPUT",
                    help="Set destination .osm file name and location.")

parser.add_option("-p", "--digits_of_precision", dest="digits_of_precision", metavar="DIGITS_OF_PRECISION", type=int, default=5,
                    help="Set node digit precision. Used as a snapping to grid tolarence for nodes. default to 5")

# Add version attributes. this can cause big problems so surpress the help
parser.add_option("--add_version", dest="add_version", action="store_true",
                    help=optparse.SUPPRESS_HELP)

parser.add_option("--aggregation_method", dest="aggregation_method",
                    help="Select the aggragation method. See " +
                      "the aggregation_methods/level_definition_example for valid values.")
parser.add_option("--minimum_common_way_node_number", dest="minimum_common_way_node_number", type=int, default=10,
                    help="The minimum node number that ways have to share in order to create one common way")                      
# Add timestamp attributes. Again, this can cause big problems so surpress the help
parser.add_option("--add-timestamp", dest="addTimestamp", action="store_true",
                    help=optparse.SUPPRESS_HELP)
# Add positive id. Again, this can cause big problems so surpress the help
parser.add_option("--positive_id", dest="positive_id", action="store_true",
                    help=optparse.SUPPRESS_HELP)

(options, args) = parser.parse_args()

if len(args) < 1:
    parser.print_help()
    parser.error("you must specify a source filename")
elif len(args) > 1:
    parser.error("you have specified too many arguments, " +
                    "only supply the source filename")

# for debuging only
if options.positive_id:
    global_id.set_positive()

 # Stuff needed for locating translation methods
if options.aggregation_method:
    # add dirs to path if necessary
    (root, ext) = os.path.splitext(options.aggregation_method)
    if os.path.exists(options.aggregation_method) and ext == '.py':
        # user supplied translation file directly
        sys.path.insert(0, os.path.dirname(root))
    else:
        # first check translations in the subdir translations of cwd
        sys.path.insert(0, os.path.join(os.getcwd(), "aggregation_methods"))
        # then check subdir of script dir
        sys.path.insert(1, os.path.join(os.path.dirname(__file__), "aggregation_methods"))
        # (the cwd will also be checked implicityly)

    # strip .py if present, as import wants just the module name
    if ext == '.py':
        options.aggregation_method = os.path.basename(root)

    try:
        aggregation_method = __import__(options.aggregation_method, fromlist = [''])
    except ImportError as e:
        parser.error("Could not load translation method '%s'. Translation "
                "script must be in your current directory, or in the "
                "translations/ subdirectory of your current or ogr2osm.py "
                "directory. The following directories have been considered: %s"
                % (options.aggregation_method, str(sys.path)))
    except SyntaxError as e:
        parser.error("Syntax error in '%s'. Translation script is malformed:\n%s"
                % (options.aggregation_method, e))

   

source = args[0]
data_source = ogr.Open(source, 0) # 0 means read-only. 1 means writeable.

# Check to see if shapefile is found.
if data_source is None:
    print ('Could not open %s' % (source))
    sys.exit(1)
else:
    layer = data_source.GetLayer()

# Get desiered admin level
deepest_admin_level = None
if options.aggregation_method:
    levels_defs = aggregation_method.get_level_definitions(layer)
    deepest_level = next(obj for obj in levels_defs if obj['deepest'])
    if deepest_level and deepest_level['admin_level'] is not None:
        deepest_admin_level = deepest_level['admin_level']

tag_mapper = tags.TagMapper()
osm_builder = OsmAdminBoundaryBuilder(options)

# Loop over all features and build OSM objects
for feature in layer:
    ogrgeometry = feature.GetGeometryRef()
    
    node_tags = tag_mapper.get_node_tags(feature, layer)
    way_tags = tag_mapper.get_way_tags(feature, layer)  
    relation_tags = tag_mapper.get_relation_tags(feature, layer)
    if deepest_admin_level:
        relation_tags['admin_level'] = deepest_admin_level
    
    osm_builder.ogr_geometry_to_osm_admin_boundary(ogrgeometry, relation_tags, way_tags, node_tags)



# Aggregate lower levels
if aggregation_method:
#if 0:
    levels = [ level for level in levels_defs if not level['deepest'] ]
    for level in levels:
        divided_features = level['features']
        for key, features in divided_features.items():
            geom = ogr.Geometry(ogr.wkbMultiPolygon)
            for feature in features:
                ogrgeometry = feature.GetGeometryRef()
                geometryType = ogrgeometry.GetGeometryType()
                if (geometryType == ogr.wkbPolygon or
                    geometryType == ogr.wkbPolygon25D):
                    geom.AddGeometry(ogrgeometry.Clone())
                elif (geometryType == ogr.wkbMultiPolygon or
                        geometryType == ogr.wkbMultiPolygon25D):
                        for polygon in ogrgeometry:
                            geom.AddGeometry(polygon.Clone())
            
            result_geometry = geom.UnionCascaded()
            relation_tags = tag_mapper.get_common_value_fields(features, layer)
            relation_tags['admin_level'] = level['admin_level']
            osm_builder.ogr_geometry_to_osm_admin_boundary(result_geometry, relation_tags, {}, {})

# Optimize ways
osm_builder.optimize_ways()

# Write output file
osm_builder.output_to_file()