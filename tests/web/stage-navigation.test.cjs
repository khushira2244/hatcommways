// Run: node --test tests/web/stage-navigation.test.cjs
// Executes the production controllers with a minimal DOM and controlled API promises.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');
const base=path.resolve(__dirname,'../../apps/web');
class Element {
 constructor(){this.hidden=false;this.disabled=false;this.dataset={};this.style={setProperty(){}};this.children=[];this.attrs={};this.nodes={};this.classList={toggle(){},add(){},remove(){}};this.textContent='';}
 set innerHTML(value){this.html=value;this.children=[];this.nodes={};}
 get innerHTML(){return this.html||'';}
 querySelector(key){return this.nodes[key]??=new Element();}
 querySelectorAll(key){if(key==='button')return [this.querySelector('.stage-label'),this.querySelector('.stage-block')];return [];}
 append(node){this.children.push(node)}
 setAttribute(k,v){this.attrs[k]=v}
 remove(){this.removed=true}
 closest(){return new Element()}
}
function harness(file){
 const nodes={};const document={querySelector:k=>{if(k==='#save-and-exit'&&(!nodes[k]||nodes[k].removed))return null;return nodes[k]??=new Element()},querySelectorAll:k=>k==='.stage-timeline-row'?(nodes['#stage-rows']?.children||[]):[],createElement:()=>new Element(),body:new Element()};
 document.body.append=e=>{nodes['#'+e.id]=e};
 const requests=[],pending=[],timers=[],listeners={};let automatic=true;
 const location={search:'?event=event-fixture&id=a',assign:url=>{location.assigned=url},replace:url=>{location.replaced=url}};
 const stages=['a','b','c'].map((id,i)=>({id,stage_order:i+1,canonical_name:`Stage ${id}`,purpose:'Purpose',starts_at:'2026-09-01T08:00:00Z',ends_at:'2026-09-01T10:00:00Z',version:1,dependency_stage_ids:[]}));
 const snapshot=(id,mode='EMPTY')=>({event:{id:'event-fixture',version:3,starts_at:stages[0].starts_at,ends_at:stages[0].ends_at},stages,selected_stage:stages.find(s=>s.id===id),mode,work:[],proposal:{id:'proposal-'+id,payload:{proposed_work:[]}}});
 const ctx=vm.createContext({document,location,URLSearchParams,Intl,Date,console,crypto:require('node:crypto').webcrypto,setTimeout:fn=>timers.push(fn),getToken:()=>true,history:{pushState(_,__,url){location.search=url.slice(url.indexOf('?'))},replaceState(_,__,url){location.search=url.slice(url.indexOf('?'))}},window:{addEventListener:(key,fn)=>listeners[key]=fn},api:(url,options={})=>{requests.push({url,options});if(url==='/auth/me')return Promise.resolve({display_name:'Owner',account_type:'INDIVIDUAL'});if(automatic)return Promise.resolve(snapshot('a'));return new Promise((resolve,reject)=>pending.push({url,resolve,reject}))}});
 const auth=fs.readFileSync(path.join(base,'auth.js'),'utf8');vm.runInContext(auth.slice(auth.indexOf('function installSaveExit('),auth.indexOf('const signupForm')),ctx);
 let source=fs.readFileSync(path.join(base,file),'utf8').replace(/^initialize\(\);$/m,'');
 vm.runInContext(source,ctx);
 const run=code=>vm.runInContext(code,ctx);
 const settle=async()=>{for(let i=0;i<8;i++)await Promise.resolve()};
 return {ctx,nodes,document,requests,pending,timers,listeners,location,snapshot,run,settle,manual(){automatic=false},async start(){run('initialize()');await settle();this.manual()}};
}
test('stage switches retain workspace, use GET only, keep event and save current stage',async()=>{
 const h=harness('inside-stage.js');await h.start();const root=h.nodes['#inside-stage'];const old=h.nodes['#inside-title'].textContent;
 const done=h.run("switchStage('b')");assert.equal(root.hidden,false);assert.equal(h.nodes['#inside-title'].textContent,old);assert.equal(h.nodes['#save-and-exit'].disabled,true);
 h.pending.shift().resolve(h.snapshot('b','PROPOSAL'));await done;
 assert.equal(h.run('stageId'),'b');assert.equal(h.run('data.mode'),'PROPOSAL');assert.equal(h.nodes['#compact-stage-list'].children.length,3);assert.match(h.location.search,/event=event-fixture/);assert.equal(h.nodes['#back-stage-plan'].href,'./planning.html?event=event-fixture');assert.ok(h.requests.every(r=>!r.options.method));
 const save=h.nodes['#save-and-exit'].onclick();const request=h.requests.at(-1);assert.equal(request.options.method,'PUT');assert.equal(request.url,'/events/event-fixture/resume-state');assert.deepEqual(JSON.parse(request.options.body),{current_phase:'WORK_DESIGN',last_open_stage_id:'b'});h.pending.shift().resolve({});await save;assert.equal(h.location.assigned,'./my-events.html');
});
test('rapid switching ignores stale success and stale failure',async()=>{
 for(const fail of [false,true]){const h=harness('inside-stage.js');await h.start();const b=h.run("switchStage('b')"),c=h.run("switchStage('c')");const rb=h.pending.shift(),rc=h.pending.shift();rc.resolve(h.snapshot('c'));await c;fail?rb.reject(new Error('stale')):rb.resolve(h.snapshot('b'));await b;assert.equal(h.run('stageId'),'c');assert.equal(h.nodes['#inside-message'].textContent,'');}
});
test('failed switch keeps prior data, URL and usable controls',async()=>{const h=harness('inside-stage.js');await h.start();const p=h.run("switchStage('b')");h.pending.shift().reject(new Error('offline'));await p;assert.equal(h.run('stageId'),'a');assert.match(h.location.search,/id=a/);assert.equal(h.nodes['#inside-stage'].hidden,false);assert.equal(h.nodes['#generate-work'].disabled,false);});
test('browser history changes selected workspace without writes',async()=>{const h=harness('inside-stage.js');await h.start();h.location.search='?event=event-fixture&id=c';const p=h.listeners.popstate();h.pending.shift().resolve(h.snapshot('c'));await p;assert.equal(h.run('stageId'),'c');assert.ok(h.requests.every(r=>!r.options.method));});
test('all existing modes remain read-only on selection',async()=>{
 for(const mode of ['EMPTY','REQUESTED','RUNNING','PROPOSAL','CONFIRMED','FAILED']){const h=harness('inside-stage.js');await h.start();const p=h.run("switchStage('b')");h.pending.shift().resolve(h.snapshot('b',mode));await p;assert.equal(h.nodes['#inside-stage'].dataset.mode,mode);assert.equal(h.nodes['#generate-work'].hidden,mode!=='EMPTY'&&mode!=='PROPOSAL'&&mode!=='CONFIRMED');assert.ok(h.requests.every(r=>!r.options.method));if(['PROPOSAL','CONFIRMED'].includes(mode))assert.equal(h.nodes['#empty-work'].hidden,true);}
});
test('poll from an old stage cannot overwrite the selected stage',async()=>{const h=harness('inside-stage.js');await h.start();h.run("data.mode='RUNNING';pollExistingRequest()");const p=h.run("switchStage('b')");h.pending.shift().resolve(h.snapshot('b'));await p;h.timers.shift()();await h.settle();assert.equal(h.run('stageId'),'b');assert.equal(h.pending.length,0);});
test('generation remains explicit and includes the same event',async()=>{const h=harness('inside-stage.js');await h.start();const p=h.run('requestWork()');const r=h.requests.at(-1);assert.equal(r.options.method,'POST');assert.equal(r.url,'/stages/a/work-design-requests');assert.equal(JSON.parse(r.options.body).event_id,'event-fixture');h.pending.shift().resolve({});await h.settle();h.pending.shift().resolve(h.snapshot('a','PROPOSAL'));await p;assert.equal(h.run('data.mode'),'PROPOSAL');});
test('confirmation response cannot replace another stage',async()=>{const h=harness('inside-stage.js');await h.start();h.run("data.mode='PROPOSAL'");const confirm=h.run('confirmWork()'),mutation=h.pending.shift();const select=h.run("switchStage('b')");h.pending.shift().resolve(h.snapshot('b'));await select;mutation.resolve({});await confirm;assert.equal(h.run('stageId'),'b');assert.equal(h.pending.length,0);});
test('Stage Plan selection retains rows, updates details and Open Stage only',async()=>{
 const h=harness('stage-plan.js');const form=h.document.querySelector('#stage-editor');for(const k of ['canonical_name','purpose','proposed_start','proposed_end'])form[k]=new Element();
 h.run(`workspace=${JSON.stringify({...h.snapshot('a'),mode:'CONFIRMED'})};loadConfirmed()`);const rows=h.nodes['#stage-rows'].children;h.run("selectStage('b')");assert.equal(h.nodes['#stage-rows'].children,rows);assert.equal(form.canonical_name.value,'Stage b');assert.equal(h.nodes['#open-stage'].href,'./stage.html?id=b&event=event-fixture');assert.ok(rows.every(row=>!row.innerHTML.includes('<span>Stage')));assert.equal(h.requests.length,0);
 h.manual();const save=h.nodes['#save-and-exit'].onclick();assert.deepEqual(JSON.parse(h.requests.at(-1).options.body),{current_phase:'STAGE_PLANNING',last_open_stage_id:null});h.pending.shift().resolve({});await save;assert.equal(h.location.assigned,'./my-events.html');
});
