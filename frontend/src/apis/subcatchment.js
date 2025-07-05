import request from '@/utils/request'
import { getStringAfterFirstDash } from '@/utils/convert'

// 获取子汇水区边界 + 子汇水区（产流）参数
export const getSubcatchmentsAxios = () => {
  return request.get('/swmm/subcatchments')
}

// 通过子汇水区ID更新子汇水区所有属性
export const updateSubcatchmentByIdAxios = (id, data) => {
  const cleanedData = { ...data }
  delete cleanedData.polygon
  return request.put(`/swmm/subcatchment/${getStringAfterFirstDash(id)}`, cleanedData)
}

// 通过子汇水区ID删除子汇水区
export const deleteSubcatchmentByIdAxios = (id) => {
  return request.delete(`/swmm/subcatchment/${getStringAfterFirstDash(id)}`)
}

// 增加子汇水区
export const createSubcatchmentAxios = (data) => {
  return request.post('/swmm/subcatchment', data)
}

// 保存子汇水区边界
export const saveSubcatchmentPolygonAxios = (data) => {
  return request.post('/swmm/subcatchment/polygon', data)
}

// 获取子汇水区下渗模型参数
export const getInfiltrationAxios = (subcatchment_name) => {
  return request.get('/swmm/subcatchments/infiltration', { params: { subcatchment_name } })
}

// 获取子汇水区汇流模型参数
export const getSubareaAxios = (subcatchment_name) => {
  return request.get('/swmm/subcatchments/subarea', { params: { subcatchment_name } })
}

// 更新子汇水区下渗模型参数
export const updateInfiltrationAxios = (data) => {
  return request.put('/swmm/subcatchments/infiltration', data)
}

// 更新子汇水区汇流模型参数
export const updateSubareaAxios = (data) => {
  return request.put('/swmm/subcatchments/subarea', data)
}
