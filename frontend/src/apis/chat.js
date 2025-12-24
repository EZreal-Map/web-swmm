import request from '@/utils/request'

// 获取模型列表和选中的模型信息
export const getAgentModelInfoAxios = () => request.get('/agent/chat/models')

// 更新选中的模型
export const updateAgentModelAxios = (model) => request.put('/agent/chat/model', { model })
