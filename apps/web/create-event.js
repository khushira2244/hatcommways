const WIZARD_KEY = "hatcommways_event_wizard";
const CREATED_KEY = "hatcommways_created_event";
const EVENT_IDEMPOTENCY_KEY = "hatcommways_event_create_idempotency";
const participantOptions = ["Community Members","Volunteers","Students","Families","Organizations","Local Businesses","Experts / Specialists","Other"];
let wizardStep = 1;

function futureDemoDates(now = new Date()) {
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 30);
  const localDate = value => [value.getFullYear(), String(value.getMonth() + 1).padStart(2, "0"), String(value.getDate()).padStart(2, "0")].join("-");
  return { startDate: localDate(start), endDate: localDate(start) };
}

function demoEventFixture(now = new Date()) {
  return {
    name: "Gachibowli Community Lake Cleanup",
    shortPurpose: "Organize a community cleanup around a local lake to remove plastic waste, separate recyclable material, coordinate volunteers, and hand over collected waste to the responsible local authority.",
    category: "Environment", customCategory: "", format: "In Person",
    venue: "Gachibowli Lake", city: "Hyderabad", region: "Telangana", country: "India",
    ...futureDemoDates(now), startTime: "08:00", endTime: "13:00", timezone: "Asia/Kolkata",
    detailedPurpose: "Clean a public-access lake area, remove plastic and recyclable waste, coordinate volunteers safely, and arrange proper collection and disposal with the responsible local authority.",
    scale: "50",
    participants: ["Community Members", "Volunteers", "Organizations", "Experts / Specialists"],
    customParticipant: "",
    resources: "Gloves, trash bags, collection tools, first-aid supplies, drinking water, transport support, and waste collection support.",
    requirements: "Public-space or lake-access permission may be needed. Collected waste must be handed over safely. Participants may work near access roads and should use protective equipment.",
    constraints: "Volunteer availability, weather, safe lake access, nearby traffic, waste collection timing, and coordination with local authorities.",
    outcomes: "Remove visible waste, separate recyclable material, safely hand over collected waste, improve the lake surroundings, and create a reusable cleanup plan.",
    notes: "Avoid disturbing wildlife or entering unsafe lake areas. Coordinate access and waste collection with the responsible local authority.",
    theme: "Professional / Formal", customTheme: "",
  };
}

function applyWizardValues(form, values) {
  form.querySelectorAll('[name="participants"]').forEach(field => { field.checked = values.participants?.includes(field.value) || false; });
  Object.entries(values).forEach(([name, value]) => {
    if (name === "participants") return;
    form.querySelectorAll(`[name="${name}"]`).forEach(field => {
      if (field.type === "radio") field.checked = field.value === value;
      else field.value = value ?? "";
    });
  });
  form.dispatchEvent(new Event("change", { bubbles: true }));
}

