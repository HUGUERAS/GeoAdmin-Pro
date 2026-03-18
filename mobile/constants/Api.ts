// Dev: IP local do computador (descobrir: ipconfig | findstr "IPv4")
// Prod: Railway
export const API_URL = __DEV__
  ? 'http://192.168.1.251:8000'
  : 'https://geo-admin-pro.vercel.app'
