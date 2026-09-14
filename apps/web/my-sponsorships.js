/* The API projects public contributions separately from owner-only offers. */
(async function(){
  const $=s=>document.querySelector(s), esc=discoveryEsc;
  const eventUrl=id=>'./event.html?event='+encodeURIComponent(id);
  const name=value=>cleanRanchiEventName(value);
  const date=value=>value?new Date(value).toLocaleDateString(undefined,{dateStyle:'medium'}):'—';
  const status=$('#page-status');
  if(!getToken()){location.replace('./signin.html');return;}
  try{
    const account=await api('/auth/me');
    const isOrganization=account.account_type==='ORGANIZATION';
    if(!isOrganization) $('.app-nav').innerHTML='<a href="./app.html">Explore</a><a href="./my-events.html">My Events</a><a href="./create-event.html">Create Event</a>';
    for(const id of ['account-trigger-name','account-name']) $('#'+id).textContent=account.display_name;
    for(const id of ['account-avatar','menu-avatar']) $('#'+id).textContent=account.display_name.trim().charAt(0).toUpperCase();
    $('#account-email').textContent=account.email;
    $('#account-trigger-type').textContent=isOrganization?'Organization':'Individual';
    $('#account-type').textContent=isOrganization?'Organization account':'Individual account';
    if(isOrganization){const link=$('#account-panel a');link.href='./my-sponsorships.html';link.textContent='My Sponsorships';}
    const panel=$('#account-panel'),trigger=$('#account-trigger');
    const close=()=>{panel.hidden=true;trigger.setAttribute('aria-expanded','false');};
    trigger.onclick=()=>{panel.hidden=!panel.hidden;trigger.setAttribute('aria-expanded',String(!panel.hidden));};
    document.addEventListener('click',e=>{if(!e.target.closest('.account-menu'))close();});
    document.addEventListener('keydown',e=>{if(e.key==='Escape')close();});
    $('#signout').onclick=async()=>{try{await api('/auth/signout',{method:'POST'});}finally{clearToken();location.replace('./index.html');}};
    const sponsorId=new URLSearchParams(location.search).get('sponsor')||account.id;
    const data=await api('/sponsors/'+encodeURIComponent(sponsorId));
    $('#sponsor-heading').textContent=(data.is_owner?'Welcome back, ':'')+data.sponsor.display_name;
    $('#organization-name').textContent=data.sponsor.display_name;
    $('#organization-avatar').textContent=data.sponsor.display_name.split(/\s+/).slice(0,2).map(x=>x[0]).join('');
    const contributions=data.contributions, byEvent=new Map();
    contributions.forEach(c=>{if(!byEvent.has(c.event_id))byEvent.set(c.event_id,c);});
    const events=[...byEvent.values()];
    const types=[...new Set(contributions.map(c=>c.support_type))];
    $('#organization-intro').textContent=types.length?'Supporting community events through '+types.join(', ')+'.':'Supporting community action and local collaboration.';
    $('#sponsor-metrics').innerHTML=`<div><strong>${events.length}</strong><span>Events supported</span></div><div><strong>${contributions.length}</strong><span>Approved contributions</span></div>`;
    $('#highlights').innerHTML=events.slice(0,6).map(e=>`<article class="highlight">${image(e)}<div class="highlight-body"><h3>${esc(name(e.name))}</h3><p>⌖ ${esc(cleanRanchiLocation(e.name,e.location_description))}</p><p>${esc(e.category||'Community')} · ${esc(date(e.starts_at))}</p><p>${esc(e.support_type)}</p><a href="${eventUrl(e.event_id)}">View Event →</a></div></article>`).join('')||'<p>No public approved contributions yet.</p>';
    function image(e){return typeof e.image==='string'&&/^data:image\/(png|jpeg|webp);base64,/.test(e.image)?`<img class="highlight-image" src="${esc(e.image)}" alt="" loading="lazy">`:'<div class="highlight-image" aria-hidden="true">♧</div>';}
    if(data.is_owner&&account.id===data.sponsor.id){
      $('#private-section').hidden=false;
      $('#private-offers').innerHTML=data.offers.map(o=>`<tr><td>${esc(name(o.name))}</td><td>${esc(o.comment||o.support_type)}</td><td><span class="badge badge--${esc(o.status)}">${esc(o.status)}</span></td><td>${esc(date(o.updated_at||o.created_at))}</td><td><a href="${eventUrl(o.event_id)}">View Event</a></td></tr>`).join('')||'<tr><td colspan="5">No sponsorship offers yet. Explore events to offer support.</td></tr>';
    }
    $('#sponsor-content').hidden=false;status.hidden=true;
    const mapped=events.filter(e=>e.latitude!=null&&e.longitude!=null&&Number.isFinite(Number(e.latitude))&&Number.isFinite(Number(e.longitude)));
    if(!mapped.length){$('#map-status').textContent='No public contribution locations available yet.';return;}
    try{
      const maps=await Promise.race([HatcommwaysEventMap.loadGoogleMaps(),new Promise((_,reject)=>setTimeout(()=>reject(new Error('Map unavailable')),12000))]);
      const position=e=>({lat:Number(e.latitude),lng:Number(e.longitude)});
      const map=new maps.Map($('#contribution-map'),{center:position(mapped[0]),zoom:14,mapId:HatcommwaysEventMap.getMapId(),mapTypeControl:false,streetViewControl:false});
      const bounds=new maps.LatLngBounds(),info=new maps.InfoWindow();
      mapped.forEach(e=>{
        const marker=new maps.marker.AdvancedMarkerElement({map,position:position(e),title:name(e.name)});bounds.extend(position(e));
        marker.addListener('click',()=>{const box=document.createElement('div');box.className='map-info';box.innerHTML=`<strong>${esc(name(e.name))}</strong><p>${esc(cleanRanchiLocation(e.name,e.location_description))}</p><p>${esc(e.support_type)} · Approved</p><a href="${eventUrl(e.event_id)}">View Event →</a>`;info.setContent(box);info.open({map,anchor:marker});});
      });
      if(mapped.length>1)map.fitBounds(bounds,36);
      $('#map-status').textContent=`${mapped.length} approved contribution locations. Select a marker to view the event.`;
    }catch{$('#contribution-map').textContent='Contribution map unavailable';$('#contribution-map').classList.add('map-unavailable');$('#map-status').textContent='Map unavailable. Approved events and links are available below.';}
  }catch(error){status.textContent=error.status===404?'Sponsor organization not found.':error.message;}
})();
