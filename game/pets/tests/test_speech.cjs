const {test}=require('node:test');
const assert=require('node:assert/strict');
const {GameSpeech}=require('../../../engine/web/core/game-speech.js');
const tick=()=>new Promise(r=>setImmediate(r));
function setup(){
 const calls=[],sources=[],captions=[];
 const ctx={state:'running',destination:{},decodeAudioData:async()=>({duration:1}),createGain:()=>({gain:{},connect(){},disconnect(){}}),createBufferSource(){const s={connect(){},disconnect(){},start(){s.started=true;},stop(){}};sources.push(s);return s;}};
 const speech=new GameSpeech({getContext:()=>ctx,onCaption:t=>captions.push(t),fetcher:async(url,opts)=>{calls.push([url,opts]);return url==='/api/speech'?{ok:true,json:async()=>({url:'/warm.wav'})}:{ok:true,arrayBuffer:async()=>new ArrayBuffer(8)};}});
 return {speech,calls,sources,captions};
}
test('preload warms decoded speech without speaking, replay avoids network',async()=>{
 const s=setup();await s.speech.preload(['Pet house.','Pet house.']);
 assert.equal(s.sources.length,0);assert.equal(s.captions.length,0);assert.equal(s.calls.length,2);
 assert.equal(JSON.parse(s.calls[0][1].body).priority,'background');
 s.speech.unlock();await s.speech.say('Pet house.');assert.equal(s.calls.length,2);assert.equal(s.sources.length,1);
});
test('roulette narration waits for sound gate; hover does not interrupt it',async()=>{
 const s=setup();s.speech.unlock();let release;const gate=new Promise(r=>release=r);
 const job=s.speech.say('Diamond, 1.',{notBefore:gate});await tick();assert.equal(s.sources.length,0);
 await s.speech.say('Prize draw.',{priority:'hover'});assert.equal(s.speech.active.text,'Diamond, 1.');
 release();await job;assert.equal(s.sources.length,1);assert.ok(s.sources[0].started);
});
test('navigating away cancels delayed result narration',async()=>{
 const s=setup();s.speech.unlock();let release;const gate=new Promise(r=>release=r);
 const job=s.speech.say('Diamond, 1.',{notBefore:gate});await tick();
 await s.speech.say('Home.');release();await job;assert.equal(s.sources.length,1);assert.equal(s.speech.last.text,'Home.');
});
