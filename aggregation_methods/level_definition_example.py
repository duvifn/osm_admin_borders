levels = [
    {
        'field_to_aggregate_by' : 'id',
        'admin_level' : 4,
        'deepest' : True
    },
    {
        'field_to_aggregate_by' : 'na',
        'admin_level' : 3,
        'deepest' : False
    }]

def divide_features_by_field(layer, field_name):
    result = {}
    for feature in layer:
        try:
            field_value = feature.GetField(field_name)
        except Exception as error:
            print('Can\'t read field: ' + field_name + ' ' + repr(error))
            raise error
        if field_value is not None:
            value_features = result.setdefault(field_value, [])
            value_features.append(feature)
    layer.ResetReading()
    return result

def get_level_definitions(layer):
    layer.ResetReading()
    level_definitions = []

    for level in levels:
        level_def = {
            'deepest': level['deepest'],
            'admin_level' : level['admin_level'],
            'features': divide_features_by_field(layer, level['field_to_aggregate_by'])
        }
        level_definitions.append(level_def)
    return level_definitions