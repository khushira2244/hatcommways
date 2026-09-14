// Run with Playwright available: node --test tests/web/stage-confirmation.test.cjs
const {test}=require('node:test');
const assert=require('node:assert/strict');
const {chromium}=require('playwright');
const fs=require('node:fs');
const path=require('node:path');
const web=path.resolve(__dirname,'../../apps/web');
const event={id:'test-event',name:'Test event',location_description:'Test location',version:1,starts_at:'2026-10-01T08:00:00Z',ends_at:'2026-10-01T16:00:00Z'};
const stage={temporary_stage_ref:'stage-1',canonical_name:'Preparation',purpose:'Prepare safely',proposed_order:1,proposed_start:event.starts_at,proposed_end:event.ends_at,dependencies:[]};
const proposal={id:'test-proposal',payload:{proposal_id:'test-proposal',event_id:event.id,base_event_version:1,proposed_stages:[stage],assumptions:[],concise_rationale:'Prepare',approval_required:true}};
async function scenario(t, response, {authFails=false, pending=false}={}){
 const browser=await chromium.launch({headless:true,channel:'chrome'});t.after(()=>browser.close());
 const page=await browser.newPage();let committed=false,posts=0,gets=0,bodies=[];
 await page.route('**/*',async route=>{
  const req=route.request(),url=new URL(req.url());
  if(url.hostname==='local.test'){
   const name=url.pathname.slice(1)||'planning.html';
   if(name==='runtime-config.js')return route.fulfill({contentType:'text/javascript',body:'window.HATCOMMWAYS_API_BASE="https://api.test";sessionStorage.setItem("hatcommways_access_token","fixture");'});
   return route.fulfill({contentType:name.endsWith('.js')?'text/javascript':name.endsWith('.css')?'text/css':'text/html',body:fs.readFileSync(path.join(web,name))});
  }
  if(url.pathname==='/auth/me'){if(authFails)return route.abort();return route.fulfill({json:{display_name:'Organizer',account_type:'INDIVIDUAL'}})}
  if(url.pathname.endsWith('/stage-plan-workspace')){gets++;return route.fulfill({json:{event,proposal,mode:committed?'CONFIRMED':'PROPOSAL',stages:committed?[{id:'saved-stage',canonical_name:stage.canonical_name,purpose:stage.purpose,stage_order:1,starts_at:stage.proposed_start,ends_at:stage.proposed_end,dependency_stage_ids:[]}]:[]}})}
  if(url.pathname.endsWith('/decision')){posts++;bodies.push(req.postDataJSON());if(!pending)committed=true;return response(route)}
  throw Error('Unexpected request '+req.url());
 });
 await page.goto('https://local.test/planning.html?event=test-event');
 await page.waitForFunction(()=>document.querySelector('#workspace-status').textContent==='Pending approval');
 return {page,stats:()=>({posts,gets,bodies}),confirm:()=>page.locator('#confirm-stages').click()};
}
for(const [name,respond] of [
 ['normal',r=>r.fulfill({json:{status:'APPROVED'}})],
 ['response lost after commit',r=>r.abort()],
 ['empty 200',r=>r.fulfill({status:200,body:''})],
 ['204',r=>r.fulfill({status:204})],
 ['non-JSON error page',r=>r.fulfill({status:502,contentType:'text/html',body:'<h1>Bad gateway</h1>'})]
])test(name+' hydrates saved stages without reload or generation',async t=>{
 const h=await scenario(t,respond);await h.confirm();
 await h.page.waitForFunction(()=>document.querySelector('#workspace-status').textContent==='Confirmed');
 assert.equal(h.stats().posts,1);assert.equal(h.stats().bodies[0].edited_payload,undefined);
 assert.equal(await h.page.locator('#confirm-stages').isVisible(),false);
 assert.match(await h.page.locator('#workspace-message').textContent(),/confirmed/i);
 await h.page.reload();await h.page.waitForFunction(()=>document.querySelector('#workspace-status').textContent==='Confirmed');assert.equal(h.stats().posts,1);
});
test('transient auth decoration failure does not prevent saved plan hydration',async t=>{
 const h=await scenario(t,r=>r.fulfill({json:{status:'APPROVED'}}),{authFails:true});await h.confirm();await h.page.waitForFunction(()=>document.querySelector('#workspace-status').textContent==='Confirmed');
});
test('slow response and repeated handler invocation send one confirmation',async t=>{
 let release;const gate=new Promise(r=>release=r);
 const h=await scenario(t,async r=>{await gate;await r.fulfill({json:{status:'APPROVED'}})});
 await h.confirm();await h.page.waitForFunction(()=>document.querySelector('#confirm-stages').disabled);
 await h.page.evaluate(()=>confirmStages());assert.equal(h.stats().posts,1);release();await h.page.waitForFunction(()=>document.querySelector('#workspace-status').textContent==='Confirmed');
});
test('failed uncommitted request keeps organizer edits and retries same key',async t=>{
 const h=await scenario(t,r=>r.abort(),{pending:true});await h.page.locator('[name=canonical_name]').fill('Organizer edit');await h.confirm();await h.page.waitForFunction(()=>!document.querySelector('#confirm-stages').disabled);
 assert.equal(await h.page.locator('[name=canonical_name]').inputValue(),'Organizer edit');assert.doesNotMatch(await h.page.locator('#workspace-message').textContent(),/json/i);
 await h.confirm();await h.page.waitForFunction(()=>!document.querySelector('#confirm-stages').disabled);
 assert.equal(h.stats().posts,2);assert.equal(h.stats().bodies[0].decision_idempotency_key,h.stats().bodies[1].decision_idempotency_key);
});
test('confirmation timeout checks persisted state instead of regenerating',async t=>{
 const h=await scenario(t,()=>new Promise(()=>{}));
 await h.page.clock.install();await h.confirm();
 await h.page.clock.fastForward(20001);
 await h.page.waitForFunction(()=>document.querySelector('#workspace-status').textContent==='Confirmed');
 assert.equal(h.stats().posts,1);
});
