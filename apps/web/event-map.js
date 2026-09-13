(function(global){
  'use strict';

  const SUPPORTED_TYPES=new Set([
    'EVENT','ACTOR','RESOURCE','SPONSOR','SUPPORT_PARTNER',
    'ACCESS_POINT','PARKING','MEETING_POINT','TRANSPORT'
  ]);
  const FILTERS=[
    ['entity_type','marker_type','Marker Type'],
    ['area_label','area_label','Area'],
    ['role','role','Role'],
    ['organization','organization','Organization'],
    ['profession','profession','Profession'],
    ['resource_type','resource_type','Resource Type']
  ];
  const COLORS={
    EVENT:'#0b5ed7',ACTOR:'#159a5b',RESOURCE:'#e28a16',SPONSOR:'#7b4bd1',
    SUPPORT_PARTNER:'#9b59b6',ACCESS_POINT:'#167d91',PARKING:'#52657a',
    MEETING_POINT:'#d45375',TRANSPORT:'#9b5b20'
  };
  let googlePromise,configuredMapId;

  function text(value){return value==null?'':String(value)}

  async function loadGoogleMaps(){
    if(global.google?.maps)return global.google.maps;
    if(googlePromise)return googlePromise;
    googlePromise=(async()=>{
      const apiKey=global.HATCOMMWAYS_GOOGLE_MAPS_API_KEY;
      const mapId=global.HATCOMMWAYS_GOOGLE_MAPS_MAP_ID;
      if(!apiKey)throw new Error('Google Maps is not configured for this environment.');
      if(!mapId)throw new Error('A Google Maps map ID is not configured for this environment.');
      configuredMapId=mapId;
      return new Promise((resolve,reject)=>{
        const callback='__hatcommwaysGoogleMapsReady';
        global[callback]=()=>{delete global[callback];resolve(global.google.maps)};
        const script=document.createElement('script');
        script.src='https://maps.googleapis.com/maps/api/js?key='+
          encodeURIComponent(apiKey)+'&callback='+callback+'&v=weekly&libraries=marker';
        script.async=true;
        script.onerror=()=>{
          delete global[callback];
          googlePromise=undefined;
          reject(new Error('Google Maps could not be loaded.'));
        };
        document.head.append(script);
      });
    })();
    return googlePromise;
  }

  function fallback(host,message){
    host.replaceChildren();
    const box=document.createElement('div');
    box.className='event-map-fallback';
    box.setAttribute('role','status');
    box.textContent=message;
    host.append(box);
  }

  function addFact(list,label,value){
    if(!value)return;
    const row=document.createElement('div');
    const term=document.createElement('dt');
    const detail=document.createElement('dd');
    term.textContent=label;
    detail.textContent=text(value);
    row.append(term,detail);
    list.append(row);
  }

  function infoContent(marker){
    const card=document.createElement('article');
    card.className='event-map-info';
    const title=document.createElement('strong');
    title.textContent=marker.display_name;
    const kind=document.createElement('small');
    kind.textContent=marker.entity_type.replaceAll('_',' ');
    const facts=document.createElement('dl');
    addFact(facts,'Role',marker.role);
    addFact(facts,'Area',marker.area_label);
    addFact(facts,'Organization',marker.organization);
    addFact(facts,'Profession',marker.profession);
    addFact(facts,'Resource type',marker.resource_type);
    addFact(facts,'Status',marker.status);
    if(['ACCESS_POINT','PARKING','MEETING_POINT','TRANSPORT'].includes(marker.entity_type)){
      addFact(facts,'Instruction',marker.metadata?.instruction);
    }
    card.append(title,kind,facts);
    return card;
  }

  function option(select,value){
    const item=document.createElement('option');
    item.value=value;
    item.textContent=value||'Show All';
    select.append(item);
  }

  async function create(host,model,{filters=false,mapsLoader=loadGoogleMaps}={}){
    if(!host)return null;
    host.setAttribute('aria-busy','true');
    const source=(model?.markers||[]).filter(marker=>SUPPORTED_TYPES.has(marker.entity_type));
    if(!source.length){
      fallback(host,'No visible map locations are available for this event.');
      host.removeAttribute('aria-busy');
      return null;
    }
    let maps,advanced;
    try{maps=await mapsLoader();advanced=await maps.importLibrary('marker')}
    catch(error){
      fallback(host,error.message||'Google Maps is unavailable.');
      host.removeAttribute('aria-busy');
      return null;
    }

    host.replaceChildren();
    const selections={};
    if(filters){
      const toolbar=document.createElement('div');
      toolbar.className='event-map-filters';
      toolbar.setAttribute('aria-label','Map filters');
      FILTERS.forEach(([field,filterKey,label])=>{
        const wrapper=document.createElement('label');
        const caption=document.createElement('span');
        const select=document.createElement('select');
        caption.textContent=label;
        select.setAttribute('aria-label',label);
        option(select,'');
        (model.available_filters?.[filterKey]||[]).forEach(value=>option(select,value));
        select.disabled=select.options.length===1;
        selections[field]=select;
        wrapper.append(caption,select);
        toolbar.append(wrapper);
      });
      host.append(toolbar);
    }
    const canvas=document.createElement('div');
    canvas.className='event-map-canvas';
    canvas.setAttribute('aria-label',model.event?.name+' map');
    host.append(canvas);
    const eventMarker=source.find(marker=>marker.entity_type==='EVENT')||source[0];
    const map=new maps.Map(canvas,{
      center:{lat:eventMarker.latitude,lng:eventMarker.longitude},
      zoom:15,mapId:configuredMapId||'DEMO_MAP_ID',
      mapTypeControl:false,streetViewControl:false,fullscreenControl:filters
    });
    const windowInfo=new maps.InfoWindow();
    const entries=source.map(data=>{
      const pin=new advanced.PinElement({
        background:COLORS[data.entity_type],borderColor:'#ffffff',
        glyphColor:'#ffffff',scale:data.entity_type==='EVENT'?1.25:1
      });
      const marker=new advanced.AdvancedMarkerElement({
        map,position:{lat:data.latitude,lng:data.longitude},title:data.display_name,
        content:pin.element
      });
      marker.addListener('click',()=>{windowInfo.setContent(infoContent(data));windowInfo.open({map,anchor:marker})});
      return {data,marker};
    });

    function matches(data){
      return Object.entries(selections).every(([field,select])=>
        !select.value||text(data[field])===select.value);
    }
    function fit(){
      const visible=entries.filter(entry=>entry.marker.map);
      if(!visible.length)return;
      if(visible.length===1){
        map.setCenter({lat:visible[0].data.latitude,lng:visible[0].data.longitude});
        map.setZoom(15);
        return;
      }
      const bounds=new maps.LatLngBounds();
      visible.forEach(entry=>bounds.extend({
        lat:entry.data.latitude,lng:entry.data.longitude
      }));
      map.fitBounds(bounds,48);
      maps.event.addListenerOnce(map,'idle',()=>{
        if(map.getZoom()>16)map.setZoom(16);
      });
    }
    function applyFilters(){
      windowInfo.close();
      entries.forEach(entry=>{entry.marker.map=matches(entry.data)?map:null});
      fit();
    }
    Object.values(selections).forEach(select=>select.addEventListener('change',applyFilters));
    fit();
    host.removeAttribute('aria-busy');
    return {
      map,
      markerCount:entries.length,
      applyFilters,
      activate(){
        maps.event.trigger(map,'resize');
        fit();
      }
    };
  }

  global.HatcommwaysEventMap={create,infoContent,loadGoogleMaps,getMapId:()=>configuredMapId,SUPPORTED_TYPES};
})(window);
