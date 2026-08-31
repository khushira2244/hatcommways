const PLANNING_RESULT_KEY = "hatcommways_planning_result";
const PLANNING_IDEMPOTENCY_KEY = "hatcommways_planning_idempotency";
const planningButton = document.querySelector("#continue-planning");
if (planningButton) planningButton.addEventListener("click", async (event) => {
  event.preventDefault();
  const saved = JSON.parse(sessionStorage.getItem("hatcommways_created_event") || "null");
  if (!saved?.event?.id) return;
  planningButton.setAttribute("aria-disabled", "true"); planningButton.textContent = "Starting planning…";
  try {
    let key = sessionStorage.getItem(PLANNING_IDEMPOTENCY_KEY);
    if (!key) { key = crypto.randomUUID(); sessionStorage.setItem(PLANNING_IDEMPOTENCY_KEY, key); }
    const result = await api(`/events/${saved.event.id}/planning-requests`, { method: "POST", body: JSON.stringify({ expected_event_version: saved.event.version, idempotency_key: key }) });
    sessionStorage.setItem(PLANNING_RESULT_KEY, JSON.stringify({ event_id: saved.event.id, event_name: saved.event.name, result }));
    location.assign(`./planning.html?event=${encodeURIComponent(saved.event.id)}`);
  } catch (error) {
    planningButton.removeAttribute("aria-disabled"); planningButton.textContent = "Continue to Planning →";
    let message = document.querySelector("#planning-error");
    if (!message) { message = document.createElement("p"); message.id = "planning-error"; message.className = "form-message form-message--error is-visible"; document.querySelector(".success-actions").after(message); }
    message.textContent = error.message;
  }
});
