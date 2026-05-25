const SESSION_KEY = "qr_menu_session";

export function getSession() {
  try {
    const rawSession = localStorage.getItem(SESSION_KEY);
    return rawSession ? JSON.parse(rawSession) : null;
  } catch {
    return null;
  }
}

export function setSession(session) {
  localStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

export function clearSession() {
  localStorage.removeItem(SESSION_KEY);
}

export function getAccessToken() {
  return getSession()?.access_token || "";
}

export function getUser() {
  return getSession()?.user || null;
}

export function isAllowedRole(allowedRoles) {
  const user = getUser();
  return Boolean(user?.role && allowedRoles.includes(user.role));
}
