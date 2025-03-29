import request from '@/utils/request'
import { getStringAfterFirstDash } from '@/utils/convert'

// 获取所有节点的坐标
export const getAllConduitsAxios = () => request.get('/swmm/conduits')

// 通过节点ID更新节点所有信息
export const updateConduitByIdAxios = (id, data) =>
  request.put(`/swmm/conduit/${getStringAfterFirstDash(id)}`, data)
