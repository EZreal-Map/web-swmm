import request from '@/utils/request'
import { getStringAfterFirstDash } from '@/utils/convert'

// 获取所有出口的属性
export const getAllOutfallsAxios = () => request.get('/swmm/outfalls')

// 通过出口ID更新出口所有属性
export const updateOutfallByIdAxios = (id, data) =>
  request.put(`/swmm/outfall/${getStringAfterFirstDash(id)}`, data)

// 增加出口
export const createOutfallAxios = (data) => request.post('/swmm/outfall', data)

// 通过出口ID删除出口
export const deleteOutfallByIdAxios = (id) =>
  request.delete(`/swmm/outfall/${getStringAfterFirstDash(id)}`)
