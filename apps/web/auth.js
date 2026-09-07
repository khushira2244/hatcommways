const API_BASE = window.HATCOMMWAYS_API_BASE || "http://127.0.0.1:8000";
const TOKEN_KEY = "hatcommways_access_token";

function getToken() { return sessionStorage.getItem(TOKEN_KEY); }
function storeToken(token) { sessionStorage.setItem(TOKEN_KEY, token); }
function clearToken() { sessionStorage.removeItem(TOKEN_KEY); }

async function api(path, options = {}) {
  const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;
  const headers = { ...(options.body && !isFormData ? { "Content-Type": "application/json" } : {}), ...(options.headers || {}) };
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
  if (status === 409) {
    const detail = data?.detail;
    if (typeof detail === "string" && !detail.toLowerCase().includes("email")) return detail;
    return "An account with this email already exists. Try signing in instead.";
  }
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
    const accountLabel = account.account_type === "ORGANIZATION" ? "Organization" : "Individual";
    const initial = account.display_name.trim().charAt(0).toUpperCase();
    document.querySelector("#account-trigger-name").textContent = account.display_name;
    document.querySelector("#account-trigger-type").textContent = accountLabel;
    document.querySelector("#account-avatar").textContent = initial;
    document.querySelector("#menu-avatar").textContent = initial;
    document.querySelector("#account-name").textContent = account.display_name;
    document.querySelector("#account-email").textContent = account.email;
    document.querySelector("#account-type").textContent = `${accountLabel} account`;
    const welcomeName = document.querySelector("#welcome-name");
    if (welcomeName) welcomeName.textContent = account.display_name;
    document.querySelector("#app-content").hidden = false;
    initializeDiscovery();
  } catch {
    clearToken();
    window.location.replace("./signin.html?expired=1");
  }
}

const DISCOVERY_EVENTS = [
  { id: "lake-cleanup", name: "Hyderabad Lake Cleanup", status: "Planning", date: "5 Sep 2026, Sat · 7:00 AM", location: "Necklace Road, Hyderabad", category: "Environment", people: 32, purpose: "Let's come together to clean our lakes and protect the environment.", x: 62, y: 32 },
  { id: "reading-circle", name: "Community Reading Circle", status: "Upcoming", date: "8 Sep 2026, Tue · 4:30 PM", location: "Jubilee Hills, Hyderabad", category: "Education", people: 18, purpose: "Help children discover stories through a welcoming neighborhood reading circle.", x: 31, y: 46 },
  { id: "health-camp", name: "Neighborhood Health Camp", status: "Confirmed", date: "12 Sep 2026, Sat · 9:00 AM", location: "Secunderabad", category: "Health", people: 24, purpose: "Connect residents with basic health checks and trusted local care resources.", x: 74, y: 19 },
  { id: "food-share", name: "Weekend Food Share", status: "Planning", date: "13 Sep 2026, Sun · 10:00 AM", location: "Banjara Hills, Hyderabad", category: "Community", people: 41, purpose: "Coordinate a respectful community food collection and distribution effort.", x: 38, y: 68 },
  { id: "arts-evening", name: "Open Arts Evening", status: "Upcoming", date: "18 Sep 2026, Fri · 6:00 PM", location: "Begumpet, Hyderabad", category: "Arts & Culture", people: 27, purpose: "Create a shared evening for local artists, families, and community stories.", x: 67, y: 72 },
  { id: "skills-exchange", name: "Community Skills Exchange", status: "Planning", date: "20 Sep 2026, Sun · 11:00 AM", location: "Kukatpally, Hyderabad", category: "Other", people: 15, purpose: "Share practical skills and connect neighbors who can learn from one another.", x: 46, y: 22 },
];

const CATEGORY_ICONS = { All: "▦", Environment: "●", Education: "◆", Health: "♥", Community: "●", "Arts & Culture": "✣", Other: "•••" };
let activeCategory = "All";

function initializeDiscovery() {
  const markerHost = document.querySelector("#event-markers");
  if (!markerHost) return;
  const chipHost = document.querySelector("#category-chips");
  Object.keys(CATEGORY_ICONS).forEach((category) => {
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.category = category;
    button.className = category === "All" ? "is-active" : "";
    button.innerHTML = `<span>${CATEGORY_ICONS[category]}</span>${category}`;
    button.addEventListener("click", () => setCategory(category));
    chipHost.append(button);
  });
  document.querySelector("#category-select").addEventListener("change", (event) => setCategory(event.target.value));
  document.querySelector("#event-search").addEventListener("input", renderMarkers);
  renderMarkers();
}

function setCategory(category) {
  activeCategory = category;
  document.querySelector("#category-select").value = category;
  document.querySelectorAll("#category-chips button").forEach((button) => button.classList.toggle("is-active", button.dataset.category === category));
  renderMarkers();
}

function renderMarkers() {
  const markerHost = document.querySelector("#event-markers");
  const term = document.querySelector("#event-search").value.trim().toLowerCase();
  markerHost.replaceChildren();
  const matches = DISCOVERY_EVENTS.filter((item) => (activeCategory === "All" || item.category === activeCategory) && (!term || `${item.name} ${item.location} ${item.category}`.toLowerCase().includes(term)));
  matches.forEach((item) => {
    const marker = document.createElement("button");
    marker.type = "button";
    marker.className = `event-marker marker-${item.category.toLowerCase().replace(/[^a-z]+/g, "-")}`;
    marker.style.left = `${item.x}%`; marker.style.top = `${item.y}%`;
    marker.setAttribute("aria-label", `Preview ${item.name}`);
    marker.innerHTML = `<span>${CATEGORY_ICONS[item.category]}</span>`;
    marker.addEventListener("click", () => showEventPreview(item));
    markerHost.append(marker);
  });
  if (!matches.length) document.querySelector("#event-preview").hidden = true;
}

function showEventPreview(item) {
  const preview = document.querySelector("#event-preview");
  preview.innerHTML = `<button class="preview-close" type="button" aria-label="Close preview">×</button><span class="preview-status">${item.status}</span><h3>${item.name}</h3><dl><div><dt>Date</dt><dd>${item.date}</dd></div><div><dt>Location</dt><dd>${item.location}</dd></div><div><dt>Category</dt><dd>${item.category}</dd></div><div><dt>People</dt><dd>${item.people} people involved</dd></div></dl><p>${item.purpose}</p><a class="button button--primary" href="./event.html?id=${encodeURIComponent(item.id)}">View Event</a>`;
  preview.hidden = false;
  preview.querySelector(".preview-close").addEventListener("click", () => { preview.hidden = true; });
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
