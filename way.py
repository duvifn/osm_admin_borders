from datetime import datetime
import json
import xml.etree.ElementTree as etree
import global_id

class Way(object):

    def __init__(self, nodes, way_id, tags = {}):
        self.id = way_id
        self.nodes = nodes[:]
        self.tags = tags
        self.str_id = get_str_id(nodes)
        self.referrers = []
   
    def add_referrer(self, referrer):
        referrers = self.referrers
        for ref in referrers:
            if ref[0] == referrer:
                ref[1] += 1
                return
        self.referrers.append([referrer,1])

    def remove_referrer(self, referrer):
        referrers = self.referrers
        for i in range(len(referrers)):
            ref = referrers[i]
            if ref[0] == referrer:
                ref[1] -= 1
                if ref[1] == 0:
                    referrers.remove(ref)
                break
  
    def to_xml(self, options):
        # Build up a dict for optional settings
        attributes = {}
        if options.add_version:
            attributes.update({'version':'1'})

        if options.addTimestamp:
            attributes.update({'timestamp':datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')})

        
        xmlattrs = {'visible':'true', 'id':str(self.id)}
        xmlattrs.update(attributes)

        xmlobject = etree.Element('way', xmlattrs)

        for node in self.nodes:
            nd = etree.Element('nd',{'ref':str(node.id)})
            xmlobject.append(nd)

        for (key, value) in self.tags.items():
            tag = etree.Element('tag', {'k':str(key), 'v':str(value)})
            xmlobject.append(tag)

        return xmlobject

    def reverse(self):
        self.nodes.reverse()
        self.str_id = get_str_id(self.nodes)

    def find_commom_path(self, other_way, starting_index_other_way, minimum_common_way_node_number, reverse = False):
        result = []
        nodes = self.nodes
        if reverse:
            # Be aware that now the indices returns by this function
            # are pointing into the the reversed node list
            nodes = nodes[:]
            nodes.reverse()
        other_nodes = other_way.nodes
        starting_node = other_nodes[starting_index_other_way]
        node_length = len(nodes)
        other_node_length = len(other_nodes)

        for i in range(node_length):
            node = nodes[i]
            
            if node == starting_node:
                j = 0
                while ((i + j + 1 < node_length) and
                       (starting_index_other_way + j + 1 < other_node_length) and
                       (nodes[i + j + 1] == other_nodes[starting_index_other_way + j + 1])):
                    j += 1
                if j >= minimum_common_way_node_number -1:
                    result.append((i, i + j))
                # A node can be referrenced by a way more than once,
                # so we wouldn't break here

        return result
    
    def split_at_positions(self, positions):
        nodes = self.nodes
        nodes_length = len(nodes)
        result = []
        
        # Positions are assumed to be sorted according their index in the way
        i = 0
        node_index = 0
        
        # int division
        while (i // 2) < len(positions):
            next_position = positions[i // 2][i % 2]
            if next_position - node_index > 0:
                segment = nodes[node_index: next_position + 1]
                result.append(segment)
            node_index = next_position
            i += 1
        
        # Last segment
        if next_position < nodes_length -1:
            segment = nodes[next_position: nodes_length]
            result.append(segment)
        return result

# Helper function to get a new ID
def get_new_id():
    return global_id.get_new_id()

def get_str_id(nodes):
    return '_'.join([ str(x.id) for x in nodes ])

def remove_duplicates(nodes):
    # Remove sequential similar nodes
    for i in range(len(nodes) -1, 0, -1):
        if nodes[i].id ==  nodes[i-1].id:
            del nodes[i]

class WayCache(object):
    def __init__(self, node_cache):
        self._cache = {}
        self.node_cache = node_cache

    def remove(self, way):
        for node in way.nodes:
            node.remove_referrer(way)
        if way.str_id in self._cache:
            del self._cache[way.str_id]

    def add_from_node_list(self, node_list, tags, merge_tags_func = None):
        nodes = node_list[:]
        remove_duplicates(nodes)
        str_id = get_str_id(nodes)
        if str_id in self._cache:
            way = self._cache[str_id]
            if (merge_tags_func):
                way.tags = merge_tags_func(way.tags, tags)
        else:
            way = Way(nodes, get_new_id(), tags)
            self._cache[str_id] = way
            for node in nodes: 
                node.add_referrer(way)
        return way

    def add_from_ogr(self, ogr_line, tags, node_tags = {}, merge_tags_func = None):
        nodes = []
        node_cache = self.node_cache
        for i in range(ogr_line.GetPointCount()):
            point = ogr_line.GetPoint(i)
            
            nd = node_cache.add_from_touple(point, node_tags)
            nodes.append(nd)
        remove_duplicates(nodes)

        str_id = get_str_id(nodes)
        if str_id in self._cache:
            way = self._cache[str_id]
            if (merge_tags_func):
                way.tags = merge_tags_func(way.tags, tags)
        else:
            way = Way(nodes, get_new_id(), tags)
            self._cache[str_id] = way
            for node in nodes: 
                node.add_referrer(way)
        return way
    
    def update(self, str_id):
        cache = self._cache
        if str_id in cache:
            way = cache[str_id]
            del cache[str_id]
            cache[way.str_id] = way

    def as_list(self):
        return [ way for unused, way in self._cache.items() ]