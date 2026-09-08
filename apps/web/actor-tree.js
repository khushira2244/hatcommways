const actorParams = new URLSearchParams(location.search);
const actorEventId = actorParams.get('event');
const actorStageId = actorParams.get('stage');
const actorRoot = document.querySelector('#actor-tree-page');
let actorData;
let activeStageId = actorStageId;
let selectedRole = null;
let stagesVisible = true;

const actorEsc = value => String(value ?? '').replace(/[&<>"]/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[char]);
const loadActorTree = () => api(`/events/${actorEventId}/stages/${actorStageId}/actor-tree-workspace`);
const proposalRequirements = item => item.proposal?.status === 'PENDING' ? item.proposal.payload.proposed_requirements : [];
const displayedRequirements = item => proposalRequirements(item).length ? proposalRequirements(item) : item.requirements;

async function initializeActorTree() {
  if (!getToken() || !actorEventId || !actorStageId) {
    location.replace('./signin.html');
    return;
  }
  try {
    const [account, workspace] = await Promise.all([api('/auth/me'), loadActorTree()]);
    actorData = workspace;
    document.querySelector('#actor-name').textContent = account.display_name;
    document.querySelector('#actor-type').textContent = account.account_type === 'ORGANIZATION' ? 'Organization' : 'Individual';
    document.querySelector('#actor-avatar').textContent = account.display_name.charAt(0).toUpperCase();
    const back = `./stage.html?id=${encodeURIComponent(actorStageId)}&event=${encodeURIComponent(actorEventId)}`;
    document.querySelector('#back-inside-stage').href = back;
    document.querySelector('#sidebar-back').href = back;
    renderActorTree();
    actorRoot.hidden = false;
  } catch (error) {
    showActorError(error);
  }
}

function renderActorTree() {
  const items = actorData.work_items;
  const requests = items.map(item => item.actor_requirement_request).filter(Boolean);
  const pending = items.flatMap(proposalRequirements);
  const authoritative = items.flatMap(item => item.requirements);
  const running = requests.some(request => ['REQUESTED', 'RUNNING'].includes(request.status));
  const failed = requests.some(request => request.status === 'FAILED');
  const eventButton = document.querySelector('#event-root');
  const stageHost = document.querySelector('#stage-tree');

  eventButton.innerHTML = `<strong>${actorEsc(actorData.event.name)}</strong><small>Event</small>`;
  eventButton.setAttribute('aria-expanded', String(stagesVisible));
  document.querySelector('.tree-trunk').hidden = !stagesVisible;
  document.querySelector('#actor-status').textContent = running ? 'Generating actor requirements' : pending.length ? 'Actor proposal ready' : authoritative.length ? 'Actor structure confirmed' : failed ? 'Generation failed' : 'Not started';
  document.querySelector('#summary-event').textContent = actorData.event.name;
  stageHost.hidden = !stagesVisible;
  stageHost.style.setProperty('--stage-count', actorData.stages.length);
  stageHost.innerHTML = '';

  actorData.stages.forEach((stage, stageIndex) => {
    const selected = stage.id === activeStageId;
    const hasRoles = stage.id === actorStageId && (pending.length || authoritative.length);
    const branch = document.createElement('section');
    branch.className = `stage-branch${selected ? ' selected' : ''}`;
    branch.style.setProperty('--tree-width', `${actorData.stages.length * 100}%`);
    branch.style.setProperty('--tree-gap', `${(actorData.stages.length - 1) * 16}px`);
    branch.style.setProperty('--role-offset', `${stageIndex * -100}%`);
    branch.style.setProperty('--role-gap-offset', `${stageIndex * -16}px`);

    const stageButton = document.createElement('button');
    stageButton.className = 'stage-node';
    stageButton.type = 'button';
    stageButton.setAttribute('aria-expanded', String(Boolean(selected && hasRoles)));
    stageButton.innerHTML = `<strong>${stage.stage_order}. ${actorEsc(stage.canonical_name)}</strong><small>Stage</small>`;
    stageButton.onclick = () => {
      activeStageId = stage.id;
      selectedRole = null;
      renderActorTree();
    };
    branch.append(stageButton);

    if (selected && hasRoles) {
      const connector = document.createElement('div');
      connector.className = 'role-connector';
      connector.setAttribute('aria-hidden', 'true');
      branch.append(connector);
      const roleList = document.createElement('div');
      const requirements = items.flatMap(displayedRequirements);
      roleList.className = 'role-list';
      roleList.style.setProperty('--role-count', requirements.length);
      requirements.forEach(requirement => {
        const role = document.createElement('button');
        role.className = `role-node${selectedRole === requirement ? ' selected' : ''}`;
        role.type = 'button';
        const people = (actorData.participations || []).filter(person => person.actor_requirement_id === requirement.id);
        role.innerHTML = `<strong>${actorEsc(requirement.canonical_role_name)}</strong><small>Required: ${Number(requirement.minimum_required_count)}</small>${people.map(person => `<small class="approved-person">↳ ${actorEsc(person.display_name)}</small>`).join('')}`;
        role.onclick = () => {
          selectedRole = requirement;
          renderActorTree();
        };
        roleList.append(role);
      });
      branch.append(roleList);
    }
    stageHost.append(branch);
  });

  const activeStage = actorData.stages.find(stage => stage.id === activeStageId);
  document.querySelector('#summary-stage').textContent = activeStage?.canonical_name || '—';
  document.querySelector('#summary-role').textContent = selectedRole?.canonical_role_name || '—';
  document.querySelector('#summary-count').textContent = selectedRole ? Number(selectedRole.minimum_required_count) : '—';
  const button = document.querySelector('#generate-actors');
  button.hidden = pending.length > 0 || authoritative.length > 0;
  button.disabled = running || !items.length;
  if (!items.length) button.title = 'Confirmed work is required before actor requirements can be designed';
  const confirmButton = document.querySelector('#confirm-actor-structure');
  confirmButton.hidden = !pending.length;
  confirmButton.disabled = running;
}

async function generateActorRequirements() {
  const button = document.querySelector('#generate-actors');
  button.disabled = true;
  document.querySelector('#actor-message').textContent = '';
  try {
    for (const item of actorData.work_items) {
      if (item.proposal || item.requirements.length) continue;
      await api(`/work/${item.work.id}/actor-requirement-requests`, {
        method: 'POST',
        body: JSON.stringify({
          event_id: actorEventId,
          stage_id: actorStageId,
          expected_event_version: actorData.event.version,
          expected_stage_version: actorData.selected_stage.version,
          expected_work_version: item.work.version,
          idempotency_key: `actor-requirements:${item.work.id}:${crypto.randomUUID()}`,
        }),
      });
    }
    actorData = await loadActorTree();
    renderActorTree();
  } catch (error) {
    actorData = await loadActorTree();
    renderActorTree();
    showActorError(error);
    button.disabled = false;
  }
}

async function confirmActorStructure() {
  const button = document.querySelector('#confirm-actor-structure');
  const proposals = actorData.work_items
    .map(item => item.proposal)
    .filter(proposal => proposal?.status === 'PENDING');
  button.disabled = true;
  document.querySelector('#actor-message').textContent = '';
  try {
    for (const proposal of proposals) {
      await api(`/actor-requirement-proposals/${proposal.id}/decision`, {
        method: 'POST',
        body: JSON.stringify({
          decision: 'APPROVE',
          decision_idempotency_key: `actor-approval:${proposal.id}`,
        }),
      });
    }
    actorData = await loadActorTree();
    selectedRole = null;
    renderActorTree();
  } catch (error) {
    actorData = await loadActorTree();
    renderActorTree();
    showActorError(error);
  }
}

function showActorError(error) {
  document.querySelector('#actor-message').textContent = error.message;
  actorRoot.hidden = false;
}

document.querySelector('#generate-actors').onclick = generateActorRequirements;
document.querySelector('#confirm-actor-structure').onclick = confirmActorStructure;
document.querySelector('#event-root').onclick = () => {
  stagesVisible = !stagesVisible;
  selectedRole = null;
  renderActorTree();
};
initializeActorTree();
installSaveExit(actorEventId, 'ACTOR_REQUIREMENTS', actorStageId);
