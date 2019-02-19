def get_as_is(field_name, tag_name, field_dict, result_dict):
    if field_name in field_dict and field_dict[field_name] is not None:
        result_dict[tag_name] = field_dict[field_name]

def get_tags(field_dict, element_type):
    result = {}
    if element_type == 'relation':
        get_as_is('name', 'name', field_dict, result)
        get_as_is('name_en', 'name:en', field_dict, result)
        get_as_is('id', 'source_id', field_dict, result)
        result['boundary'] = 'administrative'
        result['type'] = 'boundary'
        result['source'] = 'osm'
    elif element_type == 'way':
        result['boundary'] = 'administrative'
        result['source'] = 'osm'
    return result