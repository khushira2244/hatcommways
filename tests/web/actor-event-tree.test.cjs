// Deterministic controller regression; no browser, database or agents required.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');
const base=path.resolve(__dirname,'../../apps/web');
class Element {
 constructor(){this.children=[];this.dataset={};this.style={setProperty(){}};this.hidden=false;this.attrs={};}
 set innerHTML(value){this.html=value;this.children=[]} get innerHTML(){return this.html||''}
 append(node){this.children.push(node)}
 insertBefore(node,before){const index=this.children.indexOf(before);this.children.splice(index<0?this.children.length:index,0,node)}
 setAttribute(key,value){this.attrs[key]=value}
}
function fixture(){return {event:{id:'event-1',name:'Community event',version:5},stages:['a','b','c'].map((id,i)=>({id,stage_order:i+1,canonical_name:`Stage ${id}`,version:2})),work_items:['a','a','b'].map((stage,i)=>({work:{id:`w${i}`,stage_id:stage,version:1},requirements:[],proposal:null,actor_requirement_request:null}))}}
function harness(data=fixture()){
 const nodes={},requests=[],timers=new Map();let timerId=0,failWork=null;
 const document={querySelector:key=>key==='#save-and-exit'&&!nodes[key]?null:(nodes[key]??=new Element()),createElement:()=>new Element(),body:{append:node=>{nodes['#'+node.id]=node}}};
 const location={search:'?event=event-1',assign:url=>location.assigned=url,replace:url=>location.replaced=url};
 const ctx=vm.createContext({document,location,URLSearchParams,console,getToken:()=>true,setTimeout:fn=>{timers.set(++timerId,fn);return timerId},clearTimeout:id=>timers.delete(id),api:async(url,options={})=>{
  requests.push({url,options});
  if(url==='/auth/me')return {display_name:'Owner',account_type:'INDIVIDUAL'};
  if(url.endsWith('/actor-tree-workspace'))return structuredClone(data);
  if(url.endsWith('/resume-state'))return {};
  if(url.includes('/work/')){
   const item=data.work_items.find(item=>url.includes('/'+item.work.id+'/'));
   if(failWork===item.work.id)throw Error('Connection interrupted');
   item.actor_requirement_request={id:'request-'+item.work.id,status:'SUCCEEDED'};
   item.proposal={id:'proposal-'+item.work.id,status:'PENDING',payload:{proposed_requirements:[{canonical_role_name:'Role '+item.work.id,minimum_required_count:2}]}};
   return item.actor_requirement_request;
  }
  if(url.includes('/decision')){
   const item=data.work_items.find(item=>url.includes('/'+item.proposal?.id+'/'));
   item.requirements=item.proposal.payload.proposed_requirements.map((role,index)=>({...role,id:item.work.id+'-'+index,stage_id:item.work.stage_id}));
   item.proposal.status='APPROVED';return {status:'APPROVED'};
  }
  throw Error('Unexpected API request '+url);
 }});
 const auth=fs.readFileSync(path.join(base,'auth.js'),'utf8');vm.runInContext(auth.slice(auth.indexOf('function installSaveExit('),auth.indexOf('const signupForm')),ctx);
 vm.runInContext(fs.readFileSync(path.join(base,'actor-tree.js'),'utf8').replace(/^initializeActorTree\(\);$/m,''),ctx);
 return {nodes,requests,data,location,timers,run:code=>vm.runInContext(code,ctx),async start(){await this.run('initializeActorTree()')},fail(id){failWork=id}};
}
function writes(h){return h.requests.filter(r=>r.options.method)}
test('one event root, sibling stages, roles stay within their stages, incomplete stage visible',async()=>{
 const data=fixture();data.work_items[0].requirements=[{id:'r-a',canonical_role_name:'Coordinator',minimum_required_count:1}];data.work_items[2].proposal={id:'p-b',status:'PENDING',payload:{proposed_requirements:[{canonical_role_name:'Helper',minimum_required_count:3}]}};
 const h=harness(data);await h.start();const branches=h.nodes['#stage-tree'].children;
 assert.equal(branches.length,3);assert.deepEqual(branches.map(b=>b.dataset.stageId),['a','b','c']);
 assert.match(branches[0].children[1].children[0].innerHTML,/Coordinator/);assert.match(branches[1].children[1].children[0].innerHTML,/Helper/);
 assert.equal(branches[2].children[1].children.length,0);assert.match(branches[2].children[0].innerHTML,/Work design not completed/);
 assert.match(h.nodes['#event-root'].innerHTML,/Community event/);assert.equal(h.location.replaced,undefined);assert.equal(writes(h).length,0);
 branches[1].children[1].children[0].onclick();assert.equal(h.nodes['#summary-stage'].textContent,'Stage b');assert.equal(h.nodes['#summary-role'].textContent,'Helper');
});
test('one explicit action generates all missing work once and preserves event/stage IDs',async()=>{
 const h=harness();await h.start();await Promise.all([h.run('generateActorRequirements()'),h.run('generateActorRequirements()')]);
 const generated=writes(h);assert.equal(generated.length,3);assert.deepEqual(generated.map(r=>JSON.parse(r.options.body).stage_id),['a','a','b']);assert.ok(generated.every(r=>JSON.parse(r.options.body).event_id==='event-1'));
 await h.run('generateActorRequirements()');assert.equal(writes(h).length,3);assert.equal(h.nodes['#confirm-actor-structure'].hidden,false);
});
test('confirmed, pending, running and approved empty structures are reused',async()=>{
 const data=fixture();data.work_items[0].proposal={id:'empty-approved',status:'APPROVED',payload:{proposed_requirements:[]}};
 data.work_items[1].actor_requirement_request={id:'running',status:'RUNNING'};
 data.work_items[2].proposal={id:'empty-pending',status:'PENDING',payload:{proposed_requirements:[]}};
 const h=harness(data);await h.start();await h.run('generateActorRequirements()');assert.equal(writes(h).length,0);assert.equal(h.nodes['#continue-event-setup'].hidden,true);assert.equal(h.timers.size,1);
});
test('confirmation covers the event, preserves tree and enables same-event setup',async()=>{
 const h=harness();await h.start();await h.run('generateActorRequirements()');await h.run('confirmActorStructure()');
 assert.ok(h.data.work_items.every(i=>i.proposal.status==='APPROVED'&&i.requirements.length===1));
 assert.equal(h.nodes['#stage-tree'].children.length,3);assert.equal(h.nodes['#actor-tree-page'].hidden,false);
 assert.equal(h.nodes['#continue-event-setup'].hidden,false);assert.equal(h.nodes['#continue-event-setup'].href,'./event-setup.html?event=event-1');
 assert.match(h.nodes['#back-inside-stage'].href,/event=event-1/);const count=writes(h).length;await h.run('confirmActorStructure()');assert.equal(writes(h).length,count);
});
test('partial generation failure reuses completed proposals on retry',async()=>{
 const h=harness();await h.start();h.fail('w1');await h.run('generateActorRequirements()');assert.equal(h.data.work_items[0].proposal.status,'PENDING');assert.match(h.nodes['#actor-message'].textContent,/interrupted/);
 h.fail(null);await h.run('generateActorRequirements()');assert.equal(writes(h).filter(r=>r.url==='/work/w0/actor-requirement-requests').length,1);assert.ok(h.data.work_items.every(i=>i.proposal?.status==='PENDING'));
 const retries=writes(h).filter(r=>r.url==='/work/w1/actor-requirement-requests');assert.equal(JSON.parse(retries[0].options.body).idempotency_key,JSON.parse(retries[1].options.body).idempotency_key);
});
test('Save & Exit writes navigation metadata only and goes to My Events',async()=>{
 const h=harness();await h.start();assert.ok(h.nodes['.actor-actions'].children.includes(h.nodes['#save-and-exit']));await h.nodes['#save-and-exit'].onclick();
 assert.equal(writes(h).length,1);assert.equal(writes(h)[0].url,'/events/event-1/resume-state');assert.equal(writes(h)[0].options.method,'PUT');assert.deepEqual(JSON.parse(writes(h)[0].options.body),{current_phase:'ACTOR_REQUIREMENTS',last_open_stage_id:null});assert.equal(h.location.assigned,'./my-events.html');
});
test('all-incomplete event has no generation and no premature Continue',async()=>{const data=fixture();data.work_items=[];const h=harness(data);await h.start();assert.equal(h.nodes['#stage-tree'].children.length,3);assert.equal(h.nodes['#generate-actors'].disabled,true);assert.equal(h.nodes['#continue-event-setup'].hidden,true);await h.run('generateActorRequirements()');assert.equal(writes(h).length,0)});
test('Event Setup returns to the same event tree without a stage parameter',async()=>{
 const source=fs.readFileSync(path.join(base,'event-setup.js'),'utf8');
 const nodes={};const ctx=vm.createContext({setupEventId:'event-1',setupStageId:null,setupRoot:{hidden:true},getToken:()=>true,loadSetup:async()=>{},location:{replace(){throw Error('unexpected redirect')}},document:{querySelector:key=>nodes[key]??={}},api:async url=>url==='/auth/me'?{display_name:'Owner',account_type:'INDIVIDUAL'}:{event:{name:'Community event'}}});
 vm.runInContext(source.slice(source.indexOf('async function initializeSetup()'),source.indexOf("document.querySelectorAll('[data-add]')")),ctx);
 await vm.runInContext('initializeSetup()',ctx);assert.equal(nodes['#setup-back'].href,'./actor-tree.html?event=event-1');
});
