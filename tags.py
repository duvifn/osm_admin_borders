class TagMapper(object):
    def __init__(self, layer, translation_module = None):
        self.field_names = get_field_names(layer)
        self.translation_module = translation_module
    def get_node_tags(self, feature, layer, field_dict = None):
        return {}
    def get_way_tags(self, feature, layer, field_dict = None):
        if not field_dict:
            field_dict = get_field_values (feature, self.field_names)
        if self.translation_module:
            return self.translation_module.get_tags(field_dict, 'way')
        return field_dict
    def get_relation_tags(self, feature, layer, field_dict = None):
        if not field_dict:
            field_dict = get_field_values (feature, self.field_names)
        if self.translation_module:
            return self.translation_module.get_tags(field_dict, 'relation')
        return field_dict
    def get_common_value_fields(self, features, layer):
        layer_definition = layer.GetLayerDefn()
        result = {}
        if len(features) > 0:
            feature = features[0]
            for i in range(layer_definition.GetFieldCount()):
                field_name =  layer_definition.GetFieldDefn(i).GetName()
                field_value = feature.GetField(field_name)
                if field_value is not None:
                    result[field_name] = field_value
            for feature in features:
                for i in range(layer_definition.GetFieldCount()):
                    field_name =  layer_definition.GetFieldDefn(i).GetName()
                    value = feature.GetField(field_name)
                    if field_name in result and result[field_name] != value:
                        del result[field_name]

        return result

def get_field_names(layer):
    layer_definition = layer.GetLayerDefn()
    result = []
    for i in range(layer_definition.GetFieldCount()):
        field_name =  layer_definition.GetFieldDefn(i).GetName()
        result.append(field_name)
    return result

def get_field_values(feature, field_names):
    result = {}
    for field_name in field_names:
        field_value = feature.GetField(field_name)
        if field_value is not None:
            result[field_name] = feature.GetField(field_name)
    return result