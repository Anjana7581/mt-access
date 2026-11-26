
const API =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export async function apiRequest(path, options = {}, token = null) {
  const response = await fetch(`${API}${path}`, {
    ...options,
    headers: {
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  const data = response.status === 204
    ? null
    : await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(
      typeof data?.detail === "string"
        ? data.detail
        : data?.detail?.[0]?.msg || `Request failed (${response.status})`
    );
  }

  return data;
}

export function getToken() {
  return sessionStorage.getItem("mt_access_token");
}

export function saveToken(token) {
  sessionStorage.setItem("mt_access_token", token);
}

export function clearToken() {
  sessionStorage.removeItem("mt_access_token");
}
