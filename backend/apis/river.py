from fastapi import APIRouter, HTTPException
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple
import os
import geopandas as gpd
from shapely.geometry import Point, LineString, Polygon
import pandas as pd
import json
from collections import defaultdict
import tempfile
import uuid


from schemas.river import (
    RiverClipRequest,
    RiverNetworkRequest,
    RiverNetworkImportRequest,
)
from schemas.junction import JunctionModel
from schemas.conduit import ConduitRequestModel
from schemas.result import Result
from utils.utils import with_exception_handler
from apis.junction import create_junction as create_junction_api
from apis.conduit import create_conduit as create_conduit_api

riverRouter = APIRouter()

# 定义水系 shapefile 路径常量
RIVER_SHAPEFILE_PATH = Path("static/river_network/研究区域水系.shp")
# 配置 GDAL 环境变量，允许自动恢复或创建缺失的 .shx 文件
os.environ["SHAPE_RESTORE_SHX"] = "YES"

# 坐标参考系常量
DEFAULT_CRS = "EPSG:4326"  # WGS84
METRIC_EPSG = 3857  # Web Mercator，方便按"米"计算长度

CoordKey = Tuple[float, float]


# ==================== GeoJSON 导入辅助函数 ====================


def normalize_identifier(value) -> Optional[str]:
    """将数值/字符串 ID 统一为字符串,便于匹配"""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if float(value).is_integer():
            return str(int(value))
        return str(value)
    text = str(value).strip()
    return text or None


def extract_point_coordinates(feature: dict) -> Optional[Tuple[float, float]]:
    geometry = feature.get("geometry") or {}
    coords = geometry.get("coordinates")
    if not isinstance(coords, (list, tuple)) or len(coords) < 2:
        return None
    lon, lat = coords[0], coords[1]
    if not isinstance(lon, (int, float)) or not isinstance(lat, (int, float)):
        return None
    return float(lon), float(lat)


# ==================== 水系打断相关函数 ====================


def ensure_crs(
    gdf: gpd.GeoDataFrame, default_crs: str = DEFAULT_CRS
) -> gpd.GeoDataFrame:
    """确保 GeoDataFrame 带有 CRS，没有则设置为默认值"""
    if gdf.crs is None:
        return gdf.set_crs(default_crs)
    return gdf


def iter_lines(geom) -> Iterable:
    """对单个几何对象，安全地迭代其中所有 LineString"""
    if geom is None or geom.is_empty:
        return

    geom_type = getattr(geom, "geom_type", None)
    if geom_type == "LineString":
        yield geom
    elif geom_type == "MultiLineString":
        for part in geom.geoms:
            if not part.is_empty:
                yield part


def find_confluence_nodes(
    gdf_m: gpd.GeoDataFrame,
    precision: int = 0,
) -> Dict[CoordKey, Point]:
    """在投影坐标下识别河流交汇点（基于不同几何要素的顶点重合）"""
    node_features: Dict[CoordKey, Set[int]] = defaultdict(set)
    node_geom: Dict[CoordKey, Tuple[float, float]] = {}

    for feature_idx, geom in enumerate(gdf_m.geometry):
        for line in iter_lines(geom):
            for x, y, *_ in line.coords:
                key = (round(x, precision), round(y, precision))
                node_features[key].add(feature_idx)
                node_geom[key] = (x, y)

    confluences: Dict[CoordKey, Point] = {}
    for key, features in node_features.items():
        if len(features) >= 2:
            x, y = node_geom[key]
            confluences[key] = Point(x, y)

    return confluences


