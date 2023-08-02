import os
import chevron
import logging
import glob
import shutil
import sys

logger = logging.getLogger(__name__)


# This makes sure we have somewhere to write the classes, and
# creates a couple of files the python implementation needs.
# cgmes_profile_info details which uri belongs in each profile.
# We don't use that here because we aren't creating the header
# data for the separate profiles.
def setup(version_path, cgmes_profile_info):
    if not os.path.exists(version_path):
        os.makedirs(version_path)
        _create_init(version_path)
        _copy_files(version_path)


def location(version):
    return "pydantic." + version + ".Base"


base = {"base_class": "Base", "class_location": location}

template_files = [{"filename": "pydantic_class_template.mustache", "ext": ".py"}]
enum_template_files = [{"filename": "pydantic_enum_template.mustache", "ext": ".py"}]

required_profiles = ['EQ']

def get_class_location(class_name, class_map, version):
    # Check if the current class has a parent class
    if class_map[class_name].superClass():
        if class_map[class_name].superClass() in class_map:
            return "pydantic." + version + "." + class_map[class_name].superClass()
        elif (
            class_map[class_name].superClass() == "Base"
            or class_map[class_name].superClass() == None
        ):
            return location(version)
    else:
        return location(version)


partials = {}


# called by chevron, text contains the label {{dataType}}, which is evaluated by the renderer (see class template)
def _set_instances(text, render):
    instance = None
    try:
        instance = eval(render(text))
    except:
        rendered = render(text)
        rendered = rendered.replace('&quot;','"')
        instance = eval(rendered)
    if "label" in instance:
        value = instance["label"] + ' = "' + instance["label"] + '"'
        if "comment" in instance:
            value += " #" + instance["comment"]
        return value
    else:
            return ""

# called by chevron, text contains the label {{dataType}}, which is evaluated by the renderer (see class template)
def _set_attribute(text, render):
    attribute = eval(render(text))

    if is_required_profile(attribute['attr_origin']):
        return attribute['label'] + ":" + _set_data_type(attribute) + _set_default(attribute)
    else:
        return ""

def _set_default(attribute):
    if "range" in attribute and "isFixed" in attribute:
        return " = " + attribute["range"].split("#")[1] + "." + attribute["isFixed"]
    elif "multiplicity" in attribute:
        multiplicity = attribute["multiplicity"]
        if multiplicity in ["M:1", "M:1..1"]:
            return ""
        if multiplicity in ["M:0..1"]:
            return ""
        elif multiplicity in ["M:0..n"] or "M:0.." in multiplicity:
            return ""
        elif multiplicity in ["M:1..n"] or "M:1.." in multiplicity:
            return ""
        else:
            return ""
    else:
        return ""


def _is_primitive(datatype):
    if datatype in ["str", "int", "bool", "float", "date", "time", "datetime"]:
        return True
    else:
        return False


def _compute_data_type(attribute):
    if "label" in attribute and attribute["label"] == "mRID":
        return "uuid.UUID"

    if "dataType" in attribute:
        if attribute["dataType"].startswith("#"):
            datatype = attribute["dataType"].split("#")[1]
            if datatype == "Integer" or datatype == "integer":
                return "int"
            if datatype == "Boolean":
                return "bool"
            if datatype == "String":
                return "str"
            if datatype == "DateTime":
                return "datetime"
            if datatype == "MonthDay":
                return "str" #TO BE FIXED
            if datatype == "Date":
                return "str" #TO BE FIXED
            if datatype == "Time":
                return "time"
            if datatype == "Float":
                return "float"
            if datatype == "String":
                return "str"
            else:
                return "float"
    if "range" in attribute:
        #return "'"+attribute["range"].split("#")[1]+"'"
        return attribute["range"].split("#")[1]

