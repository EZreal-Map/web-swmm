from pydantic import BaseModel


class JunctionModel(BaseModel):
    type: str = "junction"
    name: str
    lon: float
    lat: float
    elevation: float
    depth_max: float
    depth_init: float
    depth_surcharge: float
    area_ponded: float