def generate_points_along_rivers(
    gdf: gpd.GeoDataFrame,
    spacing: float = 500.0,
    precision: int = 0,
) -> gpd.GeoDataFrame:
    """在河道上按规则打点（起点/交汇点/终点分段 + 区段内均匀）"""
    if spacing <= 0:
        raise ValueError("spacing 必须为正数（单位：米）")

    if gdf.empty:
        return gpd.GeoDataFrame(columns=["line_idx", "s_m"], geometry=[], crs=gdf.crs)

    gdf = ensure_crs(gdf)
    gdf_m = gdf.to_crs(epsg=METRIC_EPSG)
    confluence_nodes = find_confluence_nodes(gdf_m, precision=precision)

    point_records: List[dict] = []
    point_geoms_m: List[Point] = []

    for line_idx, (geom_m, row) in enumerate(zip(gdf_m.geometry, gdf.itertuples())):
        row_dict = row._asdict()
        row_dict.pop("Index", None)

        for line_geom in iter_lines(geom_m):
            if line_geom.length == 0.0:
                continue

            break_positions: Set[float] = {0.0, float(line_geom.length)}

            for x, y, *_ in line_geom.coords:
                key = (round(x, precision), round(y, precision))
                if key in confluence_nodes:
                    p = confluence_nodes[key]
                    d = float(line_geom.project(p))
                    break_positions.add(d)

            sorted_breaks = sorted(break_positions)
            sample_positions: Set[float] = set()

            for start_d, end_d in zip(sorted_breaks[:-1], sorted_breaks[1:]):
                seg_len = end_d - start_d
                if seg_len <= 0:
                    continue

                n_points = max(2, int(seg_len / spacing) + 1)
                step = seg_len / (n_points - 1)

                for i in range(n_points):
                    pos = start_d + i * step
                    sample_positions.add(round(pos, 3))

            for s_m in sorted(sample_positions):
                p_m = line_geom.interpolate(s_m)
                point_geoms_m.append(p_m)

                rec = dict(row_dict)
                rec.update({"line_idx": line_idx, "s_m": float(s_m)})
                point_records.append(rec)

    pts_gdf_m = gpd.GeoDataFrame(point_records, geometry=point_geoms_m, crs=gdf_m.crs)
    pts_gdf = pts_gdf_m.to_crs(gdf.crs)
    return pts_gdf


