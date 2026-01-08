import request from '@/utils/request'

// 根据研究区域 polygon 获取水系 geojson
export const getRiverNetworkAxios = (data) => request.post('/river/clip', data)

// 打断河流
export const breakRiverAxios = (data) => request.post('/river/break', data)

// 河流 节点，渠道 的导入
export const importRiverAxios = (data) => request.post('/river/import', data)
