import request from '@/utils/request'
import { getStringAfterFirstDash } from '@/utils/convert'

// 获取所有节点的坐标
export const getAllJunctionsAxios = () => request.get('/swmm/junctions')

// 通过节点ID更新节点所有信息
export const updateJunctionByIdAxios = (id, data) =>
  request.put(`/swmm/junction/${getStringAfterFirstDash(id)}`, data)
