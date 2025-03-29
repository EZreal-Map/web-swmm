from pydantic import BaseModel


class ConduitModel(BaseModel):
    type: str = "conduit"
    name: str
    from_node: str
    to_node: str
    length: float
    roughness: float
