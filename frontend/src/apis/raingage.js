import request from '@/utils/request'

// Get all raingage names
export const getAllRaingageNamesAxios = () => request.get('/swmm/raingage/name')

// Get raingage information by ID
export const getRaingageByIdAxios = (id) => request.get(`/swmm/raingage/${id}`)

// Update raingage information by ID
export const updateRaingageByIdAxios = (id, data) => request.put(`/swmm/raingage/${id}`, data)

// Create a new raingage
export const createRaingageAxios = (data) => request.post('/swmm/raingage', data)

// Delete a raingage by ID
export const deleteRaingageByIdAxios = (id) => request.delete(`/swmm/raingage/${id}`)
