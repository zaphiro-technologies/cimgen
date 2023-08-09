from pydantic import BaseModel, ConfigDict


class Base(BaseModel):
    model_config = ConfigDict(populate_by_name=True, defer_build=True)
    """
    Base Class for CIM
    """

    """
    not valid for pydantic 2.0
    class Config:
        @staticmethod
        def schema_extra(schema: dict, _):
            props = {}
            for k, v in schema.get("properties", {}).items():
                if not v.get("hidden", False):
                    props[k] = v
            schema["properties"] = props """

    def printxml(self, dict={}):
        return dict
