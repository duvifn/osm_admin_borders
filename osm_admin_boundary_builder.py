from osgeo import ogr
from osgeo import osr
import node
import way
import relation
import xml.etree.ElementTree as etree

class OsmAdminBoundaryBuilder(object):
    def __init__(self, options):
        self.node_cache = node.NodeCache(options)
        self.way_cache = way.WayCache(self.node_cache)
        self.relation_cache = relation.RelationCache(self.way_cache)
        self.output_file = options.output_file
        self.minimum_common_way_node_number = options.minimum_common_way_node_number
        self.way_length_limit = options.way_length_limit
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
        else:
            raise RuntimeError("Only polygon layers are currently supported.")

    def optimize_ways(self):
        # Find shared paths and replace original ways with parts
        way_cache = self.way_cache
        relation_cache = self.relation_cache

        way_list = way_cache.as_list()
        way_list.sort(key= lambda w: len(w.nodes), reverse=True)
        #TODO: check when needed
        way_set = set(way_list)
        i = 0
        # way_list length is going to be changed
        while i < len(way_list):
            way = way_list[i]
            way_split_positions = []
            # We check this since way can be one 
            # that already replaced (a deleted way)
            if len(way.referrers) > 0:
                nodes = way.nodes

                # loop over nodes and find similar paths
                node_index = 0
                while node_index < len(nodes) - 1:
                    all_similar_paths = []
                    node = nodes[node_index]
                    target_ways = [ ref[0] for ref in node.referrers if (ref[0] != way and len(ref[0].referrers) > 0) ]
                    for target_way in target_ways:
                        similar_paths = target_way.find_commom_path(way, node_index, min(self.minimum_common_way_node_number, len(way.nodes)))
                        
                        if len(similar_paths) == 0:
                            # No match, try reverse ordered nodes for adjoined polygons
                            similar_paths = target_way.find_commom_path(way, node_index, min(self.minimum_common_way_node_number, len(way.nodes)), True)
                            if len(similar_paths) > 0:
                                str_id = target_way.str_id
                                target_way.reverse()
                                # similar path indices are now pointing into the reversed list 
                                # so no need to call target_way.find_commom_path again
                                
                                # update cache since target_way.str_id has been changed 
                                way_cache.update(str_id)

                        # There could be multiple similar paths in a way, 
                        # since node can be referrenced more than once by the same way
                        for similar_path in similar_paths:
                            all_similar_paths.append((target_way, similar_path, similar_path[1] - similar_path[0]))
                    if len(all_similar_paths) > 0:
                        # get min path
                        smallest_length =  min(all_similar_paths, key = lambda t: t[2])[2]
                        # Sort by way id so paths would be ordered by their way
                        all_similar_paths.sort(key=lambda path: path[0].id)
                        
                        path_index = 0
                        while path_index < len(all_similar_paths):
                            path = all_similar_paths[path_index]
                            target_way = path[0]

                            split_positions = []
                            split_positions.append((path[1][0],  path[1][0] + smallest_length))
                            # while we are on the same way
                            while path_index + 1 < len(all_similar_paths) and target_way == all_similar_paths[path_index + 1][0]:
                                path_index += 1
                                path = all_similar_paths[path_index]
                                split_positions.append((path[1][0],  path[1][0] + smallest_length))
                            
                            replaces = split_way(target_way, split_positions, way_cache, relation_cache)
                            for new_way in replaces:
                                if not new_way in way_set:
                                    # push the new ways to the end of the list
                                    way_list.append(new_way)
                                    way_set.add(new_way)
                            path_index += 1
                        
                        way_split_positions.append((node_index, node_index + smallest_length))
                        # increment node_index by minimum length size
                        node_index += smallest_length
                        
                    else: #len(all_similar_paths) == 0
                        node_index += 1
                
                # We finished looping over our way nodes.
                # Split way by way_split_positions and replace in referrers
                if len(way_split_positions) > 0:
                    replaces = split_way(way, way_split_positions, way_cache, relation_cache)
                    for new_way in replaces:
                        if not new_way in way_set:
                            # push the new ways to the end of the list
                            way_list.append(new_way)
                            way_set.add(new_way)
            i += 1
    
    def split_long_ways(self):
        # Split long ways. OSM API way node's limit is currently 2,000
        way_cache = self.way_cache
        way_length_limit = self.way_length_limit
        way_list = [way for way in way_cache.as_list() if len(way.nodes) > way_length_limit and len(way.referrers) > 0]
        
        for way in way_list:
            split_positions = []
            node_number = len(way.nodes)
            parts = node_number // way_length_limit
            for i in range(parts):
                split_position = (i * way_length_limit - (1 if i > 0 else 0), (i  + 1) * way_length_limit - 1)
                split_positions.append(split_position)
            
            # We don't need to worry about last segment since way.split_at_positions does it for us
            split_way(way, split_positions, way_cache, self.relation_cache)
            

    def output_to_file(self):
        dec_string = '<?xml version="1.0"?>\n<osm version="0.6" generator="admin_boundaries_to_osm.py">\n'
        with open(self.output_file, 'w', buffering=-1, encoding='utf8') as f:
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

def merge_tags(tags1, tags2):
    if 'admin_level' in tags1 and 'admin_level' in tags2:
        tags = sorted((tags1,tags2), key=lambda d: int(d['admin_level']))
    else:
        tags = (tags1,tags2)
    result = tags[1].copy()
    result.update(tags[0])
    
    return result
def split_way(way, way_split_positions, way_cache, relation_cache):
    splited_nodes = way.split_at_positions(way_split_positions)
                
    # replace the way in referrers
    replaces = []
    for node_list in splited_nodes:
        new_way = way_cache.add_from_node_list(node_list, way.tags, merge_tags)
        
        replaces.append(new_way)
    update_referrers(relation_cache, way, replaces)
    return replaces

def update_referrers(relation_cache, way, replaces):
    # Clone referrers because it is going to be changed while iterating
    current_referrers = way.referrers[:]
    for referrer in current_referrers:
        referrer_str_id = referrer[0].str_id
        referrer[0].replace_member(way, replaces)
        # update cache since referrer.str_id has been changed 
        relation_cache.update(referrer_str_id)