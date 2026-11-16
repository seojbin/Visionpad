const {test}=require('node:test');
const assert=require('node:assert/strict');
const {GameAudio}=require('../../../engine/web/core/game-audio.js');
const state=()=>({page:'home',pets:{animals:[{id:1,species:'dog',pitch:.88},{id:2,species:'cat',pitch:1.04}],selected:1,audio:{routine_interval_seconds:[8,14],routine_gain:.35,main_gain:1.3},brush_region:{x:12,y:14,width:36,height:24}}});
test('routine scheduler rotates owned pets, isolates detail, stops on departure/mute',()=>{
 const oldSet=global.setTimeout,oldClear=global.clearTimeout;let jobs=new Map(),id=0;
 global.setTimeout=fn=>{jobs.set(++id,fn);return id};global.clearTimeout=i=>jobs.delete(i);
 const a=new GameAudio(),s=state(),calls=[];a.oneShot=(...args)=>calls.push(args);a.latestState=s;
 const tick=()=>{const [i,fn]=jobs.entries().next().value;jobs.delete(i);fn()};
 try{
  a.syncPets(s);tick();tick();assert.deepEqual(calls.map(c=>c[0]),['dog_routine','cat_routine']);assert.equal(calls[0][4].pitch,.88);
  s.page='pet_detail';s.pets.selected=2;a.syncPets(s);tick();assert.equal(calls.at(-1)[0],'cat_routine');
  s.page='farm';a.syncPets(s);assert.equal(jobs.size,0);
  s.page='home';s.pets.animals=[];a.syncPets(s);assert.equal(jobs.size,0);
  s.pets.animals=[{id:1,species:'dog',pitch:.88}];a.syncPets(s);a.stopAll();assert.equal(jobs.size,0);
 }finally{a.stopAll();global.setTimeout=oldSet;global.clearTimeout=oldClear;}
});
test('main call has stable per-pet rate and overlaps brush without restarting it',async()=>{
 const a=new GameAudio(),sources=[];const node=()=>({gain:{value:0,setTargetAtTime(){}},connect(to){this.to=to},disconnect(){}});
 a.context={currentTime:0,createGain:node,createBufferSource(){const s={playbackRate:{value:1},connect(to){this.to=to},start(){},stop(){this.stopped=true;this.onended?.()},disconnect(){}};sources.push(s);return s}};
 a.unlock=()=>{};a.load=async()=>({duration:1});a.setDucked=()=>{};a.workGain=node();a.effectsGain=node();a.latestState=state();a.motionActive=true;a.lastMotion=a.now();
 await a.startWork('brush');const brush=a.work;
 const done=a.oneShot('dog_main',null,false,0,{petId:1,pitch:.88});await new Promise(r=>setImmediate(r));
 const main=sources.at(-1);assert.equal(main.playbackRate.value,.88);assert.equal(main.petId,1);assert.equal(a.work,brush);assert.equal(brush.stopped,undefined);
 main.onended();await done;a.stopAll();
});
test('late main decode cannot play for a removed individual',async()=>{
 const a=new GameAudio();let resolve;let created=0;a.context={currentTime:0,createGain(){created++;return{gain:{},connect(){}}}};a.unlock=()=>{};a.latestState=state();a.load=()=>new Promise(r=>resolve=r);
 const promise=a.oneShot('dog_main',null,false,0,{petId:1,pitch:.88});a.latestState.pets.animals=[];resolve({duration:1});await promise;assert.equal(created,0);a.stopAll();
});
test('new uploaded sounds are routed once through the existing audio context',()=>{
 const a=new GameAudio();assert.match(a.urls.dog_main,/features\/pets\/audio/);assert.match(a.urls.cat_routine,/features\/pets\/audio/);assert.match(a.urls.roulette,/features\/roulette\/audio/);a.stopAll();
});

test('petting completion is played once per feedback ID for pets and livestock',()=>{
 const a=new GameAudio(),calls=[];
 for(const name of ['updateTaskPosition','syncWork','syncAnimals','syncPets','syncBackground','syncFishing','syncGuidance','feedback'])a[name]=()=>{};
 a.oneShot=(...args)=>calls.push(args);
 const s={page:'pet_detail',pets:{petting_feedback:{id:'pet-1',events:[{kind:'pet_sound',sound:'cat_main',pet_id:1,pitch:1.04}]}}};
 a.handle(s);a.handle(s);assert.equal(calls.length,1);assert.equal(calls[0][4].pitch,1.04);
 const t={page:'animal_detail',pasture:{petting_feedback:{id:'sheep-1',events:[{kind:'one_shot',sound:'sheep_main'}]}}};
 a.latestState=null;a.handle(t);a.handle(t);assert.equal(calls.length,2);
 t.pasture.petting_feedback.id='sheep-2';a.handle(t);assert.equal(calls.length,3);
});
