const {test}=require('node:test');
const assert=require('node:assert/strict');
const {GameAudio}=require('../../../engine/web/core/game-audio.js');
const wait=ms=>new Promise(r=>setTimeout(r,ms));
function setup(){
 const a=new GameAudio();const played=[];a.oneShot=n=>played.push(n);
 const s={page:'home',pasture:{morning_id:0,selected:'chicken',animals:{chicken:{owned:true},sheep:{owned:true}},audio:{routine_interval_ms:15,morning_delay_ms:15}}};
 a.latestState=s;a.syncAnimals(s);return {a,s,played};
}
test('morning plays without another input; initial state does not crow',async()=>{
 const {a,s,played}=setup();await wait(20);assert.deepEqual(played,[]);
 s.pasture.morning_id++;a.syncAnimals(s,'morning');await wait(25);assert.deepEqual(played,['chicken_morning']);a.stopAll();
});
test('pasture routines include both; detail only selected animal; leaving stops routines',async()=>{
 const {a,s,played}=setup();s.page='pasture';a.syncAnimals(s);await wait(20);
 assert.deepEqual(played,['chicken_routine','sheep_routine']);played.length=0;
 s.page='animal_detail';a.syncAnimals(s);await wait(20);assert.deepEqual(played,['chicken_routine']);
 s.page='home';a.syncAnimals(s);played.length=0;await wait(25);assert.deepEqual(played,[]);a.stopAll();
});
test('stop all cancels pending morning and routine; crack gains are finite',async()=>{
 const {a,s,played}=setup();s.pasture.morning_id++;s.page='pasture';a.syncAnimals(s,'morning');a.stopAll();await wait(25);
 assert.deepEqual(played,[]);assert.ok(Number.isFinite(a.settings.work_gain.crack));assert.ok(Number.isFinite(a.settings.work_gain_during_tts.crack));
});

test('loading a different day does not replay a wake-up call',async()=>{
 const {a,s,played}=setup();s.pasture.morning_id++;a.syncAnimals(s,'loaded');await wait(25);assert.deepEqual(played,[]);a.stopAll();
});

test('unowned animals never produce routine or morning calls',async()=>{
 const {a,s,played}=setup();s.pasture.animals.chicken.owned=false;s.pasture.animals.sheep.owned=false;
 s.page='pasture';s.pasture.morning_id++;a.syncAnimals(s,'morning');await wait(35);
 assert.deepEqual(played,[]);a.stopAll();
});
test('only owned sheep calls; chicken morning is cancelled after ownership loss',async()=>{
 const {a,s,played}=setup();s.pasture.animals.chicken.owned=false;s.page='pasture';a.syncAnimals(s);await wait(20);
 assert.deepEqual(played,['sheep_routine']);a.stopAll();played.length=0;
 s.page='home';s.pasture.animals.chicken.owned=true;s.pasture.morning_id++;a.syncAnimals(s,'morning');
 s.pasture.animals.chicken.owned=false;await wait(25);assert.deepEqual(played,[]);a.stopAll();
});
test('shearing motion starts its own cut file and releases after idle',()=>{
 const {a,s}=setup(),work=[];a.startWork=name=>work.push(name);a.stopWork=()=>work.push('stop');
 a.motionActive=true;a.lastMotion=a.now();a.syncWork({...s,page:'shearing'});assert.deepEqual(work,['shear']);
 assert.equal(a.urls.shear,'/static/features/pasture/audio/cut.mp3');
 a.lastMotion=-Infinity;a.syncWork({...s,page:'shearing'});assert.equal(work.at(-1),'stop');a.stopAll();
});

test('brushing uses local animal bounds, 2.5 gain, and stops outside or paused',()=>{
 const {a,s}=setup(),work=[];s.page='animal_detail';s.pasture.brush_region={x:22,y:15,width:18,height:17};a.latestState=s;
 a.startWork=n=>work.push(n);a.stopWork=()=>work.push('stop');
 a.move(28,22);assert.equal(work.at(-1),'brush');
 assert.equal(a.settings.work_gain.brush,2.5);assert.equal(a.settings.work_gain_during_tts.brush,2.5);
 assert.equal(a.urls.brush,'/static/features/pasture/audio/brush.mp3?v=2');
 a.move(8,6);assert.equal(work.at(-1),'stop');
 a.lastPosition=[28,22];a.lastMotion=-Infinity;a.syncWork(s);assert.equal(work.at(-1),'stop');
 a.stopAll();
});

test('brush and animal main/routine sounds use concurrent independent sources',async()=>{
 const a=new GameAudio(),sources=[];
 const node=()=>({connect(to){this.to=to;},disconnect(){},gain:{value:0,setTargetAtTime(){}}});
 a.context={currentTime:0,createGain:node,createBufferSource(){const s={connect(to){this.to=to;},disconnect(){},start(){this.started=true;},stop(){this.stopped=true;this.onended?.();}};sources.push(s);return s;}};
 a.unlock=()=>{};a.load=async name=>({name,duration:1});a.setDucked=()=>{};
 a.workGain=node();a.effectsGain=node();a.motionActive=true;a.lastMotion=a.now();
 await a.startWork('brush');const brush=a.work;
 const main=a.oneShot('chicken_main',null,false),routine=a.oneShot('chicken_routine',null,false);
 await new Promise(resolve=>setImmediate(resolve));
 assert.equal(a.work,brush);assert.equal(brush.stopped,undefined);assert.equal(brush.to,a.workGain);
 assert.equal(a.oneShotSources.size,2);
 for(const source of [...a.oneShotSources]){assert.equal(source.to.to,a.effectsGain);assert.equal(source.started,true);source.onended();}
 await Promise.all([main,routine]);assert.equal(a.work,brush);assert.equal(brush.stopped,undefined);
 a.stopAll();
});

test('feed is a registered non-spatial one-shot with 1.8 gain',async()=>{
 const a=new GameAudio(),nodes=[],sources=[];
 a.context={currentTime:0,createGain(){const g={gain:{value:0},connect(to){this.to=to;},disconnect(){}};nodes.push(g);return g;},createBufferSource(){const s={connect(to){this.to=to;},start(){},disconnect(){}};sources.push(s);return s;}};
 a.unlock=()=>{};a.load=async()=>({duration:1});a.effectsGain={};
 a.createSpatialBus=()=>{throw Error('Feed must not use spatial audio');};
 assert.equal(a.urls.feed,'/static/features/pasture/audio/feed.mp3');
 const done=a.oneShot('feed',[10,20]);await new Promise(r=>setImmediate(r));
 assert.equal(sources.length,1);assert.equal(nodes[0].gain.value,1.8);assert.equal(nodes[0].to,a.effectsGain);
 sources[0].onended();await done;
});