def build_river_network(
    gdf: gpd.GeoDataFrame,
    spacing: float = 3000.0,
    merge_dist: float = 800.0,
    precision: int = 0,
) -> gpd.GeoDataFrame:
    """从河网 GeoDataFrame 生成节点+渠道网络"""
    pts_full = generate_points_along_rivers(gdf, spacing=spacing, precision=precision)

    pts_full = ensure_crs(pts_full)
    pts_m = pts_full.to_crs(epsg=METRIC_EPSG)

    node_key_to_id: Dict[CoordKey, int] = {}
    node_geoms_m: List[Point] = []
    node_records: List[dict] = []
    point_to_node: Dict[int, int] = {}

    next_node_id = 1

    for idx, geom in enumerate(pts_m.geometry):
        if geom is None or geom.is_empty:
            continue
        key = (round(geom.x, precision), round(geom.y, precision))
        node_id = node_key_to_id.get(key)
        if node_id is None:
            node_id = next_node_id
            next_node_id += 1
            node_key_to_id[key] = node_id
            node_geoms_m.append(geom)
            node_records.append({"node_id": node_id})
        point_to_node[idx] = node_id

    nodes_m = gpd.GeoDataFrame(node_records, geometry=node_geoms_m, crs=pts_m.crs)
    nodes_gdf = nodes_m.to_crs(gdf.crs)

    if merge_dist > 0:
        used_idx: Set[int] = set()
        old_to_new_id: Dict[int, int] = {}
        merged_geoms_m: List[Point] = []
        merged_records: List[dict] = []

        geoms_nodes_m = list(nodes_m.geometry)
        node_ids_arr = list(nodes_m["node_id"])

        new_node_id = 1
        for i, geom_i in enumerate(geoms_nodes_m):
            if i in used_idx:
                continue
            if geom_i is None or geom_i.is_empty:
                continue

            cluster_idx = [i]
            used_idx.add(i)

            for j in range(i + 1, len(geoms_nodes_m)):
                if j in used_idx:
                    continue
                geom_j = geoms_nodes_m[j]
                if geom_j is None or geom_j.is_empty:
                    continue
                if geom_i.distance(geom_j) < merge_dist:
                    used_idx.add(j)
                    cluster_idx.append(j)

            xs = [geoms_nodes_m[k].x for k in cluster_idx]
            ys = [geoms_nodes_m[k].y for k in cluster_idx]
            rep_geom = Point(sum(xs) / len(xs), sum(ys) / len(ys))

            curr_new_id = new_node_id
            new_node_id += 1
            merged_geoms_m.append(rep_geom)
            merged_records.append({"node_id": curr_new_id})

            for k in cluster_idx:
                old_id = int(node_ids_arr[k])
                old_to_new_id[old_id] = curr_new_id

        nodes_m = gpd.GeoDataFrame(
            merged_records, geometry=merged_geoms_m, crs=nodes_m.crs
        )
        nodes_gdf = nodes_m.to_crs(gdf.crs)

        for idx, old_id in list(point_to_node.items()):
            new_id = old_to_new_id.get(int(old_id))
            if new_id is None:
                new_id = int(old_id)
            point_to_node[idx] = new_id

    node_geom_map: Dict[int, Point] = {
        int(row.node_id): row.geometry for row in nodes_gdf.itertuples()
    }

    link_records: List[dict] = []
    link_geoms: List[LineString] = []

    # 为渠道顺序编号，便于下游直接使用 node_id 作为唯一标识
    link_id = 1

    if "line_idx" not in pts_full.columns or "s_m" not in pts_full.columns:
        raise ValueError(
            "generate_points_along_rivers 输出必须包含 line_idx 和 s_m 字段"
        )

    for line_idx in sorted(pts_full["line_idx"].unique()):
        sub = pts_full[pts_full["line_idx"] == line_idx].copy()
        if sub.empty:
            continue

        node_ids: List[int] = []
        for i in sub.index:
            n_id = point_to_node.get(i)
            if n_id is None:
                continue
            node_ids.append(n_id)
        if len(node_ids) != len(sub):
            sub = sub.loc[[i for i in sub.index if i in point_to_node]]
            if sub.empty:
                continue

        sub = sub.assign(node_id=[point_to_node[i] for i in sub.index])
        sub = sub.sort_values("s_m")

        prev_row = None
        for row in sub.itertuples():
            if prev_row is None:
                prev_row = row
                continue

            from_id = int(prev_row.node_id)
            to_id = int(row.node_id)
            if from_id == to_id:
                prev_row = row
                continue

            from_geom = node_geom_map[from_id]
            to_geom = node_geom_map[to_id]
            link_geoms.append(LineString([from_geom, to_geom]))

            rec = {
                "node_id": link_id,
                "from_id": from_id,
                "to_id": to_id,
            }

            link_records.append(rec)
            link_id += 1
            prev_row = row

    links_gdf = gpd.GeoDataFrame(link_records, geometry=link_geoms, crs=gdf.crs)

    nodes_out = nodes_gdf.copy()
    nodes_out["type"] = "node"
    # 使用短前缀避免前端标注过长
    base_prefix = uuid.uuid4().hex[:2].upper()

    # 为节点生成唯一 id，并记录映射方便渠道引用
    node_id_map: Dict[int, str] = {}
    for idx, row in enumerate(nodes_out.itertuples(), start=1):
        node_id_map[int(row.node_id)] = f"{base_prefix}-J{idx}"

    nodes_out["id"] = nodes_out["node_id"].apply(lambda x: node_id_map[int(x)])
    nodes_out = nodes_out.drop(columns=["node_id"])

    links_out = links_gdf.copy()
    links_out["type"] = "link"
    link_id_map: Dict[int, str] = {}
    for idx, row in enumerate(links_out.itertuples(), start=1):
        link_id_map[int(row.node_id)] = f"{base_prefix}-C{idx}"

    links_out["id"] = links_out["node_id"].apply(lambda x: link_id_map[int(x)])
    links_out["from_id"] = links_out["from_id"].apply(lambda x: node_id_map[int(x)])
    links_out["to_id"] = links_out["to_id"].apply(lambda x: node_id_map[int(x)])
    links_out = links_out.drop(columns=["node_id"])

    network_gdf = gpd.GeoDataFrame(
        pd.concat([nodes_out, links_out], ignore_index=True), crs=nodes_gdf.crs
    )

    # 确保输出坐标系为 WGS84 (EPSG:4326)
    if network_gdf.crs is None:
        network_gdf = network_gdf.set_crs("EPSG:4326")
    elif str(network_gdf.crs) != "EPSG:4326":
        network_gdf = network_gdf.to_crs("EPSG:4326")

    return network_gdf


