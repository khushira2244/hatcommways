const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const test=require('node:test');

class Element{
  constructor(tag='div'){this.tagName=tag.toUpperCase();this.children=[];this.attributes={};this.listeners={};this.options=[];this.value='';this.disabled=false;this.className='';this.textContent=''}
  append(...children){for(const child of children){this.children.push(child);if(this.tagName==='SELECT'&&child.tagName==='OPTION')this.options.push(child)}}
  replaceChildren(...children){this.children=[];this.options=[];this.append(...children)}
  setAttribute(name,value){this.attributes[name]=String(value)}
  removeAttribute(name){delete this.attributes[name]}
  addEventListener(name,handler){this.listeners[name]=handler}
  dispatch(name){return this.listeners[name]?.({target:this})}
}
class FakeMap{
  constructor(host,options){this.host=host;this.options=options;this.zoom=options.zoom;this.fitCalls=0}
  fitBounds(){this.fitCalls++}
  getZoom(){return this.zoom}
  setZoom(value){this.zoom=value}
  setCenter(value){this.center=value}
}
class FakeMarker{
  static instances=[];
  constructor(options){Object.assign(this,options);this.listeners={};FakeMarker.instances.push(this)}
  addListener(name,handler){this.listeners[name]=handler}
}
class FakePin{constructor(options){this.options=options;this.element=new Element('button')}}
class FakeInfoWindow{
  setContent(value){this.content=value}
  open(value){this.opened=value}
  close(){this.closed=true}
}
class FakeBounds{extend(){}}
const maps={Map:FakeMap,InfoWindow:FakeInfoWindow,LatLngBounds:FakeBounds,
  importLibrary:async()=>({AdvancedMarkerElement:FakeMarker,PinElement:FakePin}),
  event:{addListenerOnce(_map,_name,handler){handler()},trigger(){}}};

function harness(api){
  FakeMarker.instances=[];
  const document={head:new Element('head'),createElement:tag=>new Element(tag)};
  const window={api,document};
  const context=vm.createContext({window,document,encodeURIComponent,Promise,Set,Object,String});
  vm.runInContext(fs.readFileSync('apps/web/event-map.js','utf8'),context);
  return {component:window.HatcommwaysEventMap,document};
}
function model(){
  const types=['EVENT','ACTOR','RESOURCE','SPONSOR','SUPPORT_PARTNER',
    'ACCESS_POINT','PARKING','MEETING_POINT','TRANSPORT'];
  return {
    event:{name:'Synthetic event'},
    markers:types.map((entity_type,index)=>({
      id:'private-'+index,event_id:'private-event',entity_id:'private-entity',
      entity_type,display_name:entity_type+' demo',latitude:23+index/100,
      longitude:85+index/100,area_label:index<2?'Zone A':'Zone B',
      location_precision:'DEMO_APPROXIMATE',
      role:entity_type==='ACTOR'?'Volunteer':null,
      organization:entity_type==='SPONSOR'?'Demo Org':null,
      profession:entity_type==='ACTOR'?'Teacher':null,
      resource_type:entity_type==='RESOURCE'?'Water':null,status:'ACTIVE',
      metadata:{instruction:'Use marked entrance',private_note:'hidden'}
    })),
    available_filters:{marker_type:types,area_label:['Zone A','Zone B'],
      role:['Volunteer'],organization:['Demo Org'],profession:['Teacher'],
      resource_type:['Water']}
  };
}
function flatten(element){
  return element.textContent+element.children.map(flatten).join('');
}

test('renders every supported backend marker and filters in place',async()=>{
  const h=harness(async()=>({google_maps_api_key:'unused'}));
  let reloads=0;
  h.component.SUPPORTED_TYPES.forEach(type=>assert.ok(model().markers.some(m=>m.entity_type===type)));
  const host=new Element();
  const controller=await h.component.create(host,model(),{filters:true,mapsLoader:async()=>maps});
  assert.equal(controller.markerCount,9);
  assert.equal(FakeMarker.instances.length,9);
  const toolbar=host.children[0];
  assert.equal(toolbar.children.length,6);
  const typeSelect=toolbar.children[0].children[1];
  typeSelect.value='ACTOR';
  typeSelect.dispatch('change');
  assert.equal(FakeMarker.instances.filter(marker=>marker.map).length,1);
  assert.equal(FakeMarker.instances.find(marker=>marker.title==='ACTOR demo').map,controller.map);
  assert.equal(reloads,0);
});

test('safe info windows omit coordinates ids and unapproved metadata',()=>{
  const h=harness(async()=>({google_maps_api_key:'unused'}));
  const actor=model().markers.find(marker=>marker.entity_type==='ACTOR');
  const content=flatten(h.component.infoContent(actor));
  assert.match(content,/ACTOR demo/);
  assert.match(content,/Volunteer/);
  assert.match(content,/Zone A/);
  assert.match(content,/Teacher/);
  assert.doesNotMatch(content,/private-|23\.01|85\.01|private_note/);
});

test('missing API key shows a contained fallback without adding a script',async()=>{
  const h=harness(async()=>({google_maps_api_key:null}));
  const host=new Element();
  const result=await h.component.create(host,model());
  assert.equal(result,null);
  assert.match(flatten(host),/not configured/);
  assert.equal(h.document.head.children.length,0);
});

test('event pages load shared map helper and fetch their authorized map',()=>{
  const eventHtml=fs.readFileSync('apps/web/event.html','utf8');
  const actorHtml=fs.readFileSync('apps/web/actor-dashboard.html','utf8');
  const eventJs=fs.readFileSync('apps/web/event-home.js','utf8');
  const actorJs=fs.readFileSync('apps/web/actor-dashboard.js','utf8');
  assert.match(eventHtml,/event-map\.js/);
  assert.match(actorHtml,/event-map\.js/);
  assert.match(eventJs,/\/events\/'\+homeEventId\+'\/map/);
  assert.match(actorJs,/\/events\/'\+eventId\+'\/map/);
  assert.doesNotMatch(eventHtml+actorHtml,/Static map placeholder|No live Google Maps/);
});
