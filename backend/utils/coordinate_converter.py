from pyproj import Transformer

# 设置 UTM 48N（EPSG:32648）
WGS84_CRS = "EPSG:4326"     # WGS84 经纬度
UTM48N_CRS = "EPSG:32648"   # UTM 48N 投影

# 1. WGS84 经纬度 -> UTM 48N
def wgs84_to_utm(lon, lat):
    transformer = Transformer.from_crs(WGS84_CRS, UTM48N_CRS, always_xy=True)
    utm_x, utm_y = transformer.transform(lon, lat)
    return utm_x, utm_y

# 2. UTM 48N -> WGS84 经纬度
def utm_to_wgs84(utm_x, utm_y):
    transformer = Transformer.from_crs(UTM48N_CRS, WGS84_CRS, always_xy=True)
    lon, lat = transformer.transform(utm_x, utm_y)
    return lon, lat

def polygon_wgs84_to_utm(polygon):
    """将多边形顶点坐标从 WGS84 转换为 UTM 48N"""
    return [wgs84_to_utm(lon, lat) for lon, lat in polygon]

def polygon_utm_to_wgs84(polygon):
    """将多边形顶点坐标从 UTM 48N 转换为 WGS84"""
    return [utm_to_wgs84(utm_x, utm_y) for utm_x, utm_y in polygon]