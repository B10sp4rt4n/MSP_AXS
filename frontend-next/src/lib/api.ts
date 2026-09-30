/**
 * Cliente HTTP para el backend AX-S.
 * Adjunta automáticamente el token de Clerk en cada request.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://web-production-ed4f3.up.railway.app";

type RequestOptions = {
  method?: string;
  body?: unknown;
  token: string;
};

async function request<T>(path: string, { method = "GET", body, token }: RequestOptions): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    const detail: unknown = error.detail;
    const message = typeof detail === "string" ? detail
      : Array.isArray(detail) ? detail.map(item => {
          if (typeof item === "string") return item;
          if (item && typeof item === "object" && "msg" in item && typeof item.msg === "string") {
            return item.msg.replace(/^Value error, /, "");
          }
          return "";
        }).filter(Boolean).join("; ")
      : "";
    throw new Error(message || `Error ${res.status}`);
  }

  return res.json();
}

export const api = {
  get: <T>(path: string, token: string) => request<T>(path, { token }),
  post: <T>(path: string, body: unknown, token: string) => request<T>(path, { method: "POST", body, token }),
  put: <T>(path: string, body: unknown, token: string) => request<T>(path, { method: "PUT", body, token }),
  patch: <T>(path: string, body: unknown, token: string) => request<T>(path, { method: "PATCH", body, token }),
  delete: <T>(path: string, token: string) => request<T>(path, { method: "DELETE", token }),
};
