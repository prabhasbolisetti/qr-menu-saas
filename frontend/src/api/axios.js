import axios from "axios";

import {
  clearSession,
  getAccessToken
} from "../utils/auth";

const api = axios.create({
  baseURL:
    import.meta.env.VITE_API_BASE_URL ||
    "https://qr-menu-backend-feot.onrender.com",
});

api.interceptors.request.use((config) => {

  const token = getAccessToken();

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

api.interceptors.response.use(

  (response) => response,

  (error) => {

    if (error?.response?.status === 401) {
      clearSession();
    }

    return Promise.reject(error);
  }
);

export default api;