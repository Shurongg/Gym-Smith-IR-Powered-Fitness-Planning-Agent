import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export async function validateKey(apiKey) {
  const { data } = await api.post('/validate-key', { api_key: apiKey })
  return data
}

export async function createSession() {
  const { data } = await api.post('/session')
  return data
}

export async function getSession(token) {
  const { data } = await api.get(`/session/${token}`)
  return data
}

export async function generatePlan(sessionToken, apiKey, userInput) {
  const { data } = await api.post('/plan', {
    session_token: sessionToken,
    api_key: apiKey,
    user_input: userInput,
  })
  return data
}

export async function deletePlan(planId, sessionToken) {
  const { data } = await api.delete(`/plan/${planId}`, { params: { session_token: sessionToken } })
  return data
}
