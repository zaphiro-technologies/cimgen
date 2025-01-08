from .Base import BaseClass


def sql_to_pydantic(sql_object, pydantic_class):
    pydantic_attributes = {}
    if isinstance(sql_object, BaseClass):
        sql_dict = sql_object.__dict__
        if sql_object.objectType == "pmu_device":
            sql_dict["Measurements"] = sql_object.Measurements
    else:
        # When querying zaphiro_measurements
        sql_dict = dict(sql_object._mapping)
    for attribute in pydantic_class.__dataclass_fields__:
        value = sql_dict.get(attribute, None)
        if isinstance(value, list):
            transformed_list = []
            for element in value:
                if isinstance(element, BaseClass):
                    transformed_list.append(element.mRID)
                else:
                    transformed_list.append(element)
            value = transformed_list
        if isinstance(value, BaseClass):
            value = value.mRID
        if value is not None:
            pydantic_attributes[attribute] = value
    return pydantic_class(**pydantic_attributes)
