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
    return "sqlalchemy." + version + ".Base"


base = {"base_class": "Base", "class_location": location}

template_files = [{"filename": "sqlalchemy_class_template.mustache", "ext": ".py"}]

required_profiles = ["EQ"]

enum_classes = {}

def get_class_location(class_name, class_map, version):
    # Check if the current class has a parent class
    if class_map[class_name].superClass():
        if class_map[class_name].superClass() in class_map:
            return "sqlalchemy." + version + "." + class_map[class_name].superClass()
        elif (
            class_map[class_name].superClass() == "Base"
            or class_map[class_name].superClass() == None
        ):
            return location(version)
    else:
        return location(version)


partials = {}

def _lower_case_first_char(str):
    return str[:1].lower() + str[1:] if str else ''


def _relationship_type(attribute):
    if "multiplicity" in attribute and "inverseMultiplicity" in attribute:
        if attribute["multiplicity"] in ['M:0..1', "M:1", "M:1..1"] and  attribute["inverseMultiplicity"] in ['M:0..1', "M:1", "M:1..1"]:
            return "ONE-TO-ONE"
        elif attribute["multiplicity"] in ['M:0..1', "M:1", "M:1..1"] and  attribute["inverseMultiplicity"] in ['M:0..n', "M:1..n", 'M:0..2']:
            return "ONE-TO-MANY"
        elif attribute["multiplicity"] in ['M:0..n', "M:1..n", 'M:0..2'] and  attribute["inverseMultiplicity"] in ['M:0..n', "M:1..n"]:
            return "MANY-TO-MANY"
        elif attribute["multiplicity"] in ['M:0..n', "M:1..n", 'M:0..2'] and  attribute["inverseMultiplicity"] in ['M:0..1', "M:1", "M:1..1", 'M:0..2']:
            return "MANY-TO-ONE"
        else:
            return "Boh"
    else:
        return None

# called by chevron, text contains the label {{dataType}}, which is evaluated by the renderer (see class template)
def _set_attribute(text, render):
    attribute = eval(render(text))
    datatype = _compute_data_type(attribute)

    if is_required_profile(attribute["attr_origin"]) and _is_primitive(datatype):
        return (
            _lower_case_first_char(attribute["label"])
            + ": Mapped["
            + _set_data_type(attribute)
            + "]"
            + _set_column_primitive(attribute)
        )
    elif is_required_profile(attribute["attr_origin"]) and not _is_primitive(datatype) and "multiplicity" in attribute:
        relationship_type = _relationship_type(attribute)

        if relationship_type == "ONE-TO-MANY":
            return (
                 _lower_case_first_char(attribute["label"])
                + '_id'
                + ': Mapped[str] = mapped_column(ForeignKey(column="'
                + _get_table_name( attribute["class_name"] )
                + '.mRID",'
                + 'name="fk_'
                + _get_table_name(  attribute["class_name"] )
                + '_'
                + _get_table_name( attribute["domain"] )
                + '_'
                + _get_table_name( attribute["label"] )
                + '",use_alter=True)'
                + ')\n    '
                + _lower_case_first_char(attribute["label"])
                + ': Mapped['
                + _set_data_type(attribute)
                + ']'
                + _set_column_relationship(attribute, relationship_type)
            )
        if relationship_type == "MANY-TO-ONE":
            return (
                _lower_case_first_char(attribute["label"])
                + ": Mapped["
                + _set_data_type(attribute)
                + "]"
                + _set_column_relationship(attribute, relationship_type)
                )
        else:
            return ''
        # if multiplicity in ["M:1", "M:1..1", "M:0..1"] and not multiplicity_by_name:
        #     return (
        #          _lower_case_first_char(attribute["label"])
        #         + '_id'
        #         + ': Mapped[str] = mapped_column(ForeignKey(column="'
        #         + _get_table_name( attribute["class_name"] )
        #         + '.mRID",'
        #         + 'name="fk_'
        #         + _get_table_name(  attribute["class_name"] )
        #         + '_'
        #         + _get_table_name( attribute["domain"] )
        #         + '_'
        #         + _get_table_name( attribute["label"] )
        #         + '",use_alter=True)'
        #         + ')\n    '
        #         + _lower_case_first_char(attribute["label"])
        #         + ': Mapped['
        #         + _set_data_type(attribute)
        #         + ']'
        #         + _set_column_relationship(attribute, multiplicity)
        #     )
        # # elif multiplicity in ["M:0..1"] and not multiplicity_by_name:
        # #     return (
        # #         _lower_case_first_char(attribute["label"])
        # #         + ': Mapped['
        # #         + _set_data_type(attribute)
        # #         + ']'
        # #         + _set_column_relationship(attribute, multiplicity)
        # #     )
        # else:
        #     return (
        #         _lower_case_first_char(attribute["label"])
        #         + ": Mapped["
        #         + _set_data_type(attribute)
        #         + "]"
        #         + _set_column_relationship(attribute, multiplicity)
        #     )
    else:
        return ""


def _set_column_primitive(attribute):
    if "label" in attribute and attribute["label"] == "mRID":
        return ""
    elif attribute['class_name'] in enum_classes:
        return " = mapped_column(String(255))"
    elif "dataType" in attribute:
        if attribute["dataType"].startswith("#"):
            datatype = attribute["dataType"].split("#")[1]
            if datatype == "Integer" or datatype == "integer":
                return " = mapped_column(Integer)"
            if datatype == "Boolean":
                return " = mapped_column(Boolean)"
            if datatype == "String":
                return " = mapped_column(String(255))"
            if datatype == "DateTime":
                return " = mapped_column(DateTime)"
            if datatype == "MonthDay":
                return " = mapped_column(String(255))"  # TO BE FIXED
            if datatype == "Date":
                return " = mapped_column(String(255))"  # TO BE FIXED
            if datatype == "Time":
                return " = mapped_column(String(255))"  # TO BE FIXED
            if datatype == "Float":
                return  " = mapped_column(Float)"
            else:
                return " = mapped_column(Float)"
        else:
            return ""
    else:
        return ""

def _set_column_relationship(attribute, relationship_type):
    back_populate = _lower_case_first_char(attribute["inverseRole"].split(".")[1])
    if relationship_type == "ONE-TO-MANY":
        return '  =  relationship(back_populates="'+back_populate+'")'
    elif relationship_type == "MANY-TO-ONE":
        return '  =  relationship(back_populates="'+back_populate+'")'
    # if multiplicity in ["M:1", "M:1..1", "M:0..1"]:
    #     return '  =  relationship(back_populates="'+back_populate+'", remote_side=[mRID], foreign_keys=['+ _lower_case_first_char(attribute["label"])+'_id])'
    # # elif multiplicity in ["M:0..1"]:
    # #     return '  =  relationship(back_populates="'+back_populate+'")'
    # else:
    # return (
    #     '  =  relationship('
    #     + 'primaryjoin="'
    #     + attribute["domain"]
    #     + '.mRID=='
    #     + attribute["class_name"]
    #     + '.'
    #     + back_populate
    #     + '_id'
    #     + '",back_populates="'
    #     + back_populate
    #     + '", post_update=True)'
    #     )
    return ''

def _is_primitive(datatype):
    if datatype in ["str", "int", "bool", "float", "date", "time", "datetime"]:
        return True
    else:
        return False


def _compute_data_type(attribute):
    if "label" in attribute and attribute["label"] == "mRID":
        return "str"

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
                return "str"  # TO BE FIXED
            if datatype == "Date":
                return "str"  # TO BE FIXED
            if datatype == "Time":
                return "time"
            if datatype == "Float":
                return "float"
            if datatype == "String":
                return "str"
            else:
                return "float"
    if "range" in attribute:
        if attribute['class_name'] in enum_classes:
            return "str"
        else:
            return attribute["range"].split("#")[1]


def _ends_with_s(attribute_name):
    return attribute_name.endswith("s")


