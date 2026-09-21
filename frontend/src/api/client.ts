const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8420";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const isFormData = options.body instanceof FormData;
  const resp = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...(options.body && !isFormData ? { "Content-Type": "application/json" } : {}),
      ...options.headers,
    },
  });
  if (!resp.ok) {
    const text = await resp.text();
    // FastAPI's HTTPException body is {"detail": "..."} — surface that
    // directly rather than the raw JSON, since it's already a message
    // meant to be read by a person.
    let detail: string | undefined;
    try {
      const parsed = JSON.parse(text);
      if (typeof parsed.detail === "string") detail = parsed.detail;
    } catch {
      // not JSON — fall through to the raw-text message below
    }
    throw new Error(detail ?? `${resp.status} ${resp.statusText}: ${text}`);
  }
  if (resp.status === 204) return undefined as T;
  const contentType = resp.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return resp.json();
  }
  return resp.text() as unknown as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body !== undefined ? JSON.stringify(body) : undefined }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PATCH", body: body !== undefined ? JSON.stringify(body) : undefined }),
  del: <T>(path: string) => request<T>(path, { method: "DELETE" }),
  // No Content-Type set here on purpose: the browser fills in
  // "multipart/form-data; boundary=..." itself, which a hardcoded header
  // (like the JSON one above) would break.
  upload: <T>(path: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<T>(path, { method: "POST", body: form });
  },
};

export { API_BASE };
