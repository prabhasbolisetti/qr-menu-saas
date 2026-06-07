import axios from "axios";

import {
  clearSession,
  getAccessToken
} from "../utils/auth";

export const DEFAULT_API_BASE_URL = "https://qr-menu-backend-feot.onrender.com";

function normalizeBaseUrl(url) {
  return (url || DEFAULT_API_BASE_URL).replace(/\/+$/, "");
}

function splitBaseUrls(value) {
  return (value || "")
    .split(",")
    .map((url) => url.trim())
    .filter(Boolean);
}

function uniqueBaseUrls(urls) {
  const seen = new Set();

  return urls
    .map((url) => normalizeBaseUrl(url))
    .filter((url) => {
      if (seen.has(url)) return false;
      seen.add(url);
      return true;
    });
}

export const API_BASE_URL_CANDIDATES = uniqueBaseUrls([
  import.meta.env.VITE_API_BASE_URL,
  ...splitBaseUrls(import.meta.env.VITE_API_FALLBACK_BASE_URLS),
  DEFAULT_API_BASE_URL,
]);

const api = axios.create({
  baseURL: API_BASE_URL_CANDIDATES[0],
  timeout: 30000,
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
      error.userMessage = "Unable to reach the menu service. Please retry from this QR.";
    }

    return Promise.reject(error);
  }
);

export default api;
