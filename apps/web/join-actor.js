const joinEventId=new URLSearchParams(location.search).get('event');
const joinRoot=document.querySelector('#join-page');
let joinData;
let joinStep=1;
let advisory;
const jEsc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const jDate=v=>new Date(v).toLocaleString([],{dateStyle:'medium',timeStyle:'short'});
const localInput=v=>{const date=new Date(v);date.setMinutes(date.getMinutes()-date.getTimezoneOffset());return date.toISOString().slice(0,16)};

function chosenOptions(){
  const choices=new Map(selected().map(item=>[item.actor_requirement_id,item]));
  return joinData.options.filter(option=>choices.has(String(option.actor_requirement_id))).map(option=>({...option,preference:choices.get(String(option.actor_requirement_id)).preference}));
}
function selected(){
  return[...document.querySelectorAll('[data-role]:checked')].map(input=>({actor_requirement_id:input.dataset.role,preference:document.querySelector(`[data-preference="${input.dataset.role}"]`).value}));
}
function availability(){
  const type=document.querySelector('[name="availability"]:checked').value;
  const start=document.querySelector('#available-from').value;
  const end=document.querySelector('#available-until').value;
  if(type==='PARTIAL'&&(!start||!end))throw new Error('Choose the start and end of your available time.');
  return{availability_type:type,availability_start:type==='PARTIAL'?new Date(start).toISOString():null,availability_end:type==='PARTIAL'?new Date(end).toISOString():null,max_commitment_minutes:document.querySelector('#max-commitment').value?Number(document.querySelector('#max-commitment').value):null,allow_alternative_work:document.querySelector('#allow-alternative').checked};
}
function availabilityLabel(){
  const value=availability();
  if(value.availability_type==='PARTIAL')return `${jDate(value.availability_start)} — ${jDate(value.availability_end)}`;
  if(value.availability_type==='FLEXIBLE')return 'Flexible availability';
  const choices=chosenOptions();
  return choices.length?`${jDate(Math.min(...choices.map(x=>new Date(x.starts_at))))} — ${jDate(Math.max(...choices.map(x=>new Date(x.ends_at))))}`:'Full work window';
}
function showStep(step){
  joinStep=step;
  document.querySelectorAll('.join-screen').forEach(x=>x.hidden=Number(x.dataset.step)!==step);
  document.querySelectorAll('.join-steps span').forEach((x,i)=>x.classList.toggle('active',i<step));
  document.querySelector('#join-intro').textContent=step===1?'Be part of the change. Choose how you want to contribute to this event.':step===2?'Tell us when you are available. This helps us match you with the right work.':'Review your details and submit your participation request.';
  renderSidebar();
  scrollTo({top:0,behavior:'smooth'});
}
function optionMarkup(option){
  return `<label class="option-row"><input type="checkbox" data-role="${option.actor_requirement_id}"><span><strong>${jEsc(option.work_name)} — ${jEsc(option.role_name)}</strong><small>${jEsc(option.responsibility_summary)}</small><small>◷ ${jDate(option.starts_at)} — ${jDate(option.ends_at)} &nbsp; | &nbsp; Required ${option.minimum_required_count} &nbsp; | &nbsp; Accepted ${option.accepted_count} &nbsp; | &nbsp; Remaining ${option.remaining_count}</small></span><select data-preference="${option.actor_requirement_id}" aria-label="Preference for ${jEsc(option.role_name)}"><option value="PREFERRED">Preferred</option><option value="CAN_ALSO_HELP">Can also help</option></select></label>`;
}
function renderOptions(){
  const groups=joinData.options.reduce((all,x)=>{const key=`${x.stage_order}. ${x.stage_name}`;(all[key]??=[]).push(x);return all},{});
  document.querySelector('#join-options').innerHTML=Object.entries(groups).map(([stage,items])=>`<section class="work-group"><h3>${jEsc(stage)} <small>· ${items.length} roles available</small></h3>${items.map(optionMarkup).join('')}</section>`).join('')||'<p>No confirmed role requirements are available.</p>';
  document.querySelectorAll('[data-role],[data-preference]').forEach(control=>control.addEventListener('change',renderSidebar));
}
function selectedMarkup(){
  return chosenOptions().map(x=>`<article class="summary-role"><strong>${jEsc(x.work_name)} — ${jEsc(x.role_name)}</strong><small>${jEsc(x.responsibility_summary)}</small><small>${x.preference==='PREFERRED'?'Preferred':'Can also help'}</small></article>`).join('');
}
function renderSidebar(){
  if(!joinData)return;
  const choices=chosenOptions();
  const host=document.querySelector('#summary-body');
  host.innerHTML=choices.length?`<div class="summary-event"><strong>Selected Roles (${choices.length})</strong></div>${selectedMarkup()}${joinStep>1?`<div class="summary-availability"><strong>Availability</strong><p>${jEsc(availabilityLabel())}</p></div>`:''}`:'<div class="summary-empty"><strong>No roles selected yet</strong><p>Choose the work you’re interested in from the sections on the left.</p></div>';
  const next=document.querySelector('#primary-next');
  const back=document.querySelector('#sidebar-back');
  next.disabled=joinStep===1&&!choices.length;
  next.textContent=joinStep===1?'Continue to Availability →':joinStep===2?'Continue to Review & Submit →':'Submit Participation Request →';
  document.querySelector('#next-action-copy').textContent=joinStep===1?(choices.length?`${choices.length} role${choices.length===1?'':'s'} selected.`:'Select at least one role to continue.'):joinStep===2?'Review your selected roles and availability next.':'Submit this request for organizer review.';
  back.hidden=joinStep===1;
  back.textContent=joinStep===2?'← Back to Choose Work':'← Back to Availability';
}
function renderReview(){
  document.querySelector('#review-options').innerHTML=selectedMarkup();
  const value=availability();
  document.querySelector('#review-availability').innerHTML=`<p><strong>${jEsc(availabilityLabel())}</strong></p>${value.max_commitment_minutes?`<p>Maximum commitment: ${value.max_commitment_minutes} minutes</p>`:''}${document.querySelector('#join-note').value.trim()?`<p>Note: ${jEsc(document.querySelector('#join-note').value.trim())}</p>`:''}`;
}
async function goToReview(){
  const button=document.querySelector('#primary-next');
  button.disabled=true;
  const originalLabel=button.textContent;
  button.textContent='Checking availability…';
  document.querySelector('#next-action-copy').textContent='Preparing your participation advisory.';
  document.querySelector('#join-error').textContent='';
  try{
    const currentAvailability=availability();
    advisory=await api(`/events/${joinEventId}/participation-advisories`,{method:'POST',body:JSON.stringify({selections:selected(),availability:currentAvailability})});
    document.querySelector('#advisory-status').textContent=advisory.result.overall_advisory.replaceAll('_',' ');
    document.querySelector('#advisory-explanation').textContent=advisory.result.explanation;
    document.querySelector('#advisory-findings').innerHTML=advisory.result.findings.map(x=>`<p class="finding ${x.level}">${jEsc(x.message)}</p>`).join('')||'<p class="finding">No timing conflicts detected.</p>';
    renderReview();
    showStep(3);
  }catch(error){
    document.querySelector('#join-error').textContent=error.message||'The advisory could not be prepared. Please try again.';
    button.textContent=originalLabel;
    button.disabled=false;
    document.querySelector('#next-action-copy').textContent='Review your selected roles and availability next.';
  }
}
async function submitRequest(){
  const agreements=[...document.querySelectorAll('.join-agreement')];
  if(agreements.some(input=>!input.checked)){document.querySelector('#join-error').textContent='Confirm all three statements before submitting.';return}
  const button=document.querySelector('#primary-next');button.disabled=true;
  try{
    await api(`/events/${joinEventId}/participation-requests`,{method:'POST',body:JSON.stringify({advisory_id:advisory.id,note:document.querySelector('#join-note').value.trim()||null,idempotency_key:crypto.randomUUID()})});
    document.querySelector('.join-main').hidden=true;document.querySelector('#join-complete').hidden=false;
  }catch(error){document.querySelector('#join-error').textContent=error.message;button.disabled=false}
}
document.querySelector('#primary-next').onclick=()=>{if(joinStep===1){if(!selected().length)return;showStep(2)}else if(joinStep===2)goToReview();else submitRequest()};
document.querySelector('#sidebar-back').onclick=()=>showStep(joinStep-1);
document.querySelectorAll('[name="availability"]').forEach(input=>input.onchange=()=>{document.querySelector('#partial-window').hidden=input.value!=='PARTIAL'||!input.checked;renderSidebar()});
document.querySelectorAll('#partial-window input,#max-commitment,#allow-alternative,#join-note').forEach(input=>input.addEventListener('input',renderSidebar));