def _set_data_type(attribute):

    datatype = _compute_data_type(attribute)

    if "multiplicity" in attribute:
        multiplicity = attribute["multiplicity"]
        if multiplicity in ["M:1", "M:1..1", ""]:
            return datatype
        if multiplicity in ["M:0..1"]:
            return "Optional[" + datatype + "]"
        elif multiplicity in ["M:0..n"] or "M:0.." in multiplicity:
            return "Optional[List[" + datatype + "]]"
        elif multiplicity in ["M:1..n"] or "M:1.." in multiplicity:
            return "List[" + datatype + "]"
        else:
            return "List[" + datatype + "]"
    else:
        return datatype


# called by chevron, text contains the label {{dataType}}, which is evaluated by the renderer (see class template)
def _set_validator(text, render):
    attribute = eval(render(text))

    datatype = _compute_data_type(attribute)

    if not _is_primitive(datatype) and is_required_profile(attribute['attr_origin']):
        return (
            "val_"
            + attribute['label']
            + '_wrap = field_validator("'
            + attribute['label']
            + '", mode="wrap")(cyclic_references_validator)'
        )
    else:
        return ""


def set_enum_classes(new_enum_classes):
    return


def set_float_classes(new_float_classes):
    return


def has_unit_attribute(attributes):
    for attr in attributes:
        if attr['label'] == 'unit':
            return True
    return False


def is_required_profile(class_origin):
    for origin in class_origin:
        if origin['origin'] in required_profiles:
            return True
    return False

def run_template(version_path, class_details):
    if (class_details["class_name"] in ["Float", "Integer", "String", "Boolean", "Date", "DateTime", "MonthDay", "PositionPoint", "Decimal"]) or class_details["is_a_float"] == True or "Version" in class_details["class_name"] or has_unit_attribute(class_details["attributes"]) or not is_required_profile(class_details['class_origin']):
        return
    elif class_details["has_instances"] == True:
        run_template_enum(version_path, class_details, enum_template_files)
    else:
        run_template_schema(version_path, class_details, template_files)


def run_template_enum(version_path, class_details, templates):
    for template_info in templates:
        class_file = os.path.join(
                version_path, "enum" + template_info["ext"]
        )
        if not os.path.exists(class_file):
            with open(class_file, "w") as file:
                header_file_path = os.path.join(
                    os.getcwd(), "pydantic", "enum_header.py"
                )
                header_file = open(header_file_path, 'r')
                file.write(header_file.read())
        with open(class_file, "a") as file:
            template_path = os.path.join(
                os.getcwd(), "pydantic/templates", template_info["filename"]
            )
            class_details["setInstances"] = _set_instances
            with open(template_path) as f:
                args = {
                    "data": class_details,
                    "template": f,
                    "partials_dict": partials,
                }
                output = chevron.render(**args)
            file.write(output)


def run_template_schema(version_path, class_details, templates):
    for template_info in templates:
        class_file = os.path.join(
            version_path, "schema" + template_info["ext"]
        )
        if not os.path.exists(class_file):
            with open(class_file, "w") as file:
                schema_file_path = os.path.join(
                    os.getcwd(), "pydantic", "schema_header.py"
                )
                schema_file = open(schema_file_path, 'r')
                file.write(schema_file.read())
        with open(class_file, "a") as file:
            template_path = os.path.join(
                os.getcwd(), "pydantic/templates", template_info["filename"]
            )
            class_details["setAttribute"] = _set_attribute
            class_details["setValidator"] = _set_validator
            with open(template_path) as f:
                args = {
                    "data": class_details,
                    "template": f,
                    "partials_dict": partials,
                }
                output = chevron.render(**args)
            file.write(output)


def _create_init(path):
    init_file = path + "/__init__.py"
    with open(init_file, "w"):
        pass


# creates the Base class file, all classes inherit from this class
def _copy_files(path):
    shutil.copy(os.path.join(
                os.getcwd(), "pydantic/Base.py"), path + "/Base.py")
    shutil.copy(os.path.join(
                os.getcwd(), "pydantic/util.py"), path + "/util.py")


def resolve_headers(path):
    pass
