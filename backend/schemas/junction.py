from pydantic import BaseModel


class JunctionModel(BaseModel):
    type: str = "junction"
    name: str
    lon: float
    lat: float
    elevation: float = 0.0
    depth_max: float = 0.0
    depth_init: float = 0.0
    depth_surcharge: float = 0.0
    area_ponded: float = 0.0
