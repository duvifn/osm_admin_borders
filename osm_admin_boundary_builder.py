from osgeo import ogr
from osgeo import osr
import node
import way
import relation
import xml.etree.ElementTree as etree
import sys

class OsmAdminBoundaryBuilder(object):
    def __init__(self, options):
        self.node_cache = node.NodeCache(options)
        self.way_cache = way.WayCache(self.node_cache)
        self.relation_cache = relation.RelationCache(self.way_cache)
        self.output_file = options.output_file
        self.minimum_common_way_node_number = options.minimum_common_way_node_number
        self.options = options

    def ogr_geometry_to_osm_admin_boundary(self, ogrgeometry, relation_tags, way_tags, node_tags):
        geometryType = ogrgeometry.GetGeometryType()
        if (geometryType == ogr.wkbPolygon or
                geometryType == ogr.wkbPolygon25D):
            self.relation_cache.add_from_ogr(ogrgeometry, relation_tags, way_tags, node_tags)
        elif (geometryType == ogr.wkbMultiPolygon or
                geometryType == ogr.wkbMultiPolygon25D):
                for poly in ogrgeometry:
                    self.relation_cache.add_from_ogr(poly, relation_tags, way_tags, node_tags)
            
            # TODO: remove this after testing
            # print("Only singlepart layers are currently supported. Use QGis : Vector -> Geometry Tools -> Multipart To Singlepart to create a supported file.")
            # sys.exit(1)
        elif (geometryType == ogr.wkbMultiPoint or
                geometryType == ogr.wkbMultiLineString or
                geometryType == ogr.wkbGeometryCollection or
                geometryType == ogr.wkbMultiPoint25D or
                geometryType == ogr.wkbMultiLineString25D or
                geometryType == ogr.wkbGeometryCollection25D):
            print("Only polygon layers are currently supported.")
            sys.exit(1)
        else:
            print("Only polygon layers are currently supported.")
            sys.exit(1)
    
    

    def optimize_ways(self):
        # Find shared paths and replace with parts
        way_cache = self.way_cache
        relation_cache = self.relation_cache

        way_list = way_cache.as_list()
        way_list.sort(key= lambda w: len(w.nodes), reverse=True)
        #TODO: check wen needed
        way_set = set(way_list)
        i = 0
        # way_list length is going to be changed
        while i < len(way_list):
            way = way_list[i]
            way_split_positions = []
            # We check this since way can be one 
            # that already replaced (a deleted way)
            if len(way.referrers) > 0:
                # clone referres since it is going to be changed while iterating
                referrers = way.referrers[:]
               
                nodes = way.nodes

                # loop over nodes and find similar paths
                node_index = 0
                while node_index < len(nodes) - 1:
                    all_similar_paths = []
                    node = nodes[node_index]
                    target_ways = [ ref[0] for ref in node.referrers if (ref[0] != way and len(ref[0].referrers) > 0) ]
                    for target_way in target_ways:
                        similar_paths = target_way.find_commom_path(way, node_index, self.minimum_common_way_node_number)
                        
                        if len(similar_paths) == 0:
                            # No match, try reverse ordered nodes for adjoined polygons
                            similar_paths = target_way.find_commom_path(way, node_index, self.minimum_common_way_node_number, True)
                            if len(similar_paths) > 0:
                                str_id = target_way.str_id
                                target_way.reverse()
                                way_cache.update(str_id)

                        # There could be multiple similar paths in a way, 
                        # since node can be referrenced more than once by the same way
                        for similar_path in similar_paths:
                            all_similar_paths.append((target_way, similar_path, similar_path[1] - similar_path[0]))
                    if len(all_similar_paths) > 0:
                        # get min path
                        smallest_length =  min(all_similar_paths, key = lambda t: t[2])[2]
                        #largest_length = max(all_similar_paths, key = lambda t: t[2])[2]
                        # Sort by way id so paths would be ordered by their way
                        all_similar_paths.sort(key=lambda path: path[0].id)
                        
                        path_index = 0
                        while path_index < len(all_similar_paths):
                            path = all_similar_paths[path_index]
                            target_way = path[0]
                            # current_referrers = target_way.referrers[:]
                            split_positions = []
                            split_positions.append((path[1][0],  path[1][0] + smallest_length))
                            # while we are on the same way
                            while path_index + 1 < len(all_similar_paths) and target_way == all_similar_paths[path_index + 1][0]:
                                path_index += 1
                                path = all_similar_paths[path_index]
                                split_positions.append((path[1][0],  path[1][0] + smallest_length))
                            #splited_nodes = target_way.split_at_positions(split_positions)
                            
                            replace_way(target_way, split_positions, way_cache, relation_cache,  way_list, way_set)
                            # replace the way in referrers
                            # replaces = []
                            # for node_list in splited_nodes:
                            #     new_way = way_cache.add_from_node_list(node_list, target_way.tags)
                            #     if not new_way in way_set:
                            #         way_list.append(new_way)
                            #         way_set.add(new_way)
                            #     replaces.append(new_way)
                            # for referrer in current_referrers:
                            #     referrer_str_id = referrer[0].str_id
                            #     referrer[0].replace_member(target_way, replaces)
                            #     # update cache since referrer.str_id has been changed 
                            #     relation_cache.update(referrer_str_id)

                            path_index += 1
                        
                        # increment node_index by minimum length size
                        way_split_positions.append((node_index, node_index + smallest_length))
                        node_index += smallest_length
                        # push the new ways to the end of the list
                    else: #len(all_similar_paths) == 0
                        node_index += 1
                
                # We finished looping on our way nodes.
                # Split also our way by way_split_positions and replace in referrers
                if len(way_split_positions) > 0:
                    replace_way(way, way_split_positions, way_cache, relation_cache, way_list, way_set)
        
            i += 1
        # Split long ways

    def output_to_file(self):
        dec_string = '<?xml version="1.0"?>\n<osm version="0.6" generator="admin_boundaries_to_osm.py">\n'
        with open(self.output_file, 'w', buffering=-1) as f:
            f.write(dec_string)
            
            # nodes
            for unused, node in self.node_cache._cache.items():
                if len(node.referrers) > 0:
                    xmlobject = node.to_xml(self.options)
                    f.write(etree.tostring(xmlobject, encoding='unicode'))
                    f.write('\n')
            
            # ways
            for unused, way in self.way_cache._cache.items():
                if len(way.referrers) > 0:
                    xmlobject = way.to_xml(self.options)
                    f.write(etree.tostring(xmlobject, encoding='unicode'))
                    f.write('\n')

            #relations
            for unused, relation in self.relation_cache._cache.items():
                xmlobject = relation.to_xml(self.options)
                f.write(etree.tostring(xmlobject, encoding='unicode'))
                f.write('\n')

            f.write('</osm>')

def replace_way(way, way_split_positions, way_cache, relation_cache,  way_list, way_set):
    splited_nodes = way.split_at_positions(way_split_positions)
                
    # replace the way in referrers
    replaces = []
    for node_list in splited_nodes:
        new_way = way_cache.add_from_node_list(node_list, way.tags)
        if not new_way in way_set:
            way_list.append(new_way)
            way_set.add(new_way)
        replaces.append(new_way)
    update_referrers(relation_cache, way, replaces)
    # TODO: treat tags (combine with priority to lower admin levels)

def update_referrers(relation_cache, way, replaces):
    current_referrers = way.referrers[:]
    for referrer in current_referrers:
        referrer_str_id = referrer[0].str_id
        referrer[0].replace_member(way, replaces)
        # update cache since referrer.str_id has been changed 
        relation_cache.update(referrer_str_id)