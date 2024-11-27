import os
import re
import chevron
import logging
import shutil
from pathlib import Path
from importlib.resources import files

logger = logging.getLogger(__name__)


# This makes sure we have somewhere to write the classes, and
# creates a couple of files the python implementation needs.
# cgmes_profile_info details which uri belongs in each profile.
# We don't use that here because we aren't creating the header
# data for the separate profiles.
def setup(output_path: str, cgmes_profile_details: list, cim_namespace: str):
    if not os.path.exists(output_path):
        os.makedirs(output_path)
        _create_init(output_path)
        _copy_files(output_path)


def location(version):
    return "sqlalchemy." + version + ".Base"


base = {"base_class": "Base", "class_location": location}

template_files = {"filename": "sqlalchemy_class_template.mustache", "ext": ".py"}

required_profiles = ["EQ", "GL"]

enum_classes = {}

one_to_one = {}

association_tables = {}

partials = {}


def _update_one_to_one(new_one_to_one):
    global one_to_one
    one_to_one.update(new_one_to_one)


def _update_association_tables(new_association_tables):
    global association_tables
    association_tables.update(new_association_tables)


def get_class_location(class_name, class_map, version):
    # Check if the current class has a parent class
    if class_map[class_name].superClass():
        if class_map[class_name].superClass() in class_map:
            return "sqlalchemy." + version + "." + class_map[class_name].superClass()
        elif class_map[class_name].superClass() == "Base" or class_map[class_name].superClass() is None:
            return location(version)
    else:
        return location(version)


def _relationship_type(attribute):
    if "multiplicity" in attribute and "inverseMultiplicity" in attribute:
        multiplicity_by_name = _ends_with_s(attribute["label"])
        inverse_multiplicy_by_name = _ends_with_s(attribute["inverseRole"])
        if (
            attribute["multiplicity"] in ["M:1"]
            and multiplicity_by_name
            and attribute["inverseMultiplicity"] in ["M:0..1", "M:1", "M:1..1"]
        ):
            return "MANY-TO-ONE"
        elif (
            attribute["multiplicity"] in ["M:0..1", "M:1", "M:1..1"]
            and attribute["inverseMultiplicity"] in ["M:1"]
            and inverse_multiplicy_by_name
        ):
            return "ONE-TO-MANY"
        if attribute["multiplicity"] in ["M:0..1", "M:1", "M:1..1"] and attribute["inverseMultiplicity"] in [
            "M:0..1",
            "M:1",
            "M:1..1",
        ]:
            name = attribute["about"]
            reverse = attribute["inverseRole"]
            if name in one_to_one:
                # duplicated but father (should be impossible...)
                return "ONE-TO-ONE-FATHER"
            elif reverse in one_to_one:
                # son
                return "ONE-TO-ONE-SON"
            else:
                # father
                temp = {}
                temp[name] = attribute
                _update_one_to_one(temp)
                return "ONE-TO-ONE-FATHER"
        elif attribute["multiplicity"] in ["M:0..1", "M:1", "M:1..1"] and attribute["inverseMultiplicity"] in [
            "M:0..n",
            "M:1..n",
            "M:0..2",
        ]:
            return "ONE-TO-MANY"
        elif attribute["multiplicity"] in ["M:0..n", "M:1..n", "M:0..2"] and attribute["inverseMultiplicity"] in [
            "M:0..n",
            "M:1..n",
        ]:
            return "MANY-TO-MANY"
        elif attribute["multiplicity"] in ["M:0..n", "M:1..n", "M:0..2"] and attribute["inverseMultiplicity"] in [
            "M:0..1",
            "M:1",
            "M:1..1",
            "M:0..2",
        ]:
            return "MANY-TO-ONE"
        else:
            return None
    else:
        return None


def _needs_many_to_many(class_details):
    for attribute in class_details["attributes"]:
        if _relationship_type(attribute) == "MANY-TO-MANY":
            return True
    return False


def _set_association_table(text, render):
    attributes = eval(render(text))
    association = ""
    for attribute in attributes:
        if _relationship_type(attribute) == "MANY-TO-MANY":
            new_table_name = attribute["domain"] + "To" + attribute["range"].split("#")[1]
            new_inverse_table_name = attribute["range"].split("#")[1] + "To" + attribute["domain"]
            if new_table_name not in association_tables and new_inverse_table_name not in association_tables:
                temp = {}
                temp[new_table_name] = attribute
                _update_association_tables(temp)
                table_name = _get_table_name(new_table_name)
                association += (
                    table_name
                    + ' = Table("'
                    + table_name
                    + '", Base.metadata, '
                    + 'Column("'
                    + _get_table_name(attribute["domain"])
                    + '_mRID", ForeignKey("'
                    + _get_table_name(attribute["domain"])
                    + '.mRID"), primary_key=True),'
                    + 'Column("'
                    + _get_table_name(attribute["range"].split("#")[1])
                    + '_mRID", ForeignKey("'
                    + _get_table_name(attribute["range"].split("#")[1])
                    + '.mRID"), primary_key=True))\n'
                )
    return association


