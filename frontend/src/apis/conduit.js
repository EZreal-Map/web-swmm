import request from '@/utils/request'
import { getStringAfterFirstDash } from '@/utils/convert'

// 获取所有渠道的属性
export const getAllConduitsAxios = () => request.get('/swmm/conduits')

// 通过渠道ID更新节点所有属性
export const updateConduitByIdAxios = (id, data) =>
  request.put(`/swmm/conduit/${getStringAfterFirstDash(id)}`, data)

// 增加渠道
export const createConduitAxios = (data) => request.post('/swmm/conduit', data)

// 通过渠道ID删除渠道
export const deleteConduitByIdAxios = (id) =>
  request.delete(`/swmm/conduit/${getStringAfterFirstDash(id)}`)
