from datetime import datetime
import json
import xml.etree.ElementTree as etree
import global_id

class Node(object):

    def __init__(self, lon, lat, node_id, digits_of_precision, tags = {}):
        self.id = node_id
        self.lon = lon
        self.lat = lat
        self.tags = tags
        self.str_id = get_str_id(lon, lat, digits_of_precision)
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
        # Build a dict for optional settings
        attributes = {}
        if options.add_version:
            attributes.update({'version':'1'})

        if options.addTimestamp:
            attributes.update({'timestamp':datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')})

        
        xmlattrs = {'visible':'true','id':str(self.id), 'lat':str(self.lat), 'lon':str(self.lon)}
        xmlattrs.update(attributes)

        xmlobject = etree.Element('node', xmlattrs)
        for (key, value) in self.tags.items():
            tag = etree.Element('tag', {'k':str(key), 'v':str(value)})
            xmlobject.append(tag)
        return xmlobject
        

# Helper function to get a new ID
def get_new_id():
    return global_id.get_new_id()

def get_str_id(lon, lat, digits_of_precision):
    return format(lon, '.'+str(digits_of_precision)+'f') + '_' + format(lat, '.'+str(digits_of_precision)+'f')

class NodeCache(object):
    def __init__(self, options):
        self._cache = {}
        self.digits_of_precision = options.digits_of_precision
     
    def add_from_touple(self, touple, tags):
        lon = touple[0]
        lat = touple[1]
        str_id = get_str_id(lon, lat, self.digits_of_precision)
        if  str_id in self._cache:
            nd = self._cache[str_id]
            return self._cache[str_id]
        else:
            nd = Node(lon, lat, get_new_id(), self.digits_of_precision, tags)
            self._cache[str_id] = nd
            return nd