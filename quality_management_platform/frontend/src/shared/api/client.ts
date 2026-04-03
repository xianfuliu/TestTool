import axios from "axios";

const configuredBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? "").trim();

const api = axios.create({
  baseURL: configuredBaseUrl || "/",
  withCredentials: true,
});

api.interceptors.response.use((response) => {
  if (response.data?.success === false) {
    return Promise.reject(new Error(response.data.message ?? "请求失败"));
  }
  return response;
});

export async function get<T>(url: string, params?: Record<string, unknown>): Promise<T> {
  const response = await api.get(url, { params });
  return response.data.data as T;
}

export async function post<T>(url: string, payload?: Record<string, unknown>): Promise<T> {
  const response = await api.post(url, payload);
  return response.data.data as T;
}

export async function put<T>(url: string, payload?: Record<string, unknown>): Promise<T> {
  const response = await api.put(url, payload);
  return response.data.data as T;
}

export async function del<T>(url: string, params?: Record<string, unknown>): Promise<T> {
  const response = await api.delete(url, { params });
  return response.data.data as T;
}
