const govEventId = new URLSearchParams(location.search).get('event');
const govRoot = document.querySelector('#governance-page');
let govState;
const esc = value => String(value ?? '').replace(/[&<>"']/g, character => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[character]));
const labels = {NOT_REQUIRED:'Not required',NEEDS_INFORMATION:'Needs information',EVIDENCE_REQUESTED:'Evidence requested',SUBMITTED:'Submitted',UNDER_REVIEW:'Under review',CLEARED:'Cleared',PROVIDED:'Provided',NOT_APPLICABLE:'Not applicable'};
const categories = ['LOCATION_VENUE','PUBLIC_SPACE_PERMISSION','SAFETY_EMERGENCY','TRAFFIC_ACCESS','CROWD_CAPACITY','FOOD_VENDOR','MINORS_SUPERVISION','ANIMALS','EQUIPMENT_TEMPORARY_STRUCTURE','SOUND_NOISE','SPONSOR_COMMERCIAL','OTHER'];

function evidenceMarkup(evidence) {
  if (evidence.evidence_type === 'FILE') {
    const kind = evidence.content_type === 'application/pdf' ? 'PDF' : 'Image';
    return `<li><b>✓ ${esc(evidence.original_filename)}</b><small>${kind} · Uploaded</small>${evidence.label !== evidence.original_filename ? `<small>${esc(evidence.label)}</small>` : ''}</li>`;
  }
  return `<li><b>✓ ${esc(evidence.label)}</b><small>${esc(evidence.evidence_type.replaceAll('_', ' '))} · Submitted</small></li>`;
}

function render() {
  const assessment = govState.assessment;
  document.querySelector('#gov-empty').hidden = !!assessment;
  document.querySelector('#gov-result').hidden = !assessment;
  if (!assessment) return;
  document.querySelector('#gov-status').textContent = labels[assessment.organizer_visible_status] || assessment.organizer_visible_status;
  document.querySelector('#gov-summary').innerHTML = assessment.governance_required ? `<h2>Relevant governance information</h2><p>${esc(assessment.reasoning_summary)}</p>` : '<h2>No additional governance information is currently needed</h2><p>Based on the event information provided, no applicable governance items were identified.</p>';
  const host = document.querySelector('#gov-items');
  host.innerHTML = govState.items.map(item => `<article class="gov-item"><header><h2>${esc(item.label)}</h2><span>${esc(labels[item.status] || item.status)}</span></header>${item.reason ? `<p><b>Why this was suggested:</b> ${esc(item.reason)}</p>` : ''}${item.suggested_documents.length ? `<small>Suggested information or evidence</small><ul>${item.suggested_documents.map(document => `<li>${esc(document)}</li>`).join('')}</ul>` : ''}<small>${item.knowledge_type === 'VERIFIED_REQUIREMENT' ? 'Verified requirement source provided' : 'Guidance only; not presented as a verified legal requirement'}</small>${item.evidence.length ? `<section class="submitted-evidence"><b>Evidence submitted</b><ul>${item.evidence.map(evidenceMarkup).join('')}</ul></section>` : ''}<form class="item-form" data-item="${item.id}"><label>Organizer note<textarea name="organizer_note">${esc(item.organizer_note || '')}</textarea></label><div class="item-actions"><button name="save">Add information</button><button class="secondary" name="evidence" type="button">Add evidence</button><button class="secondary" name="na" type="button">Not applicable</button></div></form><form class="evidence-form" data-evidence-for="${item.id}" hidden><label>Evidence type<select name="evidence_type"><option value="FILE">Upload file</option><option value="URL">URL</option><option value="REFERENCE_NUMBER">Reference number</option><option value="TEXT_CONFIRMATION">Text confirmation</option></select></label><label class="evidence-file">Choose PDF or image<input name="file" type="file" accept=".pdf,.jpg,.jpeg,.png,.webp,application/pdf,image/jpeg,image/png,image/webp"></label><label class="evidence-value" hidden>Evidence value<input name="value_or_reference"></label><label>Evidence label (optional)<input name="label" maxlength="200"></label><label>Note (optional)<textarea name="note" maxlength="2000"></textarea></label><div class="item-actions"><button>Save evidence</button><button class="secondary" name="cancel" type="button">Cancel</button></div></form></article>`).join('');
  host.querySelectorAll('.item-form').forEach(wireItem);
  host.querySelectorAll('.evidence-form').forEach(wireEvidence);
  document.querySelector('#submit-governance').disabled = ['UNDER_REVIEW','SUBMITTED'].includes(assessment.organizer_visible_status);
}

function wireItem(form) {
  form.onsubmit = async event => { event.preventDefault(); await patchItem(form, 'PROVIDED'); };
  form.querySelector('[name="evidence"]').onclick = () => { document.querySelector(`[data-evidence-for="${form.dataset.item}"]`).hidden = false; };
  form.querySelector('[name="na"]').onclick = async () => { const reason = prompt('Why is this not applicable?'); if (reason) await patchItem(form, 'NOT_APPLICABLE', reason); };
}

function wireEvidence(form) {
  const select = form.elements.evidence_type;
  const syncType = () => { const isFile = select.value === 'FILE'; form.querySelector('.evidence-file').hidden = !isFile; form.querySelector('.evidence-value').hidden = isFile; form.elements.file.required = isFile; form.elements.value_or_reference.required = !isFile; };
  select.onchange = syncType;
  form.elements.cancel.onclick = () => { form.reset(); syncType(); form.hidden = true; };
  form.onsubmit = async event => {
    event.preventDefault();
    const button = form.querySelector('button:not([type])'); button.disabled = true;
    try {
      if (select.value === 'FILE') {
        const body = new FormData(); body.append('file', form.elements.file.files[0]); body.append('label', form.elements.label.value.trim()); body.append('note', form.elements.note.value.trim()); body.append('idempotency_key', crypto.randomUUID());
        govState = await api(`/governance/items/${form.dataset.evidenceFor}/evidence`, {method:'POST', body});
      } else {
        govState = await api(`/governance/items/${form.dataset.evidenceFor}/evidence`, {method:'POST', body:JSON.stringify({evidence_type:select.value,label:form.elements.label.value.trim() || 'Organizer evidence',value_or_reference:form.elements.value_or_reference.value.trim(),note:form.elements.note.value.trim() || null,idempotency_key:crypto.randomUUID()})});
      }
      render();
    } catch (error) { document.querySelector('#gov-message').textContent = error.message; button.disabled = false; }
  };
  syncType();
}

async function patchItem(form, status, reason = null) { govState = await api(`/governance/items/${form.dataset.item}`, {method:'PATCH',body:JSON.stringify({expected_assessment_version:govState.assessment.version,organizer_note:form.elements.organizer_note.value || null,status,not_applicable_reason:reason})}); render(); }
async function initialize() { if (!getToken() || !govEventId) { location.replace('./signin.html'); return; } try { const account = await api('/auth/me'); document.querySelector('#gov-account').textContent = account.display_name; const planningRoute = `./planning.html?event=${encodeURIComponent(govEventId)}`; document.querySelector('#continue-planning').href = planningRoute; document.querySelector('#continue-planning-empty').href = planningRoute; govState = await api(`/events/${govEventId}/governance`); render(); govRoot.hidden = false; } catch (error) { document.querySelector('#gov-message').textContent = error.message; govRoot.hidden = false; } }
document.querySelector('#run-governance').onclick = async () => { const button = document.querySelector('#run-governance'); button.disabled = true; try { govState = await api(`/events/${govEventId}/governance-assessment`, {method:'POST'}); render(); } catch (error) { document.querySelector('#gov-message').textContent = error.message; } finally { button.disabled = false; } };
document.querySelector('#show-add').onclick = () => { document.querySelector('#add-item').hidden = false; };
const add = document.querySelector('#add-item'); add.elements.category.innerHTML = categories.map(category => `<option value="${category}">${category.replaceAll('_',' ')}</option>`).join('');
add.onsubmit = async event => { event.preventDefault(); const form = new FormData(add); govState = await api(`/events/${govEventId}/governance/items`, {method:'POST',body:JSON.stringify({label:form.get('label'),category:form.get('category'),authority:form.get('authority') || null,reason:form.get('reason') || null,evidence_reference:form.get('evidence_reference') || null,idempotency_key:crypto.randomUUID()})}); add.reset(); add.hidden = true; render(); };
document.querySelector('#submit-governance').onclick = async () => { govState = await api(`/events/${govEventId}/governance/submit`, {method:'POST',body:JSON.stringify({expected_version:govState.assessment.version,idempotency_key:crypto.randomUUID()})}); render(); };
initialize();
