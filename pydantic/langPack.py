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
    instance = eval(render(text))
    if "label" in instance:
        value = instance["label"] + ' = "' + instance["label"] + '"'
        if "comment" in instance:
            value += " #" + instance["comment"]
        return value
    else:
        return ""


# called by chevron, text contains the label {{dataType}}, which is evaluated by the renderer (see class template)
def _set_imports(text, render):
    rendered = render(text)
    res = None
    try:
        res = eval(rendered)
    finally:
        result = ""
        classes = set()
        if res:
            for val in res:
                if "range" in val:
                    classes.add(val["range"].split("#")[1])
        for val in classes:
            result += "from ." + val + " import " + val + "\n"
        return result


# called by chevron, text contains the label {{dataType}}, which is evaluated by the renderer (see class template)
def _set_default(text, render):
    attribute = eval(render(text))

    if "range" in attribute and "isFixed" in attribute:
        return " = " + attribute["range"].split("#")[1] + "." + attribute["isFixed"]
    if (
        "multiplicity" in attribute
        and attribute["multiplicity"] in ["M:0..n"]
        and "range" in attribute
    ):
        return " = None"
    if "range" not in attribute and "isFixed" in attribute:
        return ' = "' + attribute["isFixed"] + '"'
    return ""


def _is_primitive(datatype):
    if datatype in ["str", "int", "bool", "float"]:
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
                return "str"
            if datatype == "Date":
                return "str"
            if datatype == "String":
                return "str"
            else:
                return "float"
    if "range" in attribute:
        return attribute["range"].split("#")[1]


# called by chevron, text contains the label {{dataType}}, which is evaluated by the renderer (see class template)
def _set_data_type(text, render):
    attribute = eval(render(text))

    datatype = _compute_data_type(attribute)

    if "multiplicity" in attribute:
        multiplicity = attribute["multiplicity"]
        if multiplicity in ["M:1..1", ""]:
            return datatype
        if multiplicity in ["M:0..1"]:
            return "Optional[" + datatype + "]"
        elif multiplicity in ["M:0..n"] or "M:0.." in multiplicity:
            return "Optional[List[" + datatype + "]]"
        elif multiplicity in ["M:1", "M:1..n"] or "M:1.." in multiplicity:
            return "List[" + datatype + "]"
        else:
            return "List[" + datatype + "]"
    else:
        return datatype


# called by chevron, text contains the label {{dataType}}, which is evaluated by the renderer (see class template)
def _set_validator(text, render):
    attribute = eval(render(text))

    datatype = _compute_data_type(attribute)

    if "multiplicity" in attribute and not _is_primitive(datatype):
        multiplicity = attribute["multiplicity"]
        if (multiplicity in ["M:0..n"] or "M:0.." in multiplicity) or (
            multiplicity in ["M:1", "M:1..n"] or "M:1.." in multiplicity
        ):
            return (
                "val_"
                + datatype
                + '_wrap = field_validator("'
                + datatype
                + '", mode="wrap")(cyclic_references_validator)'
            )
        else:
            return ""
    else:
        return ""


def set_enum_classes(new_enum_classes):
    return


def set_float_classes(new_float_classes):
    return


def run_template(version_path, class_details):
    if class_details["class_name"] in ["Float", "Integer", "String", "Boolean", "Date"]:
        templates = []
    elif class_details["has_instances"] == True:
        templates = enum_template_files
    else:
        templates = template_files

    for template_info in templates:
        class_file = os.path.join(
            version_path, class_details["class_name"] + template_info["ext"]
        )
        if not os.path.exists(class_file):
            with open(class_file, "w") as file:
                template_path = os.path.join(
                    os.getcwd(), "pydantic/templates", template_info["filename"]
                )
                class_details["setDefault"] = _set_default
                class_details["setDataType"] = _set_data_type
                class_details["setImports"] = _set_imports
                class_details["setInstances"] = _set_instances
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
    shutil.copy("pydantic/Base.py", path + "/Base.py")
    shutil.copy("pydantic/PositionPoint.py", path + "/PositionPoint.py")
    shutil.copy("pydantic/util.py", path + "/util.py")


def resolve_headers(path):
    filenames = glob.glob(path + "/*.py")
    include_names = []
    for filename in filenames:
        include_names.append(os.path.splitext(os.path.basename(filename))[0])
    with open(path + "/__init__.py", "w") as header_file:
        for include_name in include_names:
            header_file.write(
                "from "
                + "."
                + include_name
                + " import "
                + include_name
                + " as "
                + include_name
                + "\n"
            )
        header_file.close()
