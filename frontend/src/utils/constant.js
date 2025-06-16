export const POINTPREFIX = 'POINT#'
export const POLYLINEPREFIX = 'POLYLINE#'
export const POLYGONPREFIX = 'POLYGON#'

// Cesium 默认用的是 WGS84 椭球高度，而平常使用的 DEM 数据则通常是以平均海平面为基准的正交高程
// 在乐山这个地方，WGS84 椭球高度和正交高程的差值大概是 +44 米
export const HEIGHT_GEOID_OFFSET = 44 // 乐山地区 WGS84 椭球高 → 正高的近似差值（单位：米）
