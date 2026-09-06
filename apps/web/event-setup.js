const setupParams = new URLSearchParams(location.search);
const setupEventId = setupParams.get('event');
const setupStageId = setupParams.get('stage');
const setupRoot = document.querySelector('#setup-page');
let setupState;

document.querySelector('#setup-governance').href = `./governance.html?event=${encodeURIComponent(setupEventId || '')}`;

const setupEsc = value => String(value ?? '').replace(/[&<>"]/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[char]));
const optional = value => value.trim() || null;

function entry(type, value = {}) {
  const row = document.createElement('div');
  row.className = `entry-row ${type}`;
  if (type === 'invite') row.innerHTML = `<input data-field="display_name" aria-label="Invite display name" placeholder="Name" value="${setupEsc(value.display_name)}"><input data-field="email" type="email" aria-label="Invite email" placeholder="Email" value="${setupEsc(value.email)}"><input data-field="intended_role_text" aria-label="Intended role" placeholder="Intended role" value="${setupEsc(value.intended_role_text)}"><button class="remove" type="button" aria-label="Remove invite">×</button><input class="wide" data-field="phone" aria-label="Invite phone" placeholder="Phone (optional)" value="${setupEsc(value.phone)}"><input class="wide" data-field="note" aria-label="Invite note" placeholder="Note (optional)" value="${setupEsc(value.note)}">`;
  if (type === 'support') row.innerHTML = `<input data-field="name" required aria-label="Support name" placeholder="Name" value="${setupEsc(value.name)}"><select data-field="type" aria-label="Support type"><option value="SPONSOR">Sponsor</option><option value="SUPPORT_PARTNER">Support partner</option></select><input data-field="website_url" type="url" aria-label="Support website" placeholder="Website URL" value="${setupEsc(value.website_url)}"><button class="remove" type="button" aria-label="Remove support">×</button><input class="wide" data-field="description" aria-label="Support description" placeholder="Description" value="${setupEsc(value.description)}"><input class="wide" data-field="logo_url" type="url" aria-label="Support logo URL" placeholder="Logo URL" value="${setupEsc(value.logo_url)}"><label class="wide"><input data-field="visibility_enabled" type="checkbox" ${value.visibility_enabled?'checked':''}> Publicly visible</label>`;
  if (type === 'resource') row.innerHTML = `<input data-field="name" required aria-label="Resource name" placeholder="Resource need" value="${setupEsc(value.name)}"><input data-field="category" aria-label="Resource category" placeholder="Category" value="${setupEsc(value.category)}"><input data-field="quantity" type="number" min="0.01" step="any" aria-label="Resource quantity" placeholder="Qty" value="${setupEsc(value.quantity)}"><input data-field="unit" aria-label="Resource unit" placeholder="Unit" value="${setupEsc(value.unit)}"><button class="remove" type="button" aria-label="Remove resource">×</button><input class="wide" data-field="note" aria-label="Resource note" placeholder="Note" value="${setupEsc(value.note)}">`;
  if (type === 'link') row.innerHTML = `<input data-field="label" required aria-label="Contribution link label" placeholder="Label" value="${setupEsc(value.label)}"><input data-field="provider" aria-label="Contribution provider" placeholder="Provider" value="${setupEsc(value.provider)}"><input data-field="external_url" required type="url" aria-label="External contribution URL" placeholder="https://…" value="${setupEsc(value.external_url)}"><button class="remove" type="button" aria-label="Remove link">×</button><input class="wide" data-field="purpose" aria-label="Contribution purpose" placeholder="Purpose" value="${setupEsc(value.purpose)}"><label class="wide"><input data-field="visibility_enabled" type="checkbox" ${value.visibility_enabled?'checked':''}> Publicly visible</label>`;
  const typeSelect = row.querySelector('[data-field="type"]');
  if (typeSelect) typeSelect.value = value.type || 'SPONSOR';
  row.querySelector('.remove').onclick = () => row.remove();
  return row;
}

function fillList(type, values) {
  const host = document.querySelector(`#${type}-list`);
  host.innerHTML = '';
  values.forEach(value => host.append(entry(type, value)));
  if (!values.length) host.innerHTML = `<div class="empty-entry">No entries yet</div>`;
}

function renderSetup() {
  fillList('invite', setupState.initial_invites);
  fillList('support', setupState.sponsors_support);
  fillList('resource', setupState.resources);
  fillList('link', setupState.contribution_links);
  document.querySelector('#map-enabled').checked = setupState.map_settings.map_enabled;
  document.querySelector('#default-view').value = setupState.map_settings.default_view || '';
  document.querySelectorAll('[name="dimension"]').forEach(input => input.checked = setupState.map_settings.participation_dimensions.includes(input.value));
  const privacy = setupState.privacy_settings;
  document.querySelector('#event-visibility').value = privacy.event_visibility;
  document.querySelector('#show-counts').checked = privacy.show_participant_counts;
  document.querySelector('#show-tree').checked = privacy.show_actor_tree;
  document.querySelector('#show-sponsors').checked = privacy.show_sponsors;
  document.querySelector('#show-resources').checked = privacy.show_resources;
  document.querySelector('#show-links').checked = privacy.show_payment_links;
  document.querySelector('#setup-version').textContent = setupState.version;
  document.querySelector('#setup-status').textContent = setupState.version ? 'Saved' : 'Not saved';
}

function values(type) {
  return [...document.querySelectorAll(`#${type}-list .entry-row`)].map(row => {
    const read = name => row.querySelector(`[data-field="${name}"]`);
    if (type === 'invite') return {display_name:optional(read('display_name').value),email:optional(read('email').value),phone:optional(read('phone').value),note:optional(read('note').value),intended_role_text:optional(read('intended_role_text').value),status:'DRAFT'};
    if (type === 'support') return {name:read('name').value.trim(),type:read('type').value,description:optional(read('description').value),website_url:optional(read('website_url').value),logo_url:optional(read('logo_url').value),visibility_enabled:read('visibility_enabled').checked};
    if (type === 'resource') return {name:read('name').value.trim(),category:optional(read('category').value),quantity:read('quantity').value?Number(read('quantity').value):null,unit:optional(read('unit').value),note:optional(read('note').value)};
    return {label:read('label').value.trim(),provider:optional(read('provider').value),external_url:read('external_url').value.trim(),purpose:optional(read('purpose').value),visibility_enabled:read('visibility_enabled').checked};
  });
}

function snapshot() {
  return {
    initial_invites: values('invite'),
    sponsors_support: values('support'),
    resources: values('resource'),
    contribution_links: values('link'),
    map_settings: {map_enabled:document.querySelector('#map-enabled').checked,default_view:optional(document.querySelector('#default-view').value),participation_dimensions:[...document.querySelectorAll('[name="dimension"]:checked')].map(input=>input.value)},
    privacy_settings: {event_visibility:document.querySelector('#event-visibility').value,show_participant_counts:document.querySelector('#show-counts').checked,show_actor_tree:document.querySelector('#show-tree').checked,show_sponsors:document.querySelector('#show-sponsors').checked,show_resources:document.querySelector('#show-resources').checked,show_payment_links:document.querySelector('#show-links').checked},
  };
}

async function loadSetup() {
  setupState = await api(`/events/${setupEventId}/setup`);
  renderSetup();
}

async function initializeSetup() {
  if (!getToken() || !setupEventId) { location.replace('./signin.html'); return; }
  try {
    const [account, workspace] = await Promise.all([api('/auth/me'), api(`/events/${setupEventId}/stage-plan-workspace`)]);
    document.querySelector('#setup-account-name').textContent = account.display_name;
    document.querySelector('#setup-account-type').textContent = account.account_type === 'ORGANIZATION' ? 'Organization' : 'Individual';
    document.querySelector('#setup-avatar').textContent = account.display_name.charAt(0).toUpperCase();
    document.querySelector('#setup-event-name').textContent = workspace.event.name;
    document.querySelector('#setup-back').href = setupStageId ? `./actor-tree.html?event=${encodeURIComponent(setupEventId)}&stage=${encodeURIComponent(setupStageId)}` : './app.html';
    await loadSetup();
    setupRoot.hidden = false;
  } catch (error) {
    document.querySelector('#setup-message').textContent = error.message;
    document.querySelector('#setup-message').className = 'error';
    setupRoot.hidden = false;
  }
}

document.querySelectorAll('[data-add]').forEach(button => button.onclick = () => {
  const type = button.dataset.add;
  const host = document.querySelector(`#${type}-list`);
  host.querySelector('.empty-entry')?.remove();
  host.append(entry(type));
});

document.querySelector('#setup-form').onsubmit = async event => {
  event.preventDefault();
  if (!event.currentTarget.reportValidity()) return;
  const button = document.querySelector('#save-setup');
  const message = document.querySelector('#setup-message');
  button.disabled = true;
  message.textContent = 'Saving…';
  message.className = '';
  try {
    setupState = await api(`/events/${setupEventId}/setup`, {method:'PUT',body:JSON.stringify({...snapshot(),expected_version:setupState.version,idempotency_key:crypto.randomUUID()})});
    renderSetup();
    message.textContent = 'Settings saved.';
  } catch (error) {
    if (error.status === 409) {
      await loadSetup();
      message.textContent = 'These settings changed elsewhere. The latest saved version was reloaded; review your changes before saving again.';
    } else message.textContent = error.message;
    message.className = 'error';
  } finally { button.disabled = false; }
};

initializeSetup();
