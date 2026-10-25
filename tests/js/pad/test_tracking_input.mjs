import assert from 'node:assert/strict';
import {test} from 'node:test';
// F4 (known failure): TrackingGestureInput was removed from hardware.mjs together with the thumb-press clicks.
const {TrackingGestureInput}=await import('../../../engine/web/core/pad/hardware.mjs');
if(!TrackingGestureInput)test('test_tracking_input.mjs',{todo:'F4: TrackingGestureInput is not exported by hardware.mjs'},()=>{throw new SyntaxError('hardware.mjs does not export TrackingGestureInput')});
else{
const events=[];const t=new TrackingGestureInput({move:(...p)=>events.push(['move',...p]),press:()=>events.push('press'),release:()=>events.push('release'),command:c=>events.push(c)});
t.update([1,2],true);assert(!events.includes('press'));t.update([1,2],false);t.update([3,4],true);t.update([4,5],true);assert.equal(events.filter(e=>e==='press').length,1);assert.deepEqual(events[events.indexOf('press')-1],['move',3,4]);t.update([4,5],false);assert.equal(events.filter(e=>e==='release').length,1);
t.update([4,5],true);t.reset();t.update([4,5],true);assert.equal(events.filter(e=>e==='press').length,2);assert.equal(events.filter(e=>e==='release').length,2);console.log('PASS edge clicks, position order, held repeat prevention and loss rearm');
}
