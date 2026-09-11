const q=new URLSearchParams(location.search);
const eventId=q.get('event');
const root=document.querySelector('#actor-dashboard');
let actorPreviewMap,actorFullMap,actorData,humanUpdates=[];
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const when=v=>v?new Date(v).toLocaleString():'Not scheduled';
const empty=t=>'<div class="empty">'+esc(t)+'</div>';
const item=(x,rejected=false)=>'<article class="item '+(rejected?'rejected':'')+'"><b>'+esc(x.work_name||x.title)+'</b>'+(x.role_name?'<small>'+esc(x.role_name)+' · '+esc(x.stage_name||'')+'</small>':'')+(x.approved_start?'<small>'+when(x.approved_start)+' – '+when(x.approved_end)+'</small>':'')+(x.start_time?'<small>'+when(x.start_time)+' – '+when(x.end_time)+' · '+esc(x.location||'Location not set')+' · '+esc(x.status)+'</small>':'')+(x.message?'<small>'+esc(x.message)+'</small>':'')+'</article>';

function render(d,a){
  actorData=d;
  const {event,assignments,meetings,updates,setup,organizer}=d;
  const upcoming=meetings.filter(m=>m.status!=='CANCELLED'&&new Date(m.end_time)>=new Date())[0];
  const primary=assignments[0];
  document.querySelector('#actor-name').textContent=a.display_name;
  document.querySelector('#actor-avatar').textContent=a.display_name[0];
  document.querySelector('#dash-event-name').textContent=event.name;
  document.querySelector('#dash-event-category').textContent=event.category||'Uncategorized';
  document.querySelector('#dash-event-date').textContent=when(event.starts_at);
  document.querySelector('#dash-event-location').textContent=event.location_description;
  document.querySelector('#dash-status').textContent=d.participation_status.replace('_',' ');
  document.querySelector('#dash-role').textContent=primary?.role_name||'No approved role';
  document.querySelector('#dash-role-work').textContent=primary?.work_name||'';
  document.querySelector('#dash-time').textContent=primary?(when(primary.approved_start)+' – '+when(primary.approved_end)):when(event.starts_at);
  document.querySelector('#dash-about').textContent=event.purpose;
  document.querySelector('#dash-facts').textContent=assignments.length+' approved assignment(s) · '+meetings.length+' applicable meeting(s)';
  document.querySelector('#dash-organizer').textContent=organizer?.display_name||'Event organizer';
  const works=assignments.map(x=>item(x)).join('')||empty('No active work assignments.');
  document.querySelector('#overview-work').innerHTML=works;
  document.querySelector('#all-work').innerHTML=works;
  document.querySelector('#rejected-work').innerHTML=d.rejected_selections.map(x=>item(x,true)).join('')||empty('No rejected selections.');
  const ms=meetings.map(x=>item(x)).join('')||empty('No upcoming meetings.');
  document.querySelector('#overview-meetings').innerHTML=ms;
  document.querySelector('#all-meetings').innerHTML=ms;
  const us=updates.map(x=>item(x)).join('')||empty('No messages or updates.');
  document.querySelector('#overview-updates').innerHTML=us;
  document.querySelector('#all-updates').innerHTML=us;
  document.querySelector('#event-info').innerHTML='<p>'+esc(event.purpose)+'</p><p><b>Date:</b> '+when(event.starts_at)+' – '+when(event.ends_at)+'</p><p><b>Location:</b> '+esc(event.location_description)+'</p><p><b>Map:</b> '+(setup?.map_enabled?'Enabled with authorized event locations':'Not enabled')+'</p>';
  const resources=setup?.resources||[];
  document.querySelector('#event-resources').innerHTML=resources.map(r=>'<div class="item"><b>'+esc(r.name)+'</b><small>Need: '+esc(r.quantity??'Not specified')+' '+esc(r.unit||'')+'</small></div>').join('')||empty('No participant resources configured.');
  renderProblems();
  root.hidden=false;
}

