import request from '@/utils/request'
import { getStringAfterFirstDash } from '@/utils/convert'

// 获取所有管道的属性
export const getAllConduitsAxios = () => request.get('/swmm/conduits')

// 通过管道ID更新节点所有属性
export const updateConduitByIdAxios = (id, data) =>
  request.put(`/swmm/conduit/${getStringAfterFirstDash(id)}`, data)

// 增加管道
export const createConduitAxios = (data) => request.post('/swmm/conduit', data)

// 通过管道ID删除管道
export const deleteConduitByIdAxios = (id) =>
  request.delete(`/swmm/conduit/${getStringAfterFirstDash(id)}`)
