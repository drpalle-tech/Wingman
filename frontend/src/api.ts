import { DEFAULT_BASE_URL, WingmanClient } from '@wingman/client'

export const API_URL = import.meta.env.VITE_API_URL || DEFAULT_BASE_URL

export const api = new WingmanClient(API_URL)
