const API_BASE = window.HATCOMMWAYS_API_BASE || "http://127.0.0.1:8000";
const TOKEN_KEY = "hatcommways_access_token";

function getToken() { return sessionStorage.getItem(TOKEN_KEY); }
function storeToken(token) { sessionStorage.setItem(TOKEN_KEY, token); }
function clearToken() { sessionStorage.removeItem(TOKEN_KEY); }

async function api(path, options = {}) {
  const headers = { ...(options.body ? { "Content-Type": "application/json" } : {}), ...(options.headers || {}) };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  let data = null;
  if (response.status !== 204) {
    const text = await response.text();
    try { data = text ? JSON.parse(text) : null; } catch { data = { detail: text }; }
  }
  if (!response.ok) {
    const error = new Error(readError(data, response.status));
    error.status = response.status;
    throw error;
  }
  return data;
}

function readError(data, status) {
  if (status === 409) return "An account with this email already exists. Try signing in instead.";
  if (status === 401) return "The email or password is incorrect.";
  const detail = data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg.replace(/^Value error, /, "");
  return "Something went wrong. Please try again.";
}

function showMessage(element, message, kind = "error") {
  element.textContent = message;
  element.className = `form-message form-message--${kind} is-visible`;
}

const signupForm = document.querySelector("#signup-form");
if (signupForm) {
  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = document.querySelector("#form-message");
    const button = signupForm.querySelector("button[type=submit]");
    message.className = "form-message";
    if (!signupForm.reportValidity()) return;
    const values = new FormData(signupForm);
    button.disabled = true;
    try {
      await api("/auth/signup", {
        method: "POST",
        body: JSON.stringify({
          display_name: values.get("display_name").trim(),
          email: values.get("email").trim(),
          password: values.get("password"),
          account_type: values.get("account_type"),
        }),
      });
      window.location.assign(`./signin.html?created=1&email=${encodeURIComponent(values.get("email").trim())}`);
    } catch (error) {
      showMessage(message, error.message);
      button.disabled = false;
    }
  });
}

const signinForm = document.querySelector("#signin-form");
if (signinForm) {
  const params = new URLSearchParams(window.location.search);
  if (params.get("email")) signinForm.elements.email.value = params.get("email");
  if (params.get("created") === "1") showMessage(document.querySelector("#form-message"), "Account created. Sign in to continue.", "success");
  signinForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = document.querySelector("#form-message");
    const button = signinForm.querySelector("button[type=submit]");
    message.className = "form-message";
    if (!signinForm.reportValidity()) return;
    const values = new FormData(signinForm);
    button.disabled = true;
    try {
      const session = await api("/auth/signin", { method: "POST", body: JSON.stringify({ email: values.get("email").trim(), password: values.get("password") }) });
      storeToken(session.access_token);
      await api("/auth/me");
      window.location.assign("./app.html");
    } catch (error) {
      clearToken();
      showMessage(message, error.message);
      button.disabled = false;
    }
  });
}

async function initializeApp() {
  if (!getToken()) { window.location.replace("./signin.html"); return; }
  try {
    const account = await api("/auth/me");
    document.querySelector("#account-trigger").textContent = account.display_name;
    document.querySelector("#account-name").textContent = account.display_name;
    document.querySelector("#account-email").textContent = account.email;
    document.querySelector("#account-type").textContent = account.account_type === "ORGANIZATION" ? "Organization account" : "Individual account";
    document.querySelector("#welcome-name").textContent = account.display_name;
    document.querySelector("#app-content").hidden = false;
  } catch {
    clearToken();
    window.location.replace("./signin.html?expired=1");
  }
}

const appContent = document.querySelector("#app-content");
if (appContent) {
  const trigger = document.querySelector("#account-trigger");
  const panel = document.querySelector("#account-panel");
  trigger.addEventListener("click", () => { panel.hidden = !panel.hidden; trigger.setAttribute("aria-expanded", String(!panel.hidden)); });
  document.querySelector("#signout").addEventListener("click", async () => {
    try { await api("/auth/signout", { method: "POST" }); } finally { clearToken(); window.location.replace("./index.html"); }
  });
  initializeApp();
}
