from enum import Enum


class MixMode(Enum):
    MAGNITUDE_PHASE = "MAGNITUDE_PHASE"
    REAL_IMAGINARY = "REAL_IMAGINARY"


class ComponentMode(Enum):
    MAGNITUDE = "MAGNITUDE"
    PHASE = "PHASE"
    REAL = "REAL"
    IMAGINARY = "IMAGINARY"


class RegionMode(Enum):
    FULL = "FULL"
    INNER_OUTER = "INNER_OUTER"
    INNER = "INNER"
    OUTER = "OUTER"
