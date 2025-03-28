from pydantic import BaseModel


class CoordinateModel(BaseModel):
    node: str
    x: float
    y: float
