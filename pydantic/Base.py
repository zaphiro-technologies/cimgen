from pydantic import BaseModel
from enum import IntEnum


class CgmesProfileEnum(IntEnum):
    EQ = 0
    SSH = 1
    TP = 2
    SV = 3
    DY = 4
    GL = 5
    DL = 5
    TP_DB = 7
    ED_BD = 8


class Base(BaseModel):
    """
    Base Class for CIM
    """

    class Config:
        @staticmethod
        def schema_extra(schema: dict, _):
            props = {}
            for k, v in schema.get("properties", {}).items():
                if not v.get("hidden", False):
                    props[k] = v
            schema["properties"] = props

    def printxml(self, dict={}):
        return dict