# called by chevron, text contains the label {{dataType}}, which is evaluated by the renderer (see class template)
def _set_attribute(text, render):
    attribute = eval(render(text))

    if is_required_profile(attribute["attr_origin"]) and (
        attribute["is_primitive_attribute"] or attribute["is_datatype_attribute"] or attribute["is_enum_attribute"]
    ):
        return attribute["label"] + ": Mapped[" + _set_data_type(attribute) + "]" + _set_column_primitive(attribute)
    elif (
        is_required_profile(attribute["attr_origin"])
        and not attribute["is_primitive_attribute"]
        and "multiplicity" in attribute
    ):
        relationship_type = _relationship_type(attribute)

        if relationship_type == "ONE-TO-MANY" or relationship_type == "ONE-TO-ONE-SON":
            mapper_1 = "str"
            mapper_2 = _set_data_type(attribute)
            if attribute["multiplicity"] in ["M:0..1"]:
                mapper_1 = "str|None"
            return (
                attribute["label"]
                + ": Mapped["
                + mapper_1
                + '] = mapped_column(ForeignKey(column="'
                + _get_table_name(attribute["attribute_class"])
                + '.mRID",'
                + 'name="fk_'
                + _get_table_name(attribute["attribute_class"])
                + "_"
                + _get_table_name(attribute["domain"])
                + "_"
                + _get_table_name(attribute["label"])
                + '",use_alter=True)'
                + ")\n    "
                + "_"
                + attribute["label"]
                + ": Mapped["
                + mapper_2
                + "]"
                + _set_column_relationship(attribute, relationship_type)
            )
        elif relationship_type == "MANY-TO-ONE" or relationship_type == "ONE-TO-ONE-FATHER":
            return (
                attribute["label"]
                + ": Mapped["
                + _set_data_type(attribute)
                + "]"
                + _set_column_relationship(attribute, relationship_type)
            )
        elif relationship_type == "MANY-TO-MANY":
            return (
                attribute["label"]
                + ": Mapped["
                + _set_data_type(attribute)
                + "]"
                + _set_column_relationship(attribute, relationship_type)
            )
        else:
            return ""
    else:
        return ""


def _set_column_primitive(attribute):
    if attribute.get("label", "") == "mRID":
        return ""
    elif attribute["is_enum_attribute"]:
        return " = mapped_column(String(255))"
    elif "dataType" in attribute:
        if attribute["dataType"].startswith("#"):
            datatype = attribute["dataType"].split("#")[1]
            if datatype == "Integer" or datatype == "integer":
                return " = mapped_column(Integer)"
            if datatype == "Boolean":
                return " = mapped_column(Boolean, default=False)"
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
                return " = mapped_column(Float)"
            else:
                return " = mapped_column(Float)"
        else:
            return ""
    else:
        return ""


def _set_column_relationship(attribute, relationship_type):
    back_populate = attribute["inverseRole"].split(".")[1]
    if relationship_type == "ONE-TO-MANY" or relationship_type == "ONE-TO-ONE-SON":
        return ' = relationship(back_populates="' + back_populate + '", foreign_keys=[' + attribute["label"] + "])"
    elif relationship_type == "MANY-TO-ONE" or relationship_type == "ONE-TO-ONE-FATHER":
        return (
            " = relationship("
            + 'primaryjoin="'
            + attribute["domain"]
            + "Class"
            + ".mRID=="
            + attribute["attribute_class"]
            + "Class"
            + "."
            + back_populate
            + '",back_populates="'
            + "_"
            + back_populate
            + '", post_update=True)'
        )
    elif relationship_type == "MANY-TO-MANY":
        new_table_name = attribute["domain"] + "To" + attribute["range"].split("#")[1]
        new_inverse_table_name = attribute["range"].split("#")[1] + "To" + attribute["domain"]
        secondary_table = ""
        if new_table_name in association_tables:
            secondary_table = _get_table_name(new_table_name)
        elif new_inverse_table_name in association_tables:
            secondary_table = _get_table_name(new_inverse_table_name)
        return " = relationship(" + "secondary=" + secondary_table + ', back_populates="' + back_populate + '")'
    else:
        return ""


def _compute_data_type(attribute):
    if "label" in attribute and attribute["label"] == "mRID":
        return "str"

    if attribute["is_primitive_attribute"]:
        if attribute["dataType"].startswith("#"):
            datatype = attribute["dataType"].split("#")[1]
            if datatype == "Integer":
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
            if datatype == "String":
                return "str"
            else:
                return "float"
    elif attribute["is_datatype_attribute"]:
        return "float"
    elif attribute["is_enum_attribute"]:
        return "str"
    else:
        return attribute["attribute_class"]


