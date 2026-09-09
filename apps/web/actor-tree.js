const actorParams = new URLSearchParams(location.search);
const actorEventId = actorParams.get('event');
const actorStageId = actorParams.get('stage'); // Optional return-navigation hint only.
const actorRoot = document.querySelector('#actor-tree-page');
let actorData, activeStageId = actorStageId, selectedRoleKey = null;
let actorBusy = false, actorPoll = null, actorReadVersion = 0;
const actorEsc = value => String(value ?? '').replace(/[&<>"]/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[char]));
const loadActorTree = () => api(`/events/${actorEventId}/actor-tree-workspace`);
function requirementState(item) {
  if (item.requirements.length || item.proposal?.status === 'APPROVED') return 'CONFIRMED';
  if (item.proposal?.status === 'PENDING') return 'PROPOSAL';
  if (['REQUESTED', 'RUNNING'].includes(item.actor_requirement_request?.status)) return 'RUNNING';
  if (item.actor_requirement_request?.status === 'FAILED') return 'FAILED';
  return 'EMPTY';
}
const missingRequirements = item => ['EMPTY', 'FAILED'].includes(requirementState(item));
const stageItems = stageId => actorData.work_items.filter(item => item.work.stage_id === stageId);
function roleEntries(items) {
  return items.flatMap(item => {
    const state = requirementState(item);
    const roles = state === 'CONFIRMED' ? item.requirements : state === 'PROPOSAL' ? item.proposal.payload.proposed_requirements : [];
    return roles.map((role, index) => ({role, state, key: `${item.work.id}:${role.id || `${item.proposal.id}:${index}`}`}));
  });
}
function structureStatus(items) {
  if (!items.length) return 'Work design not completed';
  const states = items.map(requirementState);
  if (states.every(state => state === 'CONFIRMED')) return 'Confirmed';
  if (states.includes('RUNNING')) return 'Generation in progress';
  if (states.includes('FAILED')) return 'Generation failed — retry available';
  if (states.includes('PROPOSAL')) return 'Pending approval';
  return states.includes('CONFIRMED') ? 'Partially confirmed' : 'Not started';
}
function scheduleActorPoll() {
  clearTimeout(actorPoll);
  if (!actorBusy && actorData.work_items.some(item => requirementState(item) === 'RUNNING')) {
    actorPoll = setTimeout(async () => {
      try { await refreshActorTree(); } catch (error) { showActorError(error); }
    }, 2000);
  }
}
async function refreshActorTree() {
  const version = ++actorReadVersion;
  const next = await loadActorTree();
  if (version !== actorReadVersion) return;
  actorData = next;
  if (!actorData.stages.some(stage => stage.id === activeStageId)) activeStageId = actorData.stages[0]?.id;
  renderActorTree();
  scheduleActorPoll();
}
async function initializeActorTree() {
  if (!getToken() || !actorEventId) { location.replace('./signin.html'); return; }
  try {
    const account = await api('/auth/me');
    document.querySelector('#actor-name').textContent = account.display_name;
    document.querySelector('#actor-type').textContent = account.account_type === 'ORGANIZATION' ? 'Organization' : 'Individual';
    document.querySelector('#actor-avatar').textContent = account.display_name.charAt(0).toUpperCase();
    await refreshActorTree();
    actorRoot.hidden = false;
  } catch (error) { showActorError(error); }
}
function renderActorTree() {
  const items = actorData.work_items;
  document.querySelector('#event-root').innerHTML = `<strong>${actorEsc(actorData.event.name)}</strong><small>Event</small>`;
  document.querySelector('#actor-status').textContent = structureStatus(items);
  const host = document.querySelector('#stage-tree');
  host.style.setProperty('--stage-count', Math.max(1, actorData.stages.length));
  host.innerHTML = '';
  actorData.stages.forEach(stage => {
    const entries = roleEntries(stageItems(stage.id));
    const branch = document.createElement('section');
    branch.className = `stage-branch${stage.id === activeStageId ? ' selected' : ''}`;
    branch.dataset.stageId = stage.id;
    const button = document.createElement('button');
    button.className = 'stage-node'; button.type = 'button';
    button.setAttribute('aria-pressed', String(stage.id === activeStageId));
    button.innerHTML = `<strong>${stage.stage_order}. ${actorEsc(stage.canonical_name)}</strong><small>${actorEsc(structureStatus(stageItems(stage.id)))}</small>`;
    button.onclick = () => { activeStageId = stage.id; selectedRoleKey = null; renderActorTree(); };
    branch.append(button);
    const roles = document.createElement('div'); roles.className = 'role-list';
    entries.forEach(entry => {
      const role = document.createElement('button'); role.type = 'button';
      role.className = `role-node${entry.key === selectedRoleKey ? ' selected' : ''}`;
      role.setAttribute('aria-pressed', String(entry.key === selectedRoleKey));
      role.innerHTML = `<strong>${actorEsc(entry.role.canonical_role_name)}</strong><small>Required: ${Number(entry.role.minimum_required_count)}</small>`;
      role.onclick = () => { activeStageId = stage.id; selectedRoleKey = entry.key; renderActorTree(); };
      roles.append(role);
    });
    branch.append(roles); host.append(branch);
  });
  const stage = actorData.stages.find(stage => stage.id === activeStageId);
  const selection = roleEntries(items).find(entry => entry.key === selectedRoleKey);
  document.querySelector('#summary-event').textContent = actorData.event.name;
  document.querySelector('#summary-stage').textContent = stage?.canonical_name || '—';
  document.querySelector('#summary-role').textContent = selection?.role.canonical_role_name || '—';
  document.querySelector('#summary-count').textContent = selection ? selection.role.minimum_required_count : '—';
  document.querySelector('#summary-status').textContent = selection ? ({CONFIRMED:'Confirmed', PROPOSAL:'Pending approval'})[selection.state] : structureStatus(stageItems(activeStageId));
  const generate = document.querySelector('#generate-actors');
  generate.hidden = items.length > 0 && !items.some(missingRequirements);
  generate.disabled = actorBusy || !items.some(missingRequirements);
  const confirm = document.querySelector('#confirm-actor-structure');
  confirm.hidden = !items.some(item => requirementState(item) === 'PROPOSAL');
  confirm.disabled = actorBusy || items.some(item => requirementState(item) === 'RUNNING');
  const next = document.querySelector('#continue-event-setup');
  next.hidden = actorBusy || !items.length || !items.every(item => requirementState(item) === 'CONFIRMED');
  next.href = `./event-setup.html?event=${encodeURIComponent(actorEventId)}`;
  const backStage = actorData.stages.find(stage => stage.id === actorStageId) || stage;
  const back = document.querySelector('#back-inside-stage');
  back.hidden = !backStage;
  if (backStage) back.href = `./stage.html?id=${encodeURIComponent(backStage.id)}&event=${encodeURIComponent(actorEventId)}`;
}
async function actorOperation(operation) {
  if (actorBusy || !actorData) return;
  actorBusy = true; clearTimeout(actorPoll); renderActorTree();
  document.querySelector('#actor-message').textContent = '';
  try { await refreshActorTree(); await operation(); }
  catch (error) { showActorError(error); }
  finally {
    try { await refreshActorTree(); } catch (error) { showActorError(error); }
    actorBusy = false; renderActorTree(); scheduleActorPoll();
  }
}
async function generateActorRequirements() {
  return actorOperation(async () => {
    const candidates = actorData.work_items.filter(missingRequirements).map(item => item.work.id);
    for (const id of candidates) {
      // Refresh before each request so partial progress and other tabs are reused.
      await refreshActorTree();
      const item = actorData.work_items.find(item => item.work.id === id);
      if (!item || !missingRequirements(item)) continue;
      const stage = actorData.stages.find(stage => stage.id === item.work.stage_id);
      const previous = item.actor_requirement_request?.id || 'initial';
      await api(`/work/${id}/actor-requirement-requests`, {
        method:'POST', body:JSON.stringify({
          event_id:actorEventId, stage_id:stage.id,
          expected_event_version:actorData.event.version,
          expected_stage_version:stage.version, expected_work_version:item.work.version,
          idempotency_key:`actor-requirements:${id}:${previous}`,
        }),
      });
    }
  });
}
async function confirmActorStructure() {
  return actorOperation(async () => {
    const proposals = [...new Set(actorData.work_items.filter(item => requirementState(item) === 'PROPOSAL').map(item => item.proposal.id))];
    for (const id of proposals) {
      const result = await api(`/actor-requirement-proposals/${id}/decision`, {
        method:'POST', body:JSON.stringify({decision:'APPROVE', decision_idempotency_key:`actor-approval:${id}`}),
      });
      if (result.status !== 'APPROVED') throw new Error('An actor proposal needs review before it can be confirmed.');
    }
    selectedRoleKey = null;
  });
}
function showActorError(error) {
  document.querySelector('#actor-message').textContent = error.message;
  actorRoot.hidden = false;
}
document.querySelector('#generate-actors').onclick = generateActorRequirements;
document.querySelector('#confirm-actor-structure').onclick = confirmActorStructure;
installSaveExit(actorEventId, 'ACTOR_REQUIREMENTS');
const actorSaveExit = document.querySelector('#save-and-exit');
if (actorSaveExit) {
  actorSaveExit.style.cssText = '';
  document.querySelector('.actor-actions').insertBefore(actorSaveExit, document.querySelector('#back-inside-stage'));
}
initializeActorTree();
