const base = "/api/v1";
let refreshPromise;

export function clearSession() {
  sessionStorage.removeItem("tokens");
}

export function saveSession(tokens) {
  sessionStorage.setItem("tokens", JSON.stringify(tokens));
}

function tokens() {
  try {
    return JSON.parse(sessionStorage.getItem("tokens") || "{}");
  } catch {
    return {};
  }
}

export async function api(path, options = {}, retry = true) {
  const { raw, ...request } = options;
  const headers = { ...request.headers };
  if (tokens().access_token)
    headers.Authorization = `Bearer ${tokens().access_token}`;
  if (request.body && !(request.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
    request.body = JSON.stringify(request.body);
  }
  let response;
  try {
    response = await fetch(base + path, { ...request, headers });
  } catch {
    throw new Error(
      "Cannot reach the server. Check your connection and try again.",
    );
  }
  if (
    response.status === 401 &&
    retry &&
    tokens().refresh_token &&
    !path.startsWith("/auth/")
  ) {
    if (!refreshPromise) {
      refreshPromise = api(
        "/auth/refresh",
        { method: "POST", body: { token: tokens().refresh_token } },
        false,
      )
        .then(saveSession)
        .finally(() => {
          refreshPromise = null;
        });
    }
    try {
      await refreshPromise;
      return api(path, options, false);
    } catch {
      clearSession();
      window.dispatchEvent(new Event("session-expired"));
    }
  }
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    const detail = data.detail;
    const error = new Error(
      typeof detail === "string"
        ? detail
        : detail?.message || "The request could not be completed.",
    );
    error.defects = detail?.errors || data.errors;
    throw error;
  }
  return raw ? response : response.json();
}

export async function download(id, filename) {
  const response = await api(`/conversions/${id}/download`, { raw: true });
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
