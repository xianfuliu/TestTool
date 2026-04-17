import axios from "axios";

function extractApiErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as
      | {
          message?: unknown;
          detail?: unknown;
          error?: unknown;
          errors?: unknown;
        }
      | undefined;

    const candidates = [
      data?.message,
      data?.detail,
      data?.error,
      typeof data?.errors === "string" ? data.errors : undefined,
    ];

    for (const candidate of candidates) {
      if (typeof candidate === "string" && candidate.trim()) {
        return candidate;
      }
    }

    if (error.message?.trim()) {
      return error.message;
    }
  }

  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }

  return "请求失败";
}

const configuredBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? "").trim();

const api = axios.create({
  baseURL: configuredBaseUrl || "/",
  withCredentials: true,
});

api.interceptors.response.use(
  (response) => {
    if (response.data?.success === false) {
      return Promise.reject(new Error(typeof response.data.message === "string" ? response.data.message : "请求失败"));
    }
    return response;
  },
  (error) => Promise.reject(new Error(extractApiErrorMessage(error))),
);

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
