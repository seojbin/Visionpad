const {test}=require('node:test');const assert=require('node:assert/strict');
const {GameAudio}=require('./web/game-audio.js');
const flush=()=>new Promise(r=>setImmediate(r));
function fixture(decode){
 const sources=[];let now=1000;
 const context={state:'running',currentTime:0,destination:{},createGain:()=>({gain:{value:1,setTargetAtTime(value){this.value=value}},connect(){}}),decodeAudioData:decode||(()=>Promise.resolve({duration:.528})),createBufferSource:()=>{const s={started:false,stopped:false,connect(destination){this.destination=destination},disconnect(){},start(...args){this.started=true;this.startArgs=args},stop(){this.stopped=true;this.onended?.()}};sources.push(s);return s;}};
 const audio=new GameAudio({contextFactory:()=>context,fetcher:async()=>({ok:true,arrayBuffer:async()=>new ArrayBuffer(8)}),now:()=>now});audio.preload();
 return {audio,sources,advance:ms=>{now+=ms}};
}
for (const [page,name] of [['water_minigame','water'],['fertilizer_minigame','soil']]) {
 test(`${name}: cold quick click plays a bounded sound after release`,async()=>{
  let done;const {audio,sources}=fixture(()=>new Promise(r=>done=r));
  audio.inputDown({page},12,10);audio.inputUp();await flush();
  done({duration:6});await flush();
  assert.equal(sources.length,1);assert.equal(sources[0].started,true);
  assert.equal(sources[0].loop,undefined);assert.deepEqual(sources[0].startArgs,[0,0,.65]);assert.equal(audio.work,null);
  audio.stopAll();assert.equal(sources[0].stopped,true);
 });
 test(`${name}: holding loops and release stops the loop`,async()=>{
  const {audio,sources}=fixture();audio.inputDown({page},12,10);await flush();await flush();
  assert.equal(audio.workName,name);const loop=sources.find(s=>s.loop);assert(loop.started);
  audio.inputUp();assert(loop.stopped);audio.stopAll();
 });
}
test('pause cancels a pending click decode',async()=>{
 let done;const {audio,sources}=fixture(()=>new Promise(r=>done=r));
 audio.inputDown({page:'water_minigame'},12,10);await flush();audio.stopAll();
 done({duration:6});await flush();assert.equal(sources.length,0);
});
test('cooking follows authoritative cut and stir stages',async()=>{const {audio}=fixture();audio.inputDown({page:'cooking'},10,10);audio.handle({page:'cooking',cooking:{dragging:true}},[{kind:'work_start',sound:'cut'}]);await flush();assert.equal(audio.workName,'cut');audio.handle({page:'cooking',cooking:{dragging:false}},[]);assert.equal(audio.workName,null);audio.inputDown({page:'cooking'},30,9);audio.handle({page:'cooking',cooking:{dragging:true,gesture_kind:'stir'}},[{kind:'work_start',sound:'cook'}]);await flush();assert.equal(audio.workName,'cook');audio.stopAll();});
test('correct rewards use a bounded channel and never restart work',async()=>{const {audio,sources,advance}=fixture();await audio.correct(1);await audio.correct(1);assert.equal(sources.length,1);advance(100);await audio.correct(2);advance(100);await audio.correct(1);assert.equal(audio.rewardSources.size,2);assert.equal(sources[0].stopped,true);assert.equal(audio.workName,null);audio.stopAll();});
test('mute and reset invalidate pending feedback',async()=>{let done;const {audio,sources}=fixture(()=>new Promise(r=>done=r));const pending=audio.correct(1);await flush();audio.stopAll();done({duration:.5});await pending;assert.equal(sources.length,0);audio.setEnabled(false);await audio.correct(1);assert.equal(sources.length,0);});
test('speech ducks work without changing the volume preference',()=>{const {audio}=fixture();audio.unlock();audio.setVolume(.8);audio.setDucked(true);assert.equal(audio.volume,.8);assert.equal(audio.workGain.gain.value,.30);audio.setDucked(false);assert.equal(audio.workGain.gain.value,.75);audio.stopAll();});

