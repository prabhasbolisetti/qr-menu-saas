import axios from "axios";

import {
  clearSession,
  getAccessToken
} from "../utils/auth";

const DEFAULT_API_BASE_URL = "https://qr-menu-backend-feot.onrender.com";

function normalizeBaseUrl(url) {
  return (url || DEFAULT_API_BASE_URL).replace(/\/+$/, "");
}

const api = axios.create({
  baseURL: normalizeBaseUrl(import.meta.env.VITE_API_BASE_URL),
  timeout: 15000,
});

api.interceptors.request.use((config) => {

  const token = getAccessToken();

  if (config.url && !/^https?:\/\//i.test(config.url) && !config.url.startsWith("/")) {
    config.url = `/${config.url}`;
  }

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

    if (error.code === "ECONNABORTED") {
      error.userMessage = "The server took too long to respond. Please try again.";
    } else if (!error.response) {
      error.userMessage = "Unable to reach the server. Please check your connection.";
    }

    return Promise.reject(error);
  }
);

export default api;
