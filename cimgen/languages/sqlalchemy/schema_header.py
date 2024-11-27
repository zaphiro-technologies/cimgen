from __future__ import annotations
from typing import Annotated, Optional
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    TIMESTAMP,
    DateTime,
    Table,
)
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship, configure_mappers
from sqlalchemy import ForeignKey
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
from typing import List
from .Base import BaseClass
from datetime import datetime
import uuid

last_time = Annotated[
    str,
    mapped_column(TIMESTAMP, server_default=func.now(), server_onupdate=func.current_timestamp()),
]
