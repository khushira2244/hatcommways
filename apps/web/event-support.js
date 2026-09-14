/* Sponsor offers own an in-tab workspace. Notifications are only deep links. */
window.HatcommwaysSupport = (() => {
  let eventId, data, state, normal, host, message, mode = 'normal', selected;
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const date = value => value ? new Date(value).toLocaleString() : 'Not specified';
  const path = suffix => `/events/${encodeURIComponent(eventId)}/${suffix}`;
  const organizer = () => data.relationship === 'ORGANIZER';
  const notify = text => { message.textContent = text; };
  async function refresh() { state = await api(path('support-offers')); }
  function routeOffer(id) {
    const url = new URL(location.href);
    url.searchParams.set('tab','resources');
    if(id) url.searchParams.set('offer',id); else url.searchParams.delete('offer');
    history.replaceState(null,'',url);
  }
  function normalMode(text = '') {
    mode = 'normal'; selected = null; routeOffer(null);
    normal.hidden = false; host.hidden = true; host.replaceChildren();
    renderNormal(); notify(text);
  }
  function renderNormal() {
    const old = normal.querySelector('[data-approved-support]'); old?.remove();
    const sponsors = document.createElement('div'); sponsors.dataset.approvedSupport = '';
    sponsors.innerHTML = state.approved.map(o => `<div class="data-row"><div><strong>${esc(o.sponsor_name)}</strong><small>${esc(o.support_type)}${o.quantity ? ` · ${esc(o.quantity)} ${esc(o.resource_snapshot?.unit || '')}` : ''}</small></div><b>APPROVED</b></div>`).join('');
    document.querySelector('#sponsor-list').append(sponsors);
    if(state.approved.length) document.querySelector('#sponsor-list > .is-empty')?.remove();
    document.querySelectorAll('[data-approved-header]').forEach(n=>n.remove());
    if(state.approved.length) document.querySelector('#header-sponsors > .is-empty')?.remove();
    for(const o of [...new Map(state.approved.map(o=>[o.sponsor_account_id,o])).values()]) {
      const badge=document.createElement('span'); badge.dataset.approvedHeader=''; badge.textContent=o.sponsor_name;
      document.querySelector('#header-sponsors').append(badge);
    }
    if(state.needs.length) document.querySelector('#resource-list').innerHTML = state.needs.map(n=>`<div class="data-row"><div><strong>${esc(n.name)}</strong><small>${esc(n.note || n.category || '')}</small></div><div>${n.quantity == null ? 'Quantity not set' : `<strong>${esc(n.pledged)} / ${esc(n.quantity)} ${esc(n.unit || '')}</strong><small>${esc(n.remaining)} remaining</small>`}</div></div>`).join('');
    const actions = normal.querySelector('[data-support-actions]');
    actions.innerHTML = organizer() ? `<button type="button">Review Sponsor Offers (${state.offers.filter(o=>o.status==='PENDING').length})</button>` : '<button type="button">+ Support This Event</button>';
    actions.querySelector('button').onclick = () => organizer() ? review(state.offers[0]?.id) : submitMode();
  }
  function focused(title) {
    normal.hidden=true; host.hidden=false;
    host.innerHTML=`<button type="button" data-back>← Back to Resources &amp; Sponsors</button><h2>${title}</h2><div data-content></div>`;
    host.querySelector('[data-back]').onclick=()=>normalMode();
    notify(''); return host.querySelector('[data-content]');
  }
  function submitMode() {
    mode='submit'; const content=focused('Support This Event'); const key=crypto.randomUUID();
    content.innerHTML=`<form class="info-card support-form"><p>${esc(data.event.name)} · Your offer will be reviewed by the organizer.</p>
      <label>Support type<input name="support_type" required maxlength="100" placeholder="For example, Transport"></label>
      <label>Resource need<select name="resource_need_id"><option value="">General support</option>${state.needs.map(n=>`<option value="${esc(n.id)}">${esc(n.name)}${n.remaining == null ? '' : ` · ${esc(n.remaining)} ${esc(n.unit||'')} remaining`}</option>`).join('')}</select></label>
      <label>Quantity <small data-unit>Select a quantity-based need to contribute units.</small><input name="quantity" type="number" min="0.001" step="0.001" disabled></label>
      <label>Available from (your local time)<input name="availability_start" type="datetime-local"></label><label>Available until (your local time)<input name="availability_end" type="datetime-local"></label>
      <button type="button" data-window>Use event execution window</button>
      <label>Offer details / comment<textarea name="comment" maxlength="2000" rows="4" placeholder="For example, one pickup vehicle and driver for waste transportation."></textarea></label>
      <button type="submit">Submit Support Offer</button></form>`;
    const form=content.querySelector('form'), quantity=form.elements.quantity;
    form.elements.resource_need_id.onchange=()=>{const n=state.needs.find(n=>n.id===form.elements.resource_need_id.value);quantity.disabled=n?.quantity==null;quantity.value='';quantity.max=n?.remaining??'';content.querySelector('[data-unit]').textContent=n?.quantity==null?'Descriptive support only.':`Unit: ${n.unit||'units'} · ${n.remaining} remaining`;};
    content.querySelector('[data-window]').onclick=()=>{for(const [field,value] of [['availability_start',data.event.starts_at],['availability_end',data.event.ends_at]]) {const d=new Date(value);if(!isNaN(d))form.elements[field].value=new Date(d.getTime()-d.getTimezoneOffset()*60000).toISOString().slice(0,16);}};
    form.onsubmit=async e=>{e.preventDefault();const button=form.querySelector('[type=submit]');button.disabled=true;notify('Submitting offer…');try{const body=Object.fromEntries(new FormData(form));body.resource_need_id ||= null;body.quantity=body.quantity?Number(body.quantity):null;for(const name of ['availability_start','availability_end']) body[name]=body[name]?new Date(body[name]).toISOString():null;body.idempotency_key=key;await api(path('support-offers'),{method:'POST',body:JSON.stringify(body)});await refresh();normalMode('Support offer submitted. The organizer will review it.');}catch(error){notify(error.message);button.disabled=false;}};
  }
  function review(id) {
    mode='review';selected=id;routeOffer(id);const content=focused('Sponsor Offer Review');
    const offer=state.offers.find(o=>o.id===id);
    content.innerHTML=`<div class="resource-layout"><aside class="info-card"><h3>Sponsor Offers</h3>${state.offers.map(o=>`<button class="support-offer-row" data-offer="${esc(o.id)}"><strong>${esc(o.sponsor_name)}</strong><small>${esc(o.support_type)} · ${esc(o.resource_snapshot?.name||'General support')}</small><b>${esc(o.status)}</b></button>`).join('')||'<p>No offers yet.</p>'}</aside><article class="info-card" data-detail></article></div>`;
    content.querySelectorAll('[data-offer]').forEach(b=>b.onclick=()=>review(b.dataset.offer));
    const detail=content.querySelector('[data-detail]');
    if(!offer){detail.textContent=id?'This offer is not available in this event.':'Select a sponsor offer.';return;}
    const fit=offer.fit;
    detail.innerHTML=`<h3>${esc(offer.sponsor_name)} <small>${esc(offer.status)}</small></h3><dl><dt>Support type</dt><dd>${esc(offer.support_type)}</dd><dt>Resource</dt><dd>${esc(offer.resource_snapshot?.name||'General support')}</dd><dt>Quantity</dt><dd>${offer.quantity == null ? 'Not specified' : `${esc(offer.quantity)} ${esc(offer.resource_snapshot?.unit||'')}`}</dd><dt>Availability</dt><dd>${esc(date(offer.availability_start))} — ${esc(date(offer.availability_end))}</dd><dt>Comment</dt><dd>${esc(offer.comment||'No comment')}</dd></dl><section class="info-card"><h3>Sponsor Fit ${fit ? `· ${esc(fit.match_level)}` : ''}</h3>${fit?`<p>${esc(fit.summary)}</p><ul>${fit.issues.map(i=>`<li>${esc(i)}</li>`).join('')}</ul>`:`<p>${['FAILED','DEAD_LETTERED'].includes(offer.fit_runtime_status)?'Fit assessment could not be completed. Organizer review remains available.':'Fit assessment is not available yet. Refresh to check. Organizer review remains available.'}</p>`}<button type="button" data-refresh>Refresh offer</button></section>${offer.status==='PENDING'?'<div class="support-decisions"><button type="button" data-decision="REJECTED">Reject</button><button type="button" data-decision="APPROVED">Accept</button></div>':'<p>This offer has already been reviewed.</p>'}`;
    detail.querySelector('[data-refresh]').onclick=async()=>{try{await refresh();review(id);}catch(error){notify(error.message);}};
    detail.querySelectorAll('[data-decision]').forEach(button=>button.onclick=async()=>{const buttons=detail.querySelectorAll('[data-decision]');buttons.forEach(b=>b.disabled=true);try{await api(path(`support-offers/${encodeURIComponent(id)}/decision`),{method:'POST',body:JSON.stringify({decision:button.dataset.decision,expected_version:offer.version})});await refresh();normalMode(button.dataset.decision==='APPROVED'?'Sponsor offer accepted.':'Sponsor offer rejected.');await loadNotifications();}catch(error){notify(error.message);buttons.forEach(b=>b.disabled=false);}});
  }
  async function notifications() {
    if(!organizer())return;
    let notes;
    try { notes=await api(path('support-notifications')); } catch(error) { notify(`Support notifications unavailable: ${error.message}`); return; }
    const list=document.querySelector('#notification-list');
    list.querySelectorAll('[data-sponsor-note]').forEach(n=>n.remove());
    if(notes.length) list.querySelector('.is-empty')?.remove();
    for(const n of notes){const a=document.createElement('a');a.className='notification-request';a.dataset.sponsorNote='';a.href=`./event.html?event=${encodeURIComponent(n.event_id)}&tab=resources&offer=${encodeURIComponent(n.offer_id)}`;a.innerHTML=`<strong>${esc(n.sponsor_name)} offered ${esc(n.support_type)} support</strong><small>${esc(data.event.name)} · ${esc(n.status)}</small>`;list.append(a);}
    document.querySelector('#notification-count').textContent=participationRequests.filter(r=>r.status==='PENDING').length+notes.filter(n=>!n.is_read).length;
  }
  async function configure(options) {
    eventId=options.eventId;data=options.homeData;
    const panel=document.querySelector('#tab-resources');normal=panel.querySelector('.resource-layout');
    host=document.createElement('div');host.hidden=true;panel.append(host);
    message=document.createElement('p');message.setAttribute('role','status');message.setAttribute('aria-live','polite');panel.prepend(message);
    const actions=document.createElement('div');actions.dataset.supportActions='';normal.querySelector('.ways').append(actions);
    try{await refresh();renderNormal();}catch(error){notify(`Support offers unavailable: ${error.message}`);}
  }
  function open(){if(!state)return;const id=new URL(location.href).searchParams.get('offer');if(id&&organizer())review(id);else if(mode==='normal')renderNormal();}
  return {configure,open,notifications};
})();
