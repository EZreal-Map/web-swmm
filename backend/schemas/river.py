from pydantic import BaseModel, field_validator
from fastapi import HTTPException
from typing import List, Tuple


class RiverClipRequest(BaseModel):
    """水系切割请求模型"""

    polygon: List[List[float]] = []

    @field_validator("polygon", mode="before")
    def validate_polygon(cls, value):
        """验证边界坐标"""
        if not isinstance(value, list):
            raise HTTPException(status_code=400, detail="边界坐标必须是列表类型")

        if len(value) < 3:
            raise HTTPException(
                status_code=400, detail="边界坐标至少需要3个点才能构成有效的多边形"
            )

        for idx, coord in enumerate(value):
            if not isinstance(coord, (list, tuple)):
                raise HTTPException(
                    status_code=400, detail=f"第 {idx + 1} 个坐标必须是列表或元组类型"
                )

            if len(coord) != 2:
                raise HTTPException(
                    status_code=400,
                    detail=f"第 {idx + 1} 个坐标必须包含经度和纬度两个值",
                )

            lon, lat = coord
            if not isinstance(lon, (int, float)):
                raise HTTPException(
                    status_code=400, detail=f"第 {idx + 1} 个坐标的经度必须是数值类型"
                )

            if not isinstance(lat, (int, float)):
                raise HTTPException(
                    status_code=400, detail=f"第 {idx + 1} 个坐标的纬度必须是数值类型"
                )

            # 验证经纬度范围
            if not -180 <= lon <= 180:
                raise HTTPException(
                    status_code=400,
                    detail=f"第 {idx + 1} 个坐标的经度必须在 -180 到 180 之间",
                )

            if not -90 <= lat <= 90:
                raise HTTPException(
                    status_code=400,
                    detail=f"第 {idx + 1} 个坐标的纬度必须在 -90 到 90 之间",
                )

        return value


class RiverNetworkImportRequest(BaseModel):
    """根据 GeoJSON 导入节点与渠道请求模型"""

    geojson: dict

    @field_validator("geojson", mode="before")
    def validate_geojson(cls, value):
        if not isinstance(value, dict):
            raise HTTPException(status_code=400, detail="geojson 必须是字典类型")

        if "type" not in value:
            raise HTTPException(status_code=400, detail="geojson 必须包含 type 字段")

        geojson_type = value.get("type")
        if geojson_type not in [
            "FeatureCollection",
            "Feature",
            "LineString",
            "MultiLineString",
        ]:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"不支持的 GeoJSON 类型: {geojson_type}，仅支持 "
                    "FeatureCollection, Feature, LineString, MultiLineString"
                ),
            )

        return value


class RiverClipResponse(BaseModel):
    """水系切割响应模型"""

    geojson: dict
    feature_count: int = 0
    message: str = "水系切割成功"


class RiverNetworkRequest(BaseModel):
    """水系打断生成网络请求模型"""

    geojson: dict
    break_distance: float = 3000.0

    @field_validator("geojson", mode="before")
    def validate_geojson(cls, value):
        """验证 GeoJSON 格式"""
        if not isinstance(value, dict):
            raise HTTPException(status_code=400, detail="geojson 必须是字典类型")

        if "type" not in value:
            raise HTTPException(status_code=400, detail="geojson 必须包含 type 字段")

        # 检查是否是 FeatureCollection 或 Feature
        geojson_type = value.get("type")
        if geojson_type not in [
            "FeatureCollection",
            "Feature",
            "LineString",
            "MultiLineString",
        ]:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的 GeoJSON 类型: {geojson_type}，仅支持 FeatureCollection, Feature, LineString, MultiLineString",
            )

        return value

    @field_validator("break_distance", mode="before")
    def validate_break_distance(cls, value):
        """验证间距参数"""
        if not isinstance(value, (int, float)):
            raise HTTPException(status_code=400, detail="break_distance 必须是数值类型")

        if value <= 0:
            raise HTTPException(
                status_code=400, detail="break_distance 必须大于 0（单位：米）"
            )

        return float(value)
