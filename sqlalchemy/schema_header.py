from __future__ import annotations
from typing import Annotated, Optional
from sqlalchemy import Column, Integer, String, Float, Boolean, TIMESTAMP, DateTime
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship, configure_mappers
from sqlalchemy import ForeignKey
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
from typing import List
from .Base import Base
from datetime import datetime

intpk = Annotated[int, mapped_column(Integer, primary_key=True, autoincrement=True)]
strpk = Annotated[str, mapped_column(String(255), primary_key=True)]
str50 = Annotated[str, mapped_column(String(50))]
str255 = Annotated[str, mapped_column(String(255))]
last_time = Annotated[
    str,
    mapped_column(
        TIMESTAMP, server_default=func.now(), server_onupdate=func.current_timestamp()
    ),
]
