import request from '@/utils/request'
import { getStringAfterFirstDash } from '@/utils/convert'

// 获取所有节点的属性
export const getAllJunctionsAxios = () => request.get('/swmm/junctions')

// 通过节点ID更新节点所有属性
export const updateJunctionByIdAxios = (id, data) =>
  request.put(`/swmm/junction/${getStringAfterFirstDash(id)}`, data)

// 增加节点
export const createJunctionAxios = (data) => request.post('/swmm/junction', data)

// 通过节点ID删除节点
export const deleteJunctionByIdAxios = (id) =>
  request.delete(`/swmm/junction/${getStringAfterFirstDash(id)}`)