def _set_data_type(attribute):
    datatype = _compute_data_type(attribute)
    multiplicity_by_name = _ends_with_s(attribute["label"])

    if "multiplicity" in attribute:
        multiplicity = attribute["multiplicity"]
        if multiplicity in ["M:1..1"]:
            return datatype
        if multiplicity in ["M:1"] and not multiplicity_by_name:
            return datatype
        if multiplicity in ["M:0..1"]:
            return "Optional[" + datatype + "]"
        elif multiplicity in ["M:0..n"] or "M:0.." in multiplicity:
            return "Optional[List[" + datatype + "]]"
        elif multiplicity in ["M:1..n"] or "M:1.." in multiplicity:
            return "List[" + datatype + "]"
        elif multiplicity in ["M:1"] and multiplicity_by_name:
            # Most probably there is a bug in the RDF that states multiplicity
            # M:1 but should be M:1..N
            return "List[" + datatype + "]"
        elif multiplicity in [""]:
            return datatype
        else:
            return "List[" + datatype + "]"
    else:
        return datatype

def _set_mapper(text, render):
    className = render(text)
    tableName =  _get_table_name(className)
    return ('__mapper_args__ = {\n'
    + '      "polymorphic_identity": "' + tableName + '",\n'
    + '      "polymorphic_on": "objectType",\n'
    + '    }')

def _set_mRID(text, render):
    className = render(text)
    if className and not "," in className:
        return ('mRID: Mapped[str] = mapped_column(String(255), primary_key=True)'
        )
    elif className and "," in className:
        class1 = className.split(",")[0]
        class2 = className.split(",")[1]
        return ('mRID: Mapped[str] = mapped_column(String(255),'
                + 'ForeignKey(column="'
                + _get_table_name( class1 )
                + '.mRID", '
                + 'name="fk_'+_get_table_name( class2 )+'_'+ _get_table_name( class1 )
                + '"),'
                + 'primary_key=True)'
        )
    else:
        return ""
    
def _get_table_name( className ):
    import re
    return re.sub('([A-Z]{1})', r'_\1',className).lower()[1:]

def _set_table_name(text, render):
    className = render(text)
    return '__tablename__ = "' + _get_table_name(className) +'"'

def set_enum_classes(new_enum_classes):
    global enum_classes
    enum_classes = new_enum_classes

def set_float_classes(new_float_classes):
    return


def has_unit_attribute(attributes):
    for attr in attributes:
        if attr["label"] == "unit":
            return True
    return False


def is_required_profile(class_origin):
    for origin in class_origin:
        if origin["origin"] in required_profiles:
            return True
    return False


def run_template(version_path, class_details):
    if (
        (
            class_details["class_name"]
            in [
                "Float",
                "Integer",
                "String",
                "Boolean",
                "Date",
                "DateTime",
                "MonthDay",
                "PositionPoint",
                "Decimal",
            ]
        )
        or class_details["is_a_float"] == True
        or "Version" in class_details["class_name"]
        or has_unit_attribute(class_details["attributes"])
        or not is_required_profile(class_details["class_origin"])
    ):
        return
    elif class_details["has_instances"] == True:
        return
    else:
        run_template_schema(version_path, class_details, template_files)


def run_template_schema(version_path, class_details, templates):
    for template_info in templates:
        class_file = os.path.join(version_path, "schema" + template_info["ext"])
        if not os.path.exists(class_file):
            with open(class_file, "w") as file:
                schema_file_path = os.path.join(
                    os.getcwd(), "sqlalchemy", "schema_header.py"
                )
                schema_file = open(schema_file_path, "r")
                file.write(schema_file.read())
        with open(class_file, "a") as file:
            template_path = os.path.join(
                os.getcwd(), "sqlalchemy/templates", template_info["filename"]
            )
            class_details["needsMapper"] = len(class_details["sub_classes"]) > 0 or class_details["sub_class_of"] != "Base"
            class_details["needsId"] = class_details["sub_class_of"] == "Base"
            class_details["needsType"] = class_details["sub_class_of"] == "Base" and len(class_details["sub_classes"]) > 0
            class_details["setAttribute"] = _set_attribute
            class_details["setTableName"] = _set_table_name
            class_details["setMapper"] = _set_mapper
            class_details["setMRID"] = _set_mRID
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
    shutil.copy(os.path.join(os.getcwd(), "sqlalchemy/Base.py"), path + "/Base.py")
    shutil.copy(os.path.join(os.getcwd(), "sqlalchemy/util.py"), path + "/util.py")


def resolve_headers(path):
    pass
