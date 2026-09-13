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

function installSaveExit(eventId, currentPhase, stageId = null, beforeExit = null) {
  if (!eventId || document.querySelector('#save-and-exit')) return;
  const button = document.createElement('button');
  button.id = 'save-and-exit';
  button.type = 'button';
  button.className = 'button button--secondary';
  button.textContent = 'Save & Exit';
  button.style.cssText = 'position:fixed;right:20px;bottom:20px;z-index:20';
  button.onclick = async () => {
    button.disabled = true;
    try {
      if (beforeExit) await beforeExit();
      await api(`/events/${eventId}/resume-state`, {method:'PUT',body:JSON.stringify({current_phase:currentPhase,last_open_stage_id:stageId})});
      location.assign('./my-events.html');
    } catch (error) { button.textContent = error.message; button.disabled = false; }
  };
  document.body.append(button);
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
      const session = await api("/auth/signin", {
        method: "POST",
        body: JSON.stringify({
          email: values.get("email").trim(),
          password: values.get("password"),
        }),
      });
      storeToken(session.access_token);
      await api("/auth/me");
      window.location.assign("./app.html");
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

let discoveryEvents = [];
let discoveryMap = null;
let discoveryMapEntries = [];
let discoveryMaps = null;
let discoveryCenter = null;
let selectedDiscoveryId = null;

const CATEGORY_ICONS = { All: "▦", Environment: "●", Education: "◆", Health: "♥", Community: "●", "Arts & Culture": "✣", Other: "•••" };
const DEMO_DISCOVERY_CENTER = Object.freeze({ lat: 23.356542, lng: 85.340022 });
const DISCOVERY_MARKER_STYLES = {
  Environment: { background: "#159a5b", glyph: "●" },
  Animals: { background: "#8b5e3c", glyph: "◆" },
  "Animal Welfare": { background: "#8b5e3c", glyph: "◆" },
  Health: { background: "#e05252", glyph: "♥" },
  Community: { background: "#2f7de1", glyph: "●" },
  Education: { background: "#e58a16", glyph: "◆" },
  "Arts & Culture": { background: "#8051c9", glyph: "✣" },
  Other: { background: "#65748a", glyph: "●" },
};
const discoveryEsc = value => String(value ?? '').replace(/[&<>"']/g, character => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[character]));
let activeCategory = "All";
function normalizeDiscoveryCategory(value) {
  const key = String(value || '').trim().replace(/_/g, ' ').toLowerCase();
  return Object.keys(DISCOVERY_MARKER_STYLES).find(category => category.toLowerCase() === key) || 'Other';
}

async function initializeDiscovery() {
  const markerHost = document.querySelector("#event-markers");
  if (!markerHost) return;
  markerHost.setAttribute('aria-label', 'Event results');
  const chipHost = document.querySelector("#category-chips");
  Object.keys(CATEGORY_ICONS).forEach((category) => {
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.category = category;
    button.className = category === "All" ? "is-active" : "";
    const markerStyle = category === 'All' ? null : discoveryMarkerStyle(category);
    if (markerStyle) button.style.setProperty('--category-color', markerStyle.background);
    button.innerHTML = `<span aria-hidden="true">${markerStyle?.glyph || CATEGORY_ICONS[category]}</span>${category}`;
    button.addEventListener("click", () => setCategory(category));
    chipHost.append(button);
  });
  document.querySelector("#category-select").addEventListener("change", (event) => setCategory(event.target.value));
  document.querySelector("#event-search").addEventListener("input", renderMarkers);
  document.querySelector('.action-card--join')?.addEventListener('click',event=>{event.preventDefault();document.querySelector('#discovery').scrollIntoView({behavior:'smooth',block:'start'});document.querySelector('#event-search').focus({preventScroll:true})});
  try {
    const rows = await api('/events/discover');
    discoveryEvents = rows.map(item => ({...item,category:normalizeDiscoveryCategory(item.category),status:new Date(item.starts_at)>new Date()?'Upcoming':'Open',date:new Date(item.starts_at).toLocaleString([],{dateStyle:'medium',timeStyle:'short'}),location:item.location_description,people:item.participant_count}));
    renderMarkers();
    await initializeDiscoveryMap();
  } catch (error) {
    markerHost.innerHTML = `<p class="discovery-error">${String(error.message||error)}</p>`;
  }
}

function browserLocation(){return new Promise(resolve=>{if(!navigator.geolocation){resolve(null);return}navigator.geolocation.getCurrentPosition(position=>resolve({lat:position.coords.latitude,lng:position.coords.longitude}),()=>resolve(null),{enableHighAccuracy:true,timeout:8000,maximumAge:0})})}
async function geocodeEvent(maps,event){if(event.latitude!=null&&event.longitude!=null)return{lat:event.latitude,lng:event.longitude};try{const result=await new maps.Geocoder().geocode({address:event.location_description});const location=result.results[0]?.geometry?.location;return location?{lat:location.lat(),lng:location.lng()}:null}catch{return null}}
function discoveryMarkerStyle(category){return DISCOVERY_MARKER_STYLES[category]||DISCOVERY_MARKER_STYLES.Other}
async function initializeDiscoveryMap() {
  const host = document.querySelector('#discovery-google-map');
  const status = document.querySelector('#discovery-map-status');
  const locationRequest = browserLocation();
  try {
    const maps = await HatcommwaysEventMap.loadGoogleMaps();
    discoveryMaps = maps;
    const markerLibrary = await maps.importLibrary('marker');
    discoveryCenter = DEMO_DISCOVERY_CENTER;
    discoveryMap = new maps.Map(host, {center: discoveryCenter, zoom: 11,
      mapId: HatcommwaysEventMap.getMapId(), mapTypeControl: false, streetViewControl: false});
    document.querySelector('#map-canvas').classList.add('has-google-map');
    const entries = await Promise.all(discoveryEvents.map(async event => {
      const position = await geocodeEvent(maps, event);
      if (!position) return null;
      const style = discoveryMarkerStyle(event.category);
      const pin = new markerLibrary.PinElement({background: style.background,
        borderColor: '#fff', glyphColor: '#fff', glyph: style.glyph});
      const marker = new markerLibrary.AdvancedMarkerElement({position,
        title: event.name, content: pin.element});
      marker.addListener('click', () => showEventPreview(event));
      return {event, marker, position};
    }));
    discoveryMapEntries = entries.filter(Boolean);
    renderMarkers();
    const current = await locationRequest;
    discoveryCenter = current || DEMO_DISCOVERY_CENTER;
    status.textContent = current ? 'Showing events near your current location.' : 'Using the Ranchi fallback area.';
    // Recenter existing markers; never recreate or clear results after geolocation.
    if (!selectedDiscoveryId) fitDiscoveryBounds();
  } catch (error) {
    status.textContent = 'Interactive map unavailable. Search and event results still work.';
    host.hidden = true;
  }
}

function fitDiscoveryBounds() {
  if (!discoveryMap || !discoveryMaps) return;
  const visible = discoveryMapEntries.filter(entry => entry.marker.map);
  const center = discoveryCenter || DEMO_DISCOVERY_CENTER;
  const nearby = visible.filter(({position}) => {
    const dy = (position.lat - center.lat) * 111.2;
    const dx = (position.lng - center.lng) * 111.2 * Math.cos(center.lat * Math.PI / 180);
    return Math.hypot(dx, dy) <= 30;
  });
  const filtered = activeCategory !== 'All' || document.querySelector('#event-search').value.trim();
  const entries = nearby.length ? nearby : filtered ? visible : [];
  if (!entries.length) { discoveryMap.setCenter(center); discoveryMap.setZoom(12); return; }
  const bounds = new discoveryMaps.LatLngBounds();
  if (nearby.length) bounds.extend(center);
  entries.forEach(entry => bounds.extend(entry.position));
  document.querySelector('#event-preview').hidden = true;
  const list = document.querySelector('#event-markers');
  const mapRect = document.querySelector('#map-canvas').getBoundingClientRect();
  const listRect = list.getBoundingClientRect();
  const overlaysMap = listRect.top < mapRect.bottom && listRect.bottom > mapRect.top;
  discoveryMap.fitBounds(bounds, {top: 80, right: 55, bottom: 90,
    left: overlaysMap ? Math.min(listRect.width + 45, mapRect.width * .45) : 40});
  discoveryMaps.event.addListenerOnce(discoveryMap, 'idle', () => {
    if (discoveryMap.getZoom() > 15) discoveryMap.setZoom(15);
  });
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
  const matches = discoveryEvents.filter((item) => (activeCategory === "All" || item.category === activeCategory) && (!term || `${item.name} ${item.location} ${item.category}`.toLowerCase().includes(term)));
  discoveryMapEntries.forEach(entry=>{entry.marker.map=matches.includes(entry.event)?discoveryMap:null});
  if(!matches.length){selectedDiscoveryId=null;markerHost.innerHTML='<p class="no-events-found">No events found</p>';document.querySelector('#event-preview').hidden=true;fitDiscoveryBounds();return}
  matches.forEach((item) => {
    const marker = document.createElement("button");
    marker.type = "button";
    marker.className = 'discovery-result-button';
    marker.setAttribute("aria-label", `Preview ${item.name}`);
    marker.innerHTML = `<strong>${discoveryEsc(item.name)}</strong><small>${discoveryEsc(item.location)}</small>`;
    marker.addEventListener("click", () => showEventPreview(item));
    markerHost.append(marker);
  });
  selectedDiscoveryId = null;
  document.querySelector('#event-preview').hidden = true;
  fitDiscoveryBounds();
}

function showEventPreview(item) {
  selectedDiscoveryId = item.id;
  const entry = discoveryMapEntries.find(entry => entry.event.id === item.id);
  if (entry && discoveryMap) { discoveryMap.panTo(entry.position); discoveryMap.setZoom(14); }
  const preview = document.querySelector("#event-preview");
  preview.innerHTML = `<button class="preview-close" type="button" aria-label="Close preview">×</button><span class="preview-status">${discoveryEsc(item.status)}</span><h3>${discoveryEsc(item.name)}</h3><dl><div><dt>Date</dt><dd>${discoveryEsc(item.date)}</dd></div><div><dt>Location</dt><dd>${discoveryEsc(item.location)}</dd></div><div><dt>Category</dt><dd>${discoveryEsc(item.category||'Uncategorized')}</dd></div><div><dt>People</dt><dd>${discoveryEsc(item.people)} participating</dd></div></dl><p>${discoveryEsc(item.purpose)}</p><a class="button button--primary" href="./event.html?event=${encodeURIComponent(item.id)}">View Event</a>`;
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
