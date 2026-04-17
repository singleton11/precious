let currentPassword = "changeme";

export function setPassword(pw) {
  currentPassword = pw;
}

export async function api(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    "X-Server-Password": currentPassword,
    ...(options.headers || {}),
  };

  const response = await fetch(path, { ...options, headers });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${response.status}: ${body}`);
  }
  return response.status === 204 ? null : response.json();
}