# ==================== 水系切割相关函数 ====================


def ensure_closed_ring(coords: List[List[float]]) -> List[Tuple[float, float]]:
    """确保坐标环是闭合的，如果需要则追加第一个点"""
    if len(coords) < 3:
        raise ValueError("边界坐标至少需要3个点才能构成有效的多边形")

    closed_coords: List[Tuple[float, float]] = [
        (float(coord[0]), float(coord[1])) for coord in coords
    ]

    first = closed_coords[0]
    last = closed_coords[-1]
    if first != last:
        closed_coords.append(first)

    return closed_coords


def clip_river_by_polygon(
    shapefile_path: Path,
    polygon_coords: List[List[float]],
    boundary_crs: str = "EPSG:4326",
) -> dict:
    """
    根据边界坐标裁剪水系 shapefile，返回 GeoJSON 格式

    Args:
        shapefile_path: shapefile 文件路径
        polygon_coords: 边界坐标列表 [[lon, lat], ...]
        boundary_crs: 边界坐标的坐标系，默认 WGS84

    Returns:
        裁剪后的 GeoJSON 字典
    """
    # 检查文件是否存在
    if not shapefile_path.exists():
        raise HTTPException(status_code=404, detail=f"水系文件不存在: {shapefile_path}")

    # 确保坐标环闭合
    closed_ring = ensure_closed_ring(polygon_coords)

    # 创建边界多边形
    boundary_poly = Polygon(closed_ring)

    if boundary_poly.is_empty:
        raise HTTPException(status_code=400, detail="边界多边形为空，请检查坐标列表")

    # 读取水系 shapefile
    river_gdf = gpd.read_file(shapefile_path)
    if river_gdf.empty:
        raise HTTPException(
            status_code=500, detail=f"水系文件 {shapefile_path} 没有数据"
        )

    # 创建边界 GeoDataFrame
    boundary_gdf = gpd.GeoDataFrame(
        index=[0], geometry=[boundary_poly], crs=boundary_crs
    )

    # 检查坐标系，如果没有则设置为默认的 WGS84
    if river_gdf.crs is None:
        river_gdf = river_gdf.set_crs("EPSG:4326")

    # 如果坐标系不一致，转换边界坐标系
    if river_gdf.crs != boundary_gdf.crs:
        boundary_gdf = boundary_gdf.to_crs(river_gdf.crs)

    # 执行裁剪
    clipped = gpd.clip(river_gdf, boundary_gdf)

    if clipped.empty:
        raise HTTPException(
            status_code=400, detail="裁剪结果为空，请确保边界与水系数据有重叠区域"
        )

    # 转换为 WGS84 以便前端使用
    if clipped.crs is None:
        clipped = clipped.set_crs("EPSG:4326")
    elif str(clipped.crs) != "EPSG:4326":
        clipped = clipped.to_crs("EPSG:4326")

    # 转换为 GeoJSON（不包含 CRS 信息，因为 GeoJSON 默认就是 WGS84）
    geojson_str = clipped.to_json(drop_id=True, show_bbox=False)
    geojson_dict = json.loads(geojson_str)

    # 确保移除任何 CRS 相关字段（GeoJSON RFC 7946 规范不应包含 crs 字段）
    if "crs" in geojson_dict:
        del geojson_dict["crs"]

    return geojson_dict


@riverRouter.post(
    "/clip",
    summary="水系切割",
    description="根据提供的边界坐标（WGS84 经纬度）裁剪水系数据，返回 GeoJSON 格式的裁剪结果",
    response_model=Result,
)
@with_exception_handler(default_message="水系切割失败，发生未知错误")
async def clip_river(request: RiverClipRequest):
    """
    水系切割 API

    **请求参数：**
    - polygon: 边界坐标列表，格式为 [[lon, lat], [lon, lat], ...]
      - 至少需要 3 个点
      - 经度范围：-180 到 180
      - 纬度范围：-90 到 90
      - 坐标系：WGS84 (EPSG:4326)

    **返回结果：**
    - geojson: 裁剪后的水系数据（GeoJSON 格式）
    - feature_count: 裁剪后的要素数量
    - message: 操作结果消息

    **示例：**
    ```json
    {
        "polygon": [
            [106.5, 26.5],
            [107.5, 26.5],
            [107.5, 27.5],
            [106.5, 27.5]
        ]
    }
    ```
    """
    # 执行水系裁剪
    geojson_result = clip_river_by_polygon(
        shapefile_path=RIVER_SHAPEFILE_PATH,
        polygon_coords=request.polygon,
        boundary_crs="EPSG:4326",
    )

    # 构造响应
    response_data = {"geojson": geojson_result}

    return Result.success_result(data=response_data, message="水系获取成功")


