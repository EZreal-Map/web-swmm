import request from '@/utils/request'

// 根据研究区域 polygon 获取水系 geojson
export const getRiverNetworkAxios = (data) => request.post('/river/clip', data)

// 打断河流
export const breakRiverAxios = (data) => request.post('/river/break', data)
