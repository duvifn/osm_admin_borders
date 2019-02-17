class TagMapper(object):
    def get_node_tags(self, feature, layer):
        return {}
    def get_way_tags(self, feature, layer):
        return {}
    def get_relation_tags(self, feature, layer ):
        layer_definition = layer.GetLayerDefn()
        result = {}
        for i in range(layer_definition.GetFieldCount()):
            field_name =  layer_definition.GetFieldDefn(i).GetName()
            field_value = feature.GetField(field_name)
            if field_value is not None:
                result[field_name] = feature.GetField(field_name)
        return result
    
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