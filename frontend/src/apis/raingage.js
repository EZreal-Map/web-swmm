import request from '@/utils/request'

// 获取所有雨量计名称
export const getAllRaingageNamesAxios = () => request.get('/swmm/raingage/name')

// 通过雨量计ID获取雨量计信息
export const getRaingageByIdAxios = (id) => request.get(`/swmm/raingage/${id}`)

// 通过雨量计ID更新雨量计信息
export const updateRaingageByIdAxios = (id, data) => request.put(`/swmm/raingage/${id}`, data)

// 创建新的雨量计
export const createRaingageAxios = (data) => request.post('/swmm/raingage', data)

// 删除雨量计
export const deleteRaingageByIdAxios = (id) => request.delete(`/swmm/raingage/${id}`)