(async()=>{
  if(!getToken()||!joinEventId){location.replace('./signin.html');return}
  try{
    const [account,data,homeResult]=await Promise.all([api('/auth/me'),api(`/events/${joinEventId}/join-options`),api(`/events/${joinEventId}/home`).catch(()=>null)]);
    joinData=data;
    document.querySelector('#join-name').textContent=account.display_name;
    document.querySelector('#join-avatar').textContent=account.display_name[0].toUpperCase();
    document.querySelector('#join-event-name').textContent=data.event.name;
    document.querySelector('#join-event-date').textContent=jDate(data.event.starts_at);
    document.querySelector('#join-event-location').textContent=data.event.location_description;
    document.querySelector('#join-event-category').textContent=data.event.category||'Uncategorized';
    document.querySelector('#join-event-purpose').textContent=data.event.purpose||'Join this community event.';
    document.querySelector('#event-back').href=`./event.html?event=${encodeURIComponent(joinEventId)}`;
    const cover=homeResult?.setup?.cover_image_data_url;
    if(cover)document.querySelector('#join-event-image').style.backgroundImage=`url(${JSON.stringify(cover)})`;
    renderOptions();
    if(data.options.length){document.querySelector('#available-from').value=localInput(Math.min(...data.options.map(x=>new Date(x.starts_at))));document.querySelector('#available-until').value=localInput(Math.max(...data.options.map(x=>new Date(x.ends_at))))}
    renderSidebar();joinRoot.hidden=false;
  }catch(error){document.querySelector('#join-error').textContent=error.message;joinRoot.hidden=false}
})();