def _ends_with_s(attribute_name):
    return attribute_name.endswith("s")


def _set_data_type(attribute):
    datatype = _compute_data_type(attribute)
    if datatype == attribute["attribute_class"]:
        datatype += "Class"
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
    tableName = _get_table_name(className)
    return (
        "__mapper_args__ = {\n"
        + '      "polymorphic_identity": "'
        + tableName
        + '",\n'
        + '      "polymorphic_on": "objectType",\n'
        + "    }"
    )


def _set_mRID(text, render):
    className = render(text)
    if className and "," not in className:
        return "mRID: Mapped[str] = mapped_column(String(255), primary_key=True)"
    elif className and "," in className:
        class1 = className.split(",")[0]
        class2 = className.split(",")[1]
        return (
            "mRID: Mapped[str] = mapped_column(String(255),"
            + 'ForeignKey(column="'
            + _get_table_name(class1)
            + '.mRID", '
            + 'name="fk_'
            + _get_table_name(class2)
            + "_"
            + _get_table_name(class1)
            + '"),'
            + "primary_key=True)"
        )
    else:
        return ""


def _get_table_name(className):
    return re.sub("([A-Z]{1})", r"_\1", className).lower()[1:]


def _set_table_name(text, render):
    className = render(text)
    return '__tablename__ = "' + _get_table_name(className) + '"'


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
    # for attribute in class_details["attributes"]:
    #     attribute["label"] = _lower_case_first_char(attribute["label"])
    if (
        class_details["is_a_primitive_class"]
        or class_details["is_a_datatype_class"]
        or "Version" in class_details["class_name"]
        or has_unit_attribute(class_details["attributes"])
        or not is_required_profile(class_details["class_origin"])
    ):
        return
    elif class_details["is_an_enum_class"]:
        return
    else:
        run_template_schema(version_path, class_details, template_files)


def run_template_schema(version_path, class_details, templates):
    class_file = os.path.join(version_path, "schema" + templates["ext"])
    if not os.path.exists(class_file):
        with open(class_file, "w") as file:
            schema_file_path = os.path.join(os.getcwd(), "cimgen", "languages", "sqlalchemy", "schema_header.py")
            schema_file = open(schema_file_path, "r")
            file.write(schema_file.read())

    # class_details["setImports"] = _setImports(class_details)
    class_details["setAssociationTable"] = _set_association_table
    class_details["needsManyToMany"] = _needs_many_to_many(class_details)
    class_details["needsMapper"] = len(class_details["sub_classes"]) > 0 or class_details["sub_class_of"] != "Base"
    class_details["needsId"] = class_details["sub_class_of"] == "Base"
    class_details["needsType"] = class_details["sub_class_of"] == "Base" and len(class_details["sub_classes"]) > 0
    class_details["setAttribute"] = _set_attribute
    class_details["setTableName"] = _set_table_name
    class_details["setMapper"] = _set_mapper
    class_details["setMRID"] = _set_mRID
    resource_file = _create_file(version_path, class_details, templates)
    _write_templated_file(resource_file, class_details, templates["filename"])


def _create_file(output_path, class_details, template) -> str:
    resource_file = Path(output_path) / ("schema" + template["ext"])
    # ("schema" + template["ext"])  "resources" / (class_details["class_name"] + template["ext"])
    resource_file.parent.mkdir(exist_ok=True)
    return str(resource_file)


def _write_templated_file(class_file, class_details, template_filename):
    with open(class_file, "a", encoding="utf-8") as file:
        templates = files("cimgen.languages.sqlalchemy.templates")
        with templates.joinpath(template_filename).open(encoding="utf-8") as f:
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
    shutil.copy(os.path.join(os.getcwd(), "cimgen/languages/sqlalchemy/Base.py"), path + "/Base.py")
    shutil.copy(os.path.join(os.getcwd(), "cimgen/languages/sqlalchemy/util.py"), path + "/util.py")


def resolve_headers(path: str, version: str):
    pass


def _setImports(class_details: dict):
    attributes = class_details["attributes"]
    import_set = set()
    if class_details["sub_class_of"] == "Base":
        import_set.add("from ..Base import Base")
    else:
        import_set.add("from ." + class_details["sub_class_of"] + " import " + class_details["sub_class_of"])
    for attribute in attributes:
        if attribute["is_list_attribute"] or attribute["is_class_attribute"]:
            import_set.add(
                "from ."
                + attribute["attribute_class"]
                + " import "
                + attribute["attribute_class"]
                + " as "
                + attribute["attribute_class"]
                + "Class"
            )
    return sorted(import_set)