test('a queued hover response cannot permanently cancel a newly pressed task',async()=>{const {audio}=fixture();audio.inputDown({page:'water_minigame'},12,10);audio.handle({page:'water_minigame',care:{dragging:false}},[]);audio.handle({page:'water_minigame',care:{dragging:true}},[]);await flush();assert.equal(audio.workName,'water');assert(audio.work);audio.stopAll();});

for (const [page,name,kind] of [['water_minigame','water'],['fertilizer_minigame','soil'],['cooking','cut','cut'],['cooking','cook','stir']]) {
 test(`${name}: repeated correct overlays preserve the same work source and gain`,async()=>{
  const {audio,advance}=fixture();const state={page,care:{dragging:true},cooking:{dragging:true,gesture_kind:kind}};
  audio.inputDown(state,10,10);audio.handle(state);await flush();await flush();
  const work=audio.work,token=audio.workToken,gain=audio.workGain.gain.value;
  assert(work);assert.equal(work.destination,audio.workGain);
  for(let i=0;i<6;i++) {
   advance(page==='cooking'?700:100);audio.handle(i%2 ? undefined : state,[{kind:'correct',count:1}]);await flush();
   assert.equal(audio.work,work);assert.equal(work.stopped,false);assert.equal(audio.workToken,token);
   assert.equal(audio.workGain.gain.value,gain);
   for(const reward of audio.rewardSources)assert.equal(reward.destination,audio.rewardGain);
  }
  assert.equal(audio.rewardSources.size,2);audio.stopAll();assert(work.stopped);
 });
}
test('care click and correct route to distinct layers',async()=>{
 const {audio}=fixture();audio.inputDown({page:'water_minigame'},10,10);audio.inputUp();await flush();
 const click=[...audio.clickSources][0];assert.equal(click.destination,audio.workGain);
 await audio.correct();assert.equal([...audio.rewardSources][0].destination,audio.rewardGain);
 assert.equal(click.stopped,false);audio.stopAll();
});
test('stale hover cannot interrupt a running sprinkling source',async()=>{
 const {audio}=fixture();audio.inputDown({page:'water_minigame'},10,10);await flush();
 const work=audio.work;audio.handle({page:'water_minigame',care:{dragging:false}},[{kind:'correct',count:1}]);await flush();
 assert.equal(audio.work,work);assert.equal(work.stopped,false);audio.stopAll();
});

test('all background page groups and same-group continuity',async()=>{
 const {audio}=fixture();audio.unlock();
 for(const page of ['home','farm','town','inventory','research','plot_detail'])assert.equal(audio.backgroundFor({page}),'basic');
 for(const page of ['seed_select','water_minigame','fertilizer_minigame','harvest','recipe_select','ingredient_select','cooking'])assert.equal(audio.backgroundFor({page}),'minigame');
 for(const page of ['shop_choice','shop_buy','shop_sell'])assert.equal(audio.backgroundFor({page}),'shop');
 audio.handle({page:'shop_choice'});await flush();const shop=audio.bgm;assert(shop?.loop);assert.equal(audio.bgmGain.gain.value,.4);
 audio.handle({page:'shop_buy'});await flush();assert.equal(audio.bgm,shop);assert.equal(shop.stopped,false);
 audio.handle({page:'cooking',cooking:{dragging:false}});await flush();assert(shop.stopped);assert.equal(audio.bgmGain.gain.value,.1);audio.stopAll();
});
test('crop press loops; correct overlays; release stops work only',async()=>{
 const {audio}=fixture();const state={page:'harvest'};audio.inputDown(state,10,10);audio.handle(state);await flush();const work=audio.work;assert.equal(audio.workName,'crop');assert(work.loop);
 await audio.correct();assert.equal(audio.work,work);assert.equal(work.stopped,false);const bgm=audio.bgm;audio.inputUp();assert(work.stopped);assert.equal(bgm.stopped,false);audio.stopAll();
});
test('sleep pauses BGM; bell survives morning and navigation',async()=>{
 const {audio}=fixture();audio.unlock();audio.handle({page:'home'});await flush();const bgm=audio.bgm;
 audio.handle({page:'home',sleeping:true,day_ended:true},[{kind:'one_shot',sound:'sleep'}]);await flush();assert(bgm.stopped);assert.equal(audio.bgm,null);
 const bell=[...audio.oneShotSources][0];assert(bell?.started);assert.equal(bell.loop,undefined);
 audio.handle({page:'home',sleeping:false,day_ended:false});await flush();assert(audio.bgm);assert.equal(bell.stopped,false);
 audio.stopTasks();audio.handle({page:'farm'});assert.equal(bell.stopped,false);assert.equal(audio.oneShotSources.size,1);audio.stopAll();assert(bell.stopped);
});
test('coin still plays on action that ends the day',async()=>{
 const {audio}=fixture();audio.handle({page:'home',day_ended:true},[{kind:'one_shot',sound:'coin'}]);await flush();assert.equal(audio.oneShotSources.size,1);audio.stopAll();
});
test('cold stale BGM load cannot replace newer background',async()=>{
 const {audio}=fixture();audio.unlock();audio.handle({page:'home'});audio.handle({page:'shop_buy'});await flush();assert.equal(audio.bgmName,'shop');assert(audio.bgm);audio.stopAll();
});
test('config sets independent background and one-shot gains',async()=>{
 const {audio}=fixture();audio.configure({bgm_gain:{shop:.55},one_shot_gain:{door:.44}});audio.unlock();audio.handle({page:'shop_buy'},[{kind:'one_shot',sound:'door'}]);await flush();assert.equal(audio.bgmGain.gain.value,.55);assert.equal([...audio.oneShotSources][0].destination.gain.value,.44);audio.stopAll();
});

