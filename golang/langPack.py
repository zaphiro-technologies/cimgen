import logging
import os
import re
from distutils.dir_util import copy_tree
import shutil
import sys
import textwrap
from pathlib import Path
import ast

import chevron

logger = logging.getLogger(__name__)


# This makes sure we have somewhere to write the classes, and
# creates a couple of files the python implementation needs.
# cgmes_profile_info details which uri belongs in each profile.
# We don't use that here because we aren't creating the header
# data for the separate profiles.
def setup(version_path, cgmes_profile_info):  # NOSONAR
    # version_path is actually the output_path

    # Add all hardcoded utils and create parent dir
    dest_dir=Path(version_path)

    if not os.path.exists(dest_dir):
       dest_dir.mkdir()

template_files = [{"filename": "struct_class_template.mustache", "ext": ".go"}]
enum_template_files = [{"filename": "enum_class_template.mustache", "ext": ".go"}]

def location(version):
    version_match = re.search(r'v\d+', version)
    # Check if the version number is found
    if version_match:
        version_number = version_match.group(0)
        return version_number
    return "v0"


base = {"base_class": "", "class_location": location}

def get_class_location(class_name, class_map, version):
    return location(version)

partials = {}

def _primitive_to_data_type(datatype):
    if datatype.lower() == "integer":
        return "int64"
    if datatype.lower() == "boolean":
        return "bool"
    if datatype.lower() == "string":
        return "string"
    if datatype.lower() == "datetime":
        return "string"
    if datatype.lower() == "monthday":
        return "string"
    if datatype.lower() == "date":
        return "string"
    # as of today no CIM model is using only time.
    if datatype.lower() == "time":
        return "string"
    if datatype.lower() == "float":
        return "float64"
    if datatype.lower() == "string":
        return "string"
    else:
    # this actually never happens
        return "float64"

# computes the data type
def _compute_data_type(attribute):
    if "label" in attribute and attribute["label"] == "mRID":
        return "string"
    elif "range" in attribute:
        return "resource"
    elif "dataType" in attribute and "class_name" in attribute:
        # for whatever weird reason String is not created as class from CIMgen
        if is_primitive_class(attribute["class_name"]) or attribute["class_name"] == "String":
            return _primitive_to_data_type(attribute["dataType"].split("#")[1])
        # the assumption is that cim data type e.g. Voltage, ActivePower, always
        # maps to a float
        elif is_cim_data_type_class(attribute["class_name"]):
            return "float64"
        else:
        # this is for example the case for 'StreetAddress.streetDetail'
            return "resource"
    else:
        raise ValueError(f"Cannot parse {attribute} to extract a data type.")

def _ends_with_s(attribute_name):
    return attribute_name.endswith("s")

# called by chevron, text contains the label {{dataType}}, which is evaluated by the renderer (see class template)
def _set_xml(text, render):
    return _get_type_xml_name(text, render)[1]

def _set_type(text, render):
    return _get_type_xml_name(text, render)[0]

def _set_name(text, render):
    return _get_type_xml_name(text, render)[2]

# called by chevron, text contains the label {{dataType}}, which is evaluated by the renderer (see class template)
def _set_instances(text, render):
    instance = None
    try:
        # render(text) returns a python dict. Some fileds might be quoted by '&quot;' instead of '"', making the first evel fail.
        instance = ast.literal_eval(render(text))
    except SyntaxError as se:
        rendered = render(text)
        rendered = rendered.replace("&quot;", '"')
        instance = eval(rendered)
        logger.warning("Exception in evaluating %s : %s . Handled replacing quotes", rendered, se.msg)
    if "label" in instance:
        type_name = instance["type"][instance["type"].find('#')+1:]
        value = type_name + "_" + instance["label"] + ' ' + type_name +' = "' + instance["label"] + '"'
        if "comment" in instance:
            value += " //" + instance["comment"]
        return value
    else:
        return ""

def _upper_case_first_char(str):
    return str[:1].upper() + str[1:] if str else ""

def _get_type_xml_name(text, renderer) -> tuple[str, str, str]:
    # the field {{dataType}} either contains the multiplicity of an attribute if it is a reference or otherwise the
    # datatype of the attribute. If no datatype is set and there is also no multiplicity entry for an attribute, the
    # default value is set to None. The multiplicity is set for all attributes, but the datatype is only set for basic
    # data types. If the data type entry for an attribute is missing, the attribute contains a reference and therefore
    # the default value is either None or [] depending on the multiplicity. See also write_python_files
    # The default will be copied as-is, hence the possibility to have default or
    # default_factory.
    attribute = eval(renderer(text))
    datatype = _compute_data_type(attribute)
    field_type = datatype
    field_xml = ''
    field_name = _upper_case_first_char(attribute["label"])
    if datatype == 'resource':
        field_name = field_name+"Id"
    if "multiplicity" in attribute:
        multiplicity = attribute["multiplicity"]
        if multiplicity in ["M:0..1"]:
            field_type = "*" + datatype
        elif multiplicity in ["M:0..n","M:1..n", "M:2..n"]:
            field_type = "[]" + datatype
            if datatype == 'resource':
                field_name = field_name+"s"
        elif multiplicity in ["M:1"] and attribute['label'] == 'PowerSystemResources':
            # Most probably there is a bug in the RDF that states multiplicity
            # M:1 but should be M:1..N
            field_type = "[]" + datatype
            if datatype == 'resource':
                field_name = field_name+"s"
        else:
            field_type = datatype

    if "label" in attribute and attribute["label"] == "mRID":
        field_xml = '`xml:"ID,attr"`'
    else:
        field_xml = '`xml:"'+attribute["namespace"]+' '+attribute["about"]+'"`'
    return (field_type, field_xml, field_name)