@riverRouter.post(
    "/break",
    summary="水系打断生成网络",
    description="将水系线要素按指定间距打断，生成节点和渠道网络，返回 GeoJSON 格式",
    response_model=Result,
)
@with_exception_handler(default_message="水系打断失败，发生未知错误")
async def generate_river_network(request: RiverNetworkRequest):
    """
    水系打断生成网络 API

    **请求参数：**
    - geojson: 水系 GeoJSON 数据（必须包含 LineString 或 MultiLineString 几何）
    - spacing: 沿河打点的目标间距，单位米（默认 3000 米）

    **返回结果：**
    - network: 包含节点和渠道的 GeoJSON 数据
      - 节点：type="node"，包含 node_id
      - 渠道：type="link"，包含 from_id 和 to_id
    - node_count: 节点数量
    - link_count: 渠道数量
    - message: 操作结果消息

    **示例：**
    ```json
    {
        "geojson": {
            "type": "FeatureCollection",
            "features": [...]
        },
        "spacing": 3000.0
    }
    ```
    """
    try:
        # 将 GeoJSON 转换为 GeoDataFrame
        # 使用临时文件方式处理 GeoJSON
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".geojson", delete=False, encoding="utf-8"
        ) as tmp_file:
            json.dump(request.geojson, tmp_file)
            tmp_path = tmp_file.name

        try:
            gdf = gpd.read_file(tmp_path)
        finally:
            # 清理临时文件
            Path(tmp_path).unlink(missing_ok=True)

        if gdf.empty:
            raise HTTPException(status_code=400, detail="输入的 GeoJSON 数据为空")

        # 检查几何类型
        valid_types = {"LineString", "MultiLineString"}
        geom_types = set(gdf.geometry.geom_type.unique())
        if not geom_types.intersection(valid_types):
            raise HTTPException(
                status_code=400,
                detail=f"GeoJSON 必须包含 LineString 或 MultiLineString 几何类型，当前类型: {geom_types}",
            )

        # 确保输入数据使用 WGS84
        if gdf.crs is None:
            gdf = gdf.set_crs("EPSG:4326")
        elif str(gdf.crs) != "EPSG:4326":
            gdf = gdf.to_crs("EPSG:4326")

        # 执行水系打断
        network_gdf = build_river_network(
            gdf=gdf,
            spacing=request.break_distance,
            merge_dist=800.0,
            precision=0,
        )

        # 统计节点和渠道数量
        node_count = len(network_gdf[network_gdf["type"] == "node"])
        link_count = len(network_gdf[network_gdf["type"] == "link"])

        # 转换为 GeoJSON（不包含 CRS 信息，因为 GeoJSON 默认就是 WGS84）
        geojson_str = network_gdf.to_json(drop_id=True, show_bbox=False)
        network_geojson = json.loads(geojson_str)

        # 确保移除任何 CRS 相关字段（GeoJSON RFC 7946 规范不应包含 crs 字段）
        if "crs" in network_geojson:
            del network_geojson["crs"]

        response_data = {
            "geojson": network_geojson,
            "node_count": node_count,
            "link_count": link_count,
            "spacing": request.break_distance,
            "message": f"水系打断成功，生成 {node_count} 个节点和 {link_count} 条渠道",
        }

        return Result.success_result(
            data=response_data, message=response_data["message"]
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@riverRouter.post(
    "/import",
    summary="根据 GeoJSON 创建节点与渠道",
    description="提取 GeoJSON 中的节点/渠道特征,自动创建 Junction 与 Conduit",
    response_model=Result,
)
@with_exception_handler(default_message="导入失败，发生未知错误")
async def import_river_network(payload: RiverNetworkImportRequest):
    geojson = payload.geojson
    geojson_type = geojson.get("type")

    if geojson_type == "FeatureCollection":
        features = geojson.get("features", [])
        if not isinstance(features, list):
            raise HTTPException(status_code=400, detail="geojson.features 必须是列表")
    else:
        features = [geojson]

    if not features:
        raise HTTPException(status_code=400, detail="geojson 中没有可用的 features")

    node_features = [
        f for f in features if (f.get("properties") or {}).get("type") == "node"
    ]
    link_features = [
        f for f in features if (f.get("properties") or {}).get("type") == "link"
    ]

    if not node_features:
        raise HTTPException(
            status_code=400, detail="geojson 中缺少节点 (type=node) 数据"
        )
    # 如果id和name是分开的，就使用字典
    node_id_to_name: Dict[str, str] = {}
    # 如果id和name是一个东西，就使用集合
    available_node_ids: Set[str] = set()
    created_junctions: List[str] = []
    junction_errors: List[dict] = []

    for feature in node_features:
        props = feature.get("properties") or {}
        raw_node_id = props.get("id")
        normalized_id = normalize_identifier(raw_node_id)
        if normalized_id is None:
            junction_errors.append(
                {
                    "id": raw_node_id,
                    "reason": "节点缺少 id，无法生成名称",
                }
            )
            continue

        if normalized_id in available_node_ids:
            continue

        node_name = normalized_id
        available_node_ids.add(normalized_id)

        coords = extract_point_coordinates(feature)
        if coords is None:
            junction_errors.append(
                {
                    "name": node_name,
                    "reason": "节点缺少有效经纬度",
                }
            )
            available_node_ids.discard(normalized_id)
            continue

        lon, lat = coords
        junction_payload = JunctionModel(name=node_name, lon=lon, lat=lat)

        try:
            await create_junction_api(junction_payload)
            created_junctions.append(node_name)
        except HTTPException as exc:
            reason = getattr(exc, "detail", str(exc))
            reason_text = (
                json.dumps(reason, ensure_ascii=False)
                if isinstance(reason, dict)
                else str(reason)
            )
            junction_errors.append(
                {
                    "name": node_name,
                    "reason": reason_text,
                }
            )
            if "已存在" not in reason_text:
                # 创建失败，移除可用节点
                available_node_ids.discard(normalized_id)

    conduit_names_in_use: Set[str] = set()
    created_conduits: List[str] = []
    conduit_errors: List[dict] = []

    for idx, feature in enumerate(link_features, start=1):
        props = feature.get("properties") or {}
        raw_link_id = props.get("id")
        normalized_link_id = normalize_identifier(raw_link_id)
        base_name = normalized_link_id if normalized_link_id else f"AUTO_{idx}"
        link_name = base_name
        suffix = 1
        while link_name in conduit_names_in_use:
            suffix += 1
            link_name = f"{base_name}_{suffix}"
        conduit_names_in_use.add(link_name)

        from_id = normalize_identifier(props.get("from_id"))
        to_id = normalize_identifier(props.get("to_id"))

        if not from_id or not to_id:
            conduit_errors.append(
                {
                    "name": link_name,
                    "reason": "渠道缺少 from_id 或 to_id",
                }
            )
            continue

        if from_id not in available_node_ids or to_id not in available_node_ids:
            conduit_errors.append(
                {
                    "name": link_name,
                    "reason": "渠道引用的节点不存在",
                }
            )
            continue

        conduit_payload = ConduitRequestModel(
            name=link_name,
            from_node=from_id,
            to_node=to_id,
        )

        try:
            await create_conduit_api(conduit_payload)
            created_conduits.append(link_name)
        except HTTPException as exc:
            conduit_errors.append(
                {
                    "name": link_name,
                    "reason": getattr(exc, "detail", str(exc)),
                }
            )

    message = (
        f"导入完成: 创建节点 {len(created_junctions)} 个, "
        f"渠道 {len(created_conduits)} 条"
    )

    response_payload = {
        "junctions": {
            "created": created_junctions,
            "failed": junction_errors,
        },
        "conduits": {
            "created": created_conduits,
            "failed": conduit_errors,
        },
    }

    return Result.success_result(data=response_payload, message=message)
