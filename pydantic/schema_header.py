from __future__ import annotations
import uuid
from pydantic import (
    ConfigDict,
    Field,
    field_validator,
    computed_field
)
from geoalchemy2.shape import to_shape
from geoalchemy2.elements import WKBElement
from shapely.geometry import Point
from datetime import date, datetime, time
from typing import Optional, Iterator, List
from .Base import Base
from .util import cyclic_references_validator
from .enum import *


class PositionPoint(Base):
    """
    Set of spatial coordinates that determine a point, defined in the coordinate system specified in 'Location.CoordinateSystem'. Use a single position point instance to desribe a point-oriented location. Use a sequence of position points to describe a line-oriented object (physical location of non-point oriented objects like cables or lines), or area of an object (like a substation or a geographical zone - in this case, have first and last position point with the same values).

        :Location: Location described by this position point.
        :sequenceNumber: Zero-relative sequence number of this point within a series of points.
        :xPosition: X axis position.
        :yPosition: Y axis position.
        :zPosition: (if applicable) Z axis position.
    """

    possibleProfileList: dict = Field(
        default={
            "class": [
                CgmesProfileEnum.GL,
            ],
            "Location": [
                CgmesProfileEnum.GL,
            ],
            "sequenceNumber": [
                CgmesProfileEnum.GL,
            ],
            "xPosition": [
                CgmesProfileEnum.GL,
            ],
            "yPosition": [
                CgmesProfileEnum.GL,
            ],
            "zPosition": [
                CgmesProfileEnum.GL,
            ],
        }
    )

    Location: 'Location'
    sequenceNumber: Optional[int]
    point: Point #= Field(repr=False)  # we introduce this field compared to CIM definition because we want to store a proper geometry "point" in the database

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def xPosition(self) -> str:
        return str(self.point.x)

    @computed_field
    @property
    def yPosition(self) -> str:
        return str(self.point.y)

    @computed_field
    @property
    def zPosition(self) -> str:
        return str(self.point.z)

    # arbitrary_types_allowed is used because shapely data types are not based
    # on Pydantic ones, so model mapping is not native.
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

    # Pydantic needs help to map GeoAlchemy classes to Shapely
    @field_validator("point", mode="before")
    def validate_point_format(cls, v):
        if isinstance(v, Point):
            return v
        elif isinstance(v, WKBElement):
            point = to_shape(v)
            if point.geom_type != "Point":
                raise ValueError("must be a Point")
            return Point(point)
        else:
            raise ValueError("must be a Point or a WKBElement")