def set_enum_classes(new_enum_classes):
    return


def set_float_classes(new_float_classes):
    return

primitive_classes = {}

def set_primitive_classes(new_primitive_classes):
    for new_class in new_primitive_classes:
        primitive_classes[new_class] = new_primitive_classes[new_class]

def is_primitive_class(name):
    if name in primitive_classes:
        return primitive_classes[name]

cim_data_type_classes = {}

def set_cim_data_type_classes(new_cim_data_type_classes):
    for new_class in new_cim_data_type_classes:
        cim_data_type_classes[new_class] = new_cim_data_type_classes[new_class]

data_classes = {}

def set_data_classes(new_data_classes):
    for new_class in new_data_classes:
        data_classes[new_class] = new_data_classes[new_class]

def is_cim_data_type_class(name):
    if name in cim_data_type_classes:
        return cim_data_type_classes[name]

def has_unit_attribute(attributes):
    for attr in attributes:
        if attr["label"] == "unit":
            return True
    return False

def run_template(version_path, class_details):
    if class_details["is_a_primitive"] is True:
        # Primitives are never used in the in memory representation but only for
        # the schema
        return
    elif class_details["is_a_cim_data_type"] is True:
        # Datatypes based on primitives are never used in the in memory
        # representation but only for the schema
        return
    elif class_details["has_instances"] is True:
        run_template_enum(version_path, class_details, enum_template_files)
    else:
        run_template_schema(version_path, class_details, template_files)

def run_template_enum(version_path, class_details, templates):
    for template_info in templates:
        class_file = Path(version_path, "cgmes", class_details["class_location"],  "enum" + template_info["ext"])
        if not os.path.exists(class_file):
            if not (parent:=class_file.parent).exists():
                if not (super_parent:=parent.parent).exists():
                    super_parent.mkdir()
                parent.mkdir()
            with open(class_file, "w", encoding="utf-8") as file:
                file.write("package " + class_details["class_location"]+"\n")
        with open(class_file, "a", encoding="utf-8") as file:
            template_path = os.path.join(os.getcwd(), "golang/templates", template_info["filename"])
            class_details["setInstances"] = _set_instances
            with open(template_path, encoding="utf-8") as f:
                args = {
                    "data": class_details,
                    "template": f,
                    "partials_dict": partials,
                }
                output = chevron.render(**args)
            file.write(output)

def run_template_schema(version_path, class_details, templates):
    for template_info in templates:
        class_file = Path(version_path, "cgmes", class_details["class_location"],  "data_type" + template_info["ext"])
        if not os.path.exists(class_file):
            if not (parent:=class_file.parent).exists():
                if not (super_parent:=parent.parent).exists():
                    super_parent.mkdir()
                parent.mkdir()
            with open(class_file, "w", encoding="utf-8") as file:
                file.write("package " + class_details["class_location"]+"\n\n")
                file.write("import (\n")
                file.write('    "fmt"\n')
                file.write('    "reflect"\n')
                file.write(")\n\n")
                file.write("type resource string\n")
        with open(class_file, "a", encoding="utf-8") as file:
            template_path = os.path.join(os.getcwd(), "golang/templates", template_info["filename"])
            class_details["setType"] = _set_type
            class_details["setName"] = _set_name
            class_details["setXML"] = _set_xml
            with open(template_path, encoding="utf-8") as f:
                args = {
                    "data": class_details,
                    "template": f,
                    "partials_dict": partials,
                }
                output = chevron.render(**args)
            file.write(output)

def resolve_headers(dest: str, version: str):
    """Add all classes in __init__.py"""

    if match := re.search(r"(?P<num>\d+_\d+_\d+)", version):  # NOSONAR
        version_number = match.group("num").replace("_", ".")
    else:
        raise ValueError(f"Cannot parse {version} to extract a number.")

    package_version = location("v"+version_number)

    dest = Path(dest)/"cgmes"/package_version
    with open(dest / "cgmes.go", "a", encoding="utf-8") as header_file:
        header_file.write(f"package {package_version}\n\n")
        header_file.write('import (\n')
        header_file.write('  "encoding/xml"\n')
        header_file.write(')\n\n')
        header_file.write("type CGMES struct {\n")
        header_file.write('  XMLName  xml.Name `xml:"http://www.w3.org/1999/02/22-rdf-syntax-ns# RDF"`\n')
        header_file.write('  FullModel  FullModel `xml:"http://iec.ch/TC57/61970-552/ModelDescription/1# FullModel"`\n')
        for data_class in data_classes:
            header_file.write('  '+ data_class +' []' + data_class + ' `xml:"' +data_classes[data_class]+' '+ data_class +'"`\n')
        header_file.write("}\n")

    source=Path(__file__).parent/"static"/package_version

    copy_tree(str(source), str(dest))
