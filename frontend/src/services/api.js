import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 120000
})

export const getProfile = (ticker) => api.get(`/stocks/${ticker}/profile`)
export const getRatios = (ticker) => api.get(`/stocks/${ticker}/ratios`)
export const getCompetitors = (ticker) => api.get(`/stocks/${ticker}/competitors`)
export const getNews = (ticker) => api.get(`/news/${ticker}`)
export const getAnalysis = (ticker) => api.get(`/analysis/${ticker}`)