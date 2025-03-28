import request from '@/utils/request'

// 获取所有节点的坐标
export const getAllConduitsAxios = () => request.get('/swmm/conduits')