function wizardValues(form) { const data = Object.fromEntries(new FormData(form)); data.participants = [...form.querySelectorAll('[name="participants"]:checked')].map(x=>x.value); return data; }
function saveWizard(form) { sessionStorage.setItem(WIZARD_KEY, JSON.stringify(wizardValues(form))); }
function restoreWizard(form) { const saved=JSON.parse(sessionStorage.getItem(WIZARD_KEY)||"null"); if(!saved)return; Object.entries(saved).forEach(([k,v])=>{ if(k==="participants") return v.forEach(x=>form.querySelector(`[name="participants"][value="${CSS.escape(x)}"]`)?.click()); const fields=form.querySelectorAll(`[name="${k}"]`); fields.forEach(f=>{ if(f.type==="radio") f.checked=f.value===v; else f.value=v??""; }); }); }
function setStep(step) { wizardStep=step; document.querySelectorAll('.wizard-step').forEach(x=>x.classList.toggle('is-active',+x.dataset.step===step)); document.querySelectorAll('#stepper li').forEach((x,i)=>{x.classList.toggle('is-active',i+1===step);x.classList.toggle('is-complete',i+1<step)}); document.querySelector('#progress-step').textContent=step; document.querySelector('#progress-fill').style.width=`${step*25}%`; document.querySelector('#back-step').hidden=step===1; document.querySelector('#skip-context').hidden=step!==3; document.querySelector('#continue-step').hidden=step===4; document.querySelector('#create-event').hidden=step!==4; if(step===4) renderReview(); window.scrollTo({top:0,behavior:'smooth'}); }
function visibleValid() { const section=document.querySelector(`.wizard-step[data-step="${wizardStep}"]`); const invalid=[...section.querySelectorAll('[required]')].find(x=>!x.checkValidity()); if(invalid){invalid.reportValidity();return false} if(wizardStep===2){const f=document.querySelector('#event-wizard'); const start=new Date(`${f.startDate.value}T${f.startTime.value}`),end=new Date(`${f.endDate.value}T${f.endTime.value}`); if(end<=start){document.querySelector('#time-error').textContent='End date and time must be after the start.';return false} document.querySelector('#time-error').textContent='';} return true; }
function renderReview(){const d=wizardValues(document.querySelector('#event-wizard')); const category=d.category==='Other'?d.customCategory:d.category; const location=d.format==='Online'?'Online':`${d.venue}, ${d.city}, ${d.region}, ${d.country}`; const sections=[['Basics',`<b>${d.name}</b><span>${d.shortPurpose}</span><span>${category}</span>`],['When & Where',`<span>${d.format}</span><span>${location}</span><span>${d.startDate} ${d.startTime} — ${d.endDate} ${d.endTime}</span><span>${d.timezone}</span>`],['Context',`<span>${d.detailedPurpose}</span><span>${d.scale?`Expected scale: ${d.scale}`:'Scale not specified'}</span><span>${d.participants?.join(', ')||'Participants not specified'}</span>`]]; document.querySelector('#review-summary').innerHTML=sections.map((x,i)=>`<article><button type="button" data-edit="${i+1}">Edit</button><h3>${x[0]}</h3>${x[1]}</article>`).join(''); document.querySelectorAll('[data-edit]').forEach(b=>b.onclick=()=>setStep(+b.dataset.edit));}
function iso(date,time,tz){const suffix=tz==='Asia/Kolkata'?'+05:30':'Z';return `${date}T${time}:00${suffix}`;}
function planningContext(d){
  const optional=value=>value?.trim()||null;
  return {
    detailed_purpose:d.detailedPurpose.trim(),
    expected_scale:d.scale?Number(d.scale):null,
    intended_participants:d.participants,
    custom_intended_participant:d.participants.includes('Other')?optional(d.customParticipant):null,
    known_resources:optional(d.resources),
    known_requirements:optional(d.requirements),
    constraints:optional(d.constraints),
    desired_outcomes:optional(d.outcomes),
    organizer_notes:optional(d.notes),
    theme:d.theme,
    custom_theme:d.theme==='Custom'?optional(d.customTheme):null,
  };
}

const wizard=document.querySelector('#event-wizard');
if(wizard){const host=document.querySelector('#participants');participantOptions.forEach(x=>host.insertAdjacentHTML('beforeend',`<label><input type="checkbox" name="participants" value="${x}"><span>${x}</span></label>`));restoreWizard(wizard); const updateConditions=()=>{const other=wizard.querySelector('[name="category"][value="Other"]').checked;wizard.customCategory.hidden=!other;wizard.customCategory.required=other;const online=wizard.format.value==='Online';document.querySelector('#physical-location').hidden=online;document.querySelector('#location-preview').hidden=online;['venue','city','region','country'].forEach(n=>wizard[n].required=!online);const customParticipantActive=[...wizard.querySelectorAll('[name="participants"]:checked')].some(x=>x.value==='Other');wizard.customParticipant.hidden=!customParticipantActive;wizard.customParticipant.required=customParticipantActive;wizard.customParticipant.disabled=!customParticipantActive;};wizard.addEventListener('change',()=>{updateConditions();saveWizard(wizard)});wizard.addEventListener('input',()=>saveWizard(wizard));updateConditions();document.querySelector('#continue-step').onclick=()=>{if(visibleValid())setStep(wizardStep+1)};document.querySelector('#back-step').onclick=()=>setStep(wizardStep-1);document.querySelector('#skip-context').onclick=()=>{if(wizard.detailedPurpose.checkValidity())setStep(4);else wizard.detailedPurpose.reportValidity()};wizard.addEventListener('submit',async e=>{e.preventDefault();if(wizardStep!==4)return;if(!visibleValid())return;const d=wizardValues(wizard);const button=document.querySelector('#create-event');button.disabled=true;try{const event=await api('/events',{method:'POST',body:JSON.stringify({name:d.name.trim(),purpose:d.shortPurpose.trim(),event_type:d.format,starts_at:iso(d.startDate,d.startTime,d.timezone),ends_at:iso(d.endDate,d.endTime,d.timezone),timezone:d.timezone,location_description:d.format==='Online'?'Online':`${d.venue}, ${d.city}, ${d.region}, ${d.country}`,planning_context:planningContext(d),idempotency_key:sessionStorage.getItem(EVENT_IDEMPOTENCY_KEY)||(()=>{const key=crypto.randomUUID();sessionStorage.setItem(EVENT_IDEMPOTENCY_KEY,key);return key})()})});const account=await api('/auth/me');sessionStorage.setItem(CREATED_KEY,JSON.stringify({event,form:d,createdBy:account.display_name}));sessionStorage.removeItem(WIZARD_KEY);sessionStorage.removeItem(EVENT_IDEMPOTENCY_KEY);location.assign('./event-created.html');}catch(err){showMessage(document.querySelector('#create-error'),err.message);button.disabled=false;}});}

