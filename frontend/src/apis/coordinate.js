import request from '@/utils/request'

// 获取所有节点的坐标
export const getAllNodeCoordinatesAxios = () => request.get('/swmm/coordinates')
