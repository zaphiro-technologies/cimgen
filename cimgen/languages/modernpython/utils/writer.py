from lxml import etree
import uuid
from pydantic import BaseModel

from .constants import NAMESPACES
from .profile import BaseProfile, Profile


class Writer(BaseModel):
    """Class for writing CIM RDF/XML files

    :param dict objects: Mapping {mRID: CIM object}
    :param dict[str, str] writer_metadata: Any additional data in header
    (default: {"modelingAuthoritySet": "www.sogno.energy"})
    :param list[BaseProfile] profile_list: List of profiles to export, default is all cgmes profiles
    """

    objects: dict
    writer_metadata: dict[str, str] = {
        "modelingAuthoritySet": "www.sogno.energy",
        "DependentOn": [],
    }
    profile_list: list[BaseProfile] = list(Profile)

    def write(
        self,
        output_file: str,
        custom_profiles: list[BaseProfile] = [],
        custom_namespaces: dict[str, str] = {},
    ) -> dict[BaseProfile, str]:
        """Write CIM RDF/XML files.
        This function writes CIM objects into one or more RDF/XML files separated by profiles.
        Each CIM object will be written to its corresponding profile file depending on class_profile_map.
        But some objects to more than one file if some attribute profiles are not the same as the class profile.

        :param str output_file: Stem of the output file, resulting files: <output_file>_<profile.long_name>.xml
        :param str model_id: Stem of the model IDs, resulting IDs: <model_id>_<profile.long_name>
        :param list[BaseProfile] custom_profiles: List of custom profiles to export, defaults to []
        :param dict[str, str] custom_namespaces: {"namespace_prefix": "namespace_uri"}, defaults to {}

        :return dict[BaseProfile, str]: Mapping of profile to output_file
        """
        profile_list = self.profile_list
        profile_list += {p for p in custom_profiles if p not in profile_list}
        profile_file_map: dict[BaseProfile, str] = {}
        self.writer_metadata["DependentOn"] = []
        for profile in sorted(profile_list):
            profile_id = f"urn:uuid:{uuid.uuid4()}"
            full_file_name = output_file + "_" + profile.long_name + ".xml"
            output = self._generate(
                profile,
                profile_id,
                custom_namespaces,
            )
            self.writer_metadata["DependentOn"].append(profile_id)
            if output:
                output.write(
                    full_file_name,
                    pretty_print=True,
                    xml_declaration=True,
                    encoding="utf-8",
                )
                profile_file_map[profile] = full_file_name
        return profile_file_map

    def _generate(
        self,
        profile: BaseProfile,
        model_id: str,
        custom_namespaces: dict[str, str] = {},
    ) -> etree._ElementTree | None:
        """Write CIM objects as RDF/XML data to a string.

        This function creates RDF/XML tree corresponding to one profile.

        :param BaseProfile profile: Only data for this profile should be written.
        :param str model_id: Stem of the model IDs, resulting IDs: <modelID>_<profileName>.
        :param dict[str, str] custom_namespaces: {"namespace_prefix": "namespace_uri"}

        :return _ElementTree|None: etree of the profile
        """
        full_model = {
            "id": model_id,
            "Model": self.writer_metadata,
        }
        full_model["Model"].update({"profile": profile.uris})

        namespaces_map = NAMESPACES
        namespaces_map.update(custom_namespaces)

        rdf_namespace = f"""{{{namespaces_map["rdf"]}}}"""
        md_namespace = f"""{{{namespaces_map["md"]}}}"""

        root = etree.Element(
            rdf_namespace + "RDF",
            nsmap=namespaces_map,
        )

        # full_model header
        model = etree.Element(
            md_namespace + "FullModel",
            nsmap=namespaces_map,
        )
        model.set(rdf_namespace + "about", full_model["id"])
        for key, value in full_model["Model"].items():
            if key == "DependentOn":
                for item in value:
                    element = etree.SubElement(
                        model,
                        md_namespace + "Model." + key,
                    )
                    element.set(rdf_namespace + "resource", item)
            elif isinstance(value, list):
                for item in value:
                    element = etree.SubElement(
                        model,
                        md_namespace + "Model." + key,
                    )
                    element.text = item
            else:
                element = etree.SubElement(
                    model,
                    md_namespace + "Model." + key,
                )
                element.text = value
        root.append(model)

        count = 0
        for id, obj in self.objects.items():
            obj_etree = obj.to_xml(profile_to_export=profile, id=id)
            if obj_etree is not None:
                root.append(obj_etree)
                count += 1
        if count > 0:
            output = etree.ElementTree(root)
        else:
            output = None
        return output