const success=document.querySelector('#success-page');
if(success){(async()=>{if(!getToken()){location.replace('./signin.html');return}try{await api('/auth/me');const saved=JSON.parse(sessionStorage.getItem(CREATED_KEY)||'null');if(!saved){location.replace('./app.html');return}const {event,form,createdBy}=saved;success.querySelector('#success-summary').innerHTML=`<h2>Event Summary</h2><dl><div><dt>Event Name</dt><dd>${event.name}</dd></div><div><dt>Category</dt><dd>${form.category==='Other'?form.customCategory:form.category}</dd></div><div><dt>Date/Time</dt><dd>${form.startDate} ${form.startTime} — ${form.endDate} ${form.endTime}</dd></div><div><dt>Location</dt><dd>${event.location_description}</dd></div><div><dt>Created By</dt><dd>${createdBy}</dd></div></dl>`;success.querySelector('#continue-planning').href=`./governance.html?event=${event.id}`;success.querySelector('#view-created-event').href=`./event.html?id=${event.id}`;success.hidden=false;}catch{clearToken();location.replace('./signin.html')}})();}

if (wizard) {
  const intendedParticipants = wizard.querySelector("#participants").closest("fieldset");
  const themeSection = document.createElement("fieldset");
  themeSection.className = "theme-section";
  themeSection.innerHTML = `
    <legend>Theme / Naming Style *</legend>
    <p class="field-helper">Choose how AI should name stages, work items, and actor roles for this event.</p>
    <div class="choice-grid themes">
      <label><input type="radio" name="theme" value="Hero / Avengers-style" required><span>Hero / Avengers-style</span></label>
      <label><input type="radio" name="theme" value="Mission / Operations"><span>Mission / Operations</span></label>
      <label><input type="radio" name="theme" value="Community / Neighbor"><span>Community / Neighbor</span></label>
      <label><input type="radio" name="theme" value="Professional / Formal"><span>Professional / Formal</span></label>
      <label><input type="radio" name="theme" value="Festival / Celebration"><span>Festival / Celebration</span></label>
      <label><input type="radio" name="theme" value="Custom"><span>Custom</span></label>
    </div>
    <label class="custom-theme" hidden>Describe your naming style
      <input name="customTheme" placeholder="Space mission / NASA-style" disabled>
    </label>`;
  intendedParticipants.after(themeSection);

  const savedTheme = JSON.parse(sessionStorage.getItem(WIZARD_KEY) || "null");
  if (savedTheme?.theme) {
    const option = wizard.querySelector(`[name="theme"][value="${CSS.escape(savedTheme.theme)}"]`);
    if (option) option.checked = true;
  }
  const customTheme = wizard.customTheme;
  if (savedTheme?.theme === "Custom") customTheme.value = savedTheme.customTheme || "";

  function updateThemeConditions({ clearInactive = false } = {}) {
    const isCustom = wizard.theme.value === "Custom";
    customTheme.closest("label").hidden = !isCustom;
    customTheme.disabled = !isCustom;
    customTheme.required = isCustom;
    if (!isCustom && clearInactive) customTheme.value = "";
  }

  themeSection.addEventListener("change", () => {
    updateThemeConditions({ clearInactive: true });
    saveWizard(wizard);
  });
  themeSection.addEventListener("input", () => saveWizard(wizard));
  updateThemeConditions();

  document.querySelector("#skip-context").onclick = () => {
    if (visibleValid()) setStep(4);
  };

  const renderReviewWithoutTheme = renderReview;
  renderReview = () => {
    renderReviewWithoutTheme();
    const data = wizardValues(wizard);
    const contextReview = document.querySelector("#review-summary article:nth-child(3)");
    const themeValue = document.createElement("span");
    const themeLabel = document.createElement("strong");
    themeLabel.textContent = "Theme / Naming Style:";
    themeValue.append(
      themeLabel,
      document.createTextNode(` ${data.theme}${data.theme === "Custom" ? ` — ${data.customTheme}` : ""}`),
    );
    contextReview.append(themeValue);
  };

  const demoButton = document.querySelector("#fill-demo-event");
  const isLocalDevelopment = ["localhost", "127.0.0.1", "::1"].includes(location.hostname);
  if (isLocalDevelopment) {
    demoButton.hidden = false;
    demoButton.addEventListener("click", () => {
      applyWizardValues(wizard, demoEventFixture());
      updateThemeConditions({ clearInactive: true });
      saveWizard(wizard);
      if (wizardStep === 4) renderReview();
    });
  }
}