function selectedAssignment(){const id=document.querySelector('#update-assignment').value;return actorData.assignments.find(assignment=>String(assignment.id)===id)||actorData.assignments[0]}
function assignmentMeeting(assignment){if(!assignment)return null;return actorData.meetings.find(meeting=>meeting.status!=='CANCELLED'&&(String(meeting.work_id||'')===String(assignment.work_id)||String(meeting.stage_id||'')===String(assignment.stage_id)||String(meeting.actor_requirement_id||'')===String(assignment.actor_requirement_id)))}
function humanUpdateStatus(update){if(update.interpretation_status==='INTERPRETED')return'INTERPRETED';if(update.interpretation_status==='RUNNING')return'UNDER REVIEW';if(update.interpretation_status==='FAILED')return'RECEIVED';return'RECEIVED'}
function renderHumanUpdates(){const host=document.querySelector('#my-human-updates');host.innerHTML=humanUpdates.map(update=>`<details class="human-update-row"><summary><b>${esc(humanUpdateStatus(update))}</b><span>${esc(update.original_text)}</span><time>${when(update.created_at)}</time><i>⌄</i></summary>${update.interpretation?`<p>${esc(update.interpretation.concise_summary)}</p>`:''}</details>`).join('')||empty('You have not submitted any updates for this event.')}
function renderCurrentAssignment(){const assignment=selectedAssignment();const host=document.querySelector('#current-assignment');if(!assignment){host.innerHTML=empty('No accepted assignment is available.');return}const meeting=assignmentMeeting(assignment);host.innerHTML=`<div class="assignment-facts"><span>Stage<b>${esc(assignment.stage_name)}</b></span><span>Work<b>${esc(assignment.work_name)}</b></span><span>Role<b>${esc(assignment.role_name)}</b></span><span>Organizer<b>${esc(actorData.organizer?.display_name||'Event organizer')}</b></span><span>Work window<b>${when(assignment.approved_start)} – ${when(assignment.approved_end)}</b></span><span>Meeting<b>${meeting?`${esc(meeting.title)} · ${when(meeting.start_time)}`:'No relevant meeting yet'}</b></span></div>`}
function renderProblems(){if(!actorData)return;const select=document.querySelector('#update-assignment');select.innerHTML=actorData.assignments.map(assignment=>`<option value="${assignment.id}">${esc(assignment.work_name)} — ${esc(assignment.role_name)}</option>`).join('');document.querySelector('#assignment-picker-wrap').hidden=actorData.assignments.length<2;select.onchange=renderCurrentAssignment;renderCurrentAssignment();renderHumanUpdates();const latest=actorData.updates[0];document.querySelector('#problems-latest-message').innerHTML=latest?item(latest):empty('No organizer message yet.')}

async function initializeActorMaps(mapData){
  [actorPreviewMap,actorFullMap]=await Promise.all([
    HatcommwaysEventMap.create(document.querySelector('#actor-map-preview'),mapData),
    HatcommwaysEventMap.create(document.querySelector('#actor-map-full'),mapData,{filters:true})
  ]);
}

document.querySelectorAll('.dash-nav button').forEach(button=>button.onclick=()=>{
  document.querySelectorAll('.dash-nav button').forEach(item=>item.classList.toggle('active',item===button));
  document.querySelectorAll('.dash-panel').forEach(panel=>panel.hidden=panel.id!=='panel-'+button.dataset.tab);
  if(button.dataset.tab==='info')requestAnimationFrame(()=>actorFullMap?.activate());
});

document.querySelectorAll('[data-update-chip]').forEach(button=>button.onclick=()=>{const textarea=document.querySelector('#human-update-text');textarea.value=button.dataset.updateChip;textarea.focus()});
document.querySelector('#submit-human-update').onclick=async()=>{const button=document.querySelector('#submit-human-update');const textarea=document.querySelector('#human-update-text');const message=document.querySelector('#human-update-message');const text=textarea.value;if(!text.trim()){message.textContent='Describe what changed before submitting.';textarea.focus();return}const assignment=selectedAssignment();if(!assignment){message.textContent='An accepted assignment is required.';return}button.disabled=true;button.textContent='Submitting…';message.textContent='';try{const saved=await api('/events/'+eventId+'/human-updates',{method:'POST',body:JSON.stringify({text,participation_id:assignment.id,idempotency_key:crypto.randomUUID()})});humanUpdates.unshift(saved);textarea.value='';message.textContent='Update submitted. Your update was received. Your current assignment remains unchanged until the organizer approves any plan change.';renderHumanUpdates()}catch(error){message.textContent=error.message}finally{button.disabled=false;button.textContent='Submit Update'}};

(async()=>{
  if(!getToken()){location.replace('./signin.html');return}
  if(!eventId){document.querySelector('#dashboard-error').textContent='Missing event id.';root.hidden=false;return}
  try{
    const [account,data,mapData,updates]=await Promise.all([
      api('/auth/me'),api('/events/'+eventId+'/actor-dashboard'),api('/events/'+eventId+'/map'),api('/events/'+eventId+'/human-updates')
    ]);
    humanUpdates=updates;
    render(data,account);
    await initializeActorMaps(mapData);
  }catch(error){
    document.querySelector('#dashboard-error').textContent=error.message;
    root.hidden=false;
  }
})();