test('step follows door gain even after config changes',async()=>{
 const {audio}=fixture();audio.configure({one_shot_gain:{door:.83}});audio.handle({page:'town'},[{kind:'one_shot',sound:'step'}]);await flush();assert.equal([...audio.oneShotSources][0].destination.gain.value,.83);audio.stopAll();
});
test('mining break completes before loot narration and reward',async()=>{
 const {audio}=fixture();const said=[];audio.onNarration=t=>said.push(t);
 audio.handle({page:'mine'},[{kind:'mining_loot',sound:'correct',tts:'구리 1개 획득'}]);await flush();assert.deepEqual(said,[]);const breaking=[...audio.oneShotSources][0];assert(breaking?.started);
 breaking.onended();await flush();assert.deepEqual(said,['구리 1개 획득']);assert.equal(audio.rewardSources.size,1);audio.stopAll();
});
test('diamond reward uses shine after break',async()=>{
 const {audio}=fixture();const said=[];audio.onNarration=t=>said.push(t);
 audio.handle({page:'mine'},[{kind:'mining_loot',sound:'shine',tts:'다이아몬드 2개 획득. 보너스'}]);await flush();[...audio.oneShotSources][0].onended();await flush();assert.equal(said.length,1);assert.equal(audio.rewardSources.size,0);assert.equal(audio.oneShotSources.size,1);audio.stopAll();
});
test('muted effects still narrate mining loot',()=>{
 const {audio}=fixture();const said=[];audio.onNarration=t=>said.push(t);audio.setEnabled(false);audio.handle({page:'mine'},[{kind:'mining_loot',sound:'shine',tts:'다이아몬드 1개 획득'}]);assert.deepEqual(said,['다이아몬드 1개 획득']);audio.stopAll();
});
test('navigation cancels stale delayed mining narration',async()=>{
 const {audio}=fixture();const said=[];audio.onNarration=t=>said.push(t);audio.handle({page:'mine'},[{kind:'mining_loot',sound:'correct',tts:'돌 1개 획득'}]);await flush();const breaking=[...audio.oneShotSources][0];audio.stopTasks();audio.handle({page:'town'});breaking.onended();await flush();assert.deepEqual(said,[]);audio.stopAll();
});

test('night snapshots preserve final mining loot narration',async()=>{const {audio}=fixture();const said=[];audio.onNarration=t=>said.push(t);audio.held=true;audio.handle({page:'home',day_ended:true},[{kind:'mining_loot',sound:'correct',tts:'돌 1개 획득. 집에 도착'}]);await flush();const breaking=[...audio.oneShotSources][0];audio.handle({page:'home',day_ended:true});breaking.onended();await flush();assert.equal(said.length,1);audio.stopAll();});
