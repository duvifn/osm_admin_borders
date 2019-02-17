from datetime import datetime
import json
import xml.etree.ElementTree as etree
import global_id

class Relation(object):

    def __init__(self, members, rel_id, tags = {}):
        self.id = rel_id
        self.members = members
        self.tags = tags
        self.str_id = get_str_id(members, tags)
    
    def to_xml(self, options):
        
        # Build up a dict for optional settings
        attributes = {}
        if options.add_version:
            attributes.update({'version':'1'})

        if options.addTimestamp:
            attributes.update({'timestamp':datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')})

        
        xmlattrs = {'visible':'true', 'id':str(self.id)}
        xmlattrs.update(attributes)

        xmlobject = etree.Element('relation', xmlattrs)

        for member in self.members:
            member_attributes = member.copy()
            member_attributes['ref'] = str(member['ref'].id)
            mbr = etree.Element('member',member_attributes)
            xmlobject.append(mbr)

        for (key, value) in self.tags.items():
            tag = etree.Element('tag', {'k':str(key), 'v':str(value)})
            xmlobject.append(tag)

        return xmlobject
    
    def replace_member(self, member_ref, member_refs_to_replace_with):
        members = self.members
        # loop in reverse order, so removing items 
        # wouldn't change the index before them
        for i in range(len(members) -1, -1, -1):
            member = members[i]
            if member['ref'] == member_ref:
                
                # remove
                member_ref.remove_referrer(self)
                del members[i]
                
                # add the replacing members in the same position
                for j in range(len(member_refs_to_replace_with)):
                    new_way = member_refs_to_replace_with[j]
                    new_member = member.copy()
                    new_member['ref'] = new_way
                    members.insert(i + j, new_member)
                    new_way.add_referrer(self)
                
                # I can't imagine a case where a way is referrenced more than 
                # once by the same relation, but just in case...
                # break
        
        # recalculate str_id, since it depends on the members
        self.str_id = get_str_id(members, self.tags)

# Helper function to get a new ID
def get_new_id():
    return global_id.get_new_id()

def get_str_id(members, tags):
    member_list = []
    for member in members:
        member_list.append(member['type'] + '_' + str(member['ref'].id)+ '_' + member['role'])
    return '_'.join(member_list) + '_' + json.dumps(tags)

def polygon_to_members(ogrgeometry, way_cache, way_tags = {}, node_tags = {}):
    members = []
    if ogrgeometry.GetGeometryCount() == 0:
        raise RuntimeError("Polygon without any ring!")
    elif ogrgeometry.GetGeometryCount() == 1:
        way = way_cache.add_from_ogr(ogrgeometry.GetGeometryRef(0), way_tags, node_tags)
        member = {
            'type': 'way',
            'role': 'outer',
            'ref': way
        }
        members.append(member)
    else:
        # Multipolygon
        way = way_cache.add_from_ogr(ogrgeometry.GetGeometryRef(0), way_tags, node_tags)
        member = {
            'type': 'way',
            'role': 'outer',
            'ref': way
        }
        members.append(member)
        for i in range(1, ogrgeometry.GetGeometryCount()):
            way = way_cache.add_from_ogr(ogrgeometry.GetGeometryRef(i), way_tags, node_tags)
            members.append( {
                'type': 'way',
                'role': 'inner',
                'ref': way
            })
    return members

class RelationCache(object):
    def __init__(self, way_cache):
        self._cache = {}
        self.way_cache = way_cache
    
    def add_from_ogr(self, ogr_polygon, tags, way_tags, node_tags):
        way_cache = self.way_cache
        members = polygon_to_members (ogr_polygon, way_cache, way_tags, node_tags)
        str_id = get_str_id(members, tags)
        if  str_id in self._cache:
            relation = self._cache[str_id]
        else:
            relation = Relation(members, get_new_id(), tags)
            self._cache[str_id] = relation
            for member in members:
                member['ref'].add_referrer(relation)
        return relation
    
    def update(self, str_id):
        cache = self._cache
        if str_id in cache:
            relation = cache[str_id]
            del cache[str_id]
            cache[relation.str_id] = relation