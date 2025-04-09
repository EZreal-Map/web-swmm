import request from '@/utils/request'
import {} from '@/utils/convert'

// 获取所有不规则断面的属性
// export const getAllTransectsAxios = () => request.get('/swmm/transects')

// 获取所有不规则断面的名称
export const getAllTransectsNameAxios = () => request.get('/swmm/transects/name')

// 通过不规则断面ID获取不规则断面的属性
export const getTransectByIdAxios = (id) => request.get(`/swmm/transect/${id}`)

// 通过不规则断面ID更新不规则断面所有属性
export const updateTransectByIdAxios = (id, data) => {
  data.station_elevations = data.station_elevations
    .filter(([x, y]) => x && y) // 排除 undefined / '' / null 的数据
    .sort((a, b) => a[1] - b[1]) // 按照 X 坐标升序排序
  return request.put(`/swmm/transect/${id}`, data)
}

// 增加不规则断面
export const createTransectAxios = (data) => request.post('/swmm/transect', data)

// 通过不规则断面ID删除不规则断面
export const deleteTransectByIdAxios = (id) => request.delete(`/swmm/transect/${id}`)
