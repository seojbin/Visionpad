const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.resolve(__dirname, '../../..');
const code = fs.readFileSync(path.join(root,'engine/web/core/game.js'),'utf8');
const helper = code.slice(code.indexOf('function companionState('),code.indexOf('function inspectPointer('));
const display = fs.readFileSync(path.join(root,'engine/web/spectator/display.js'),'utf8');
const focus = display.slice(display.indexOf('function focused('),display.indexOf('function outline('));
function setup() {
 const ctx={document:{activeElement:null},canvas:{},detailMode:false,currentState:null,pointerInside:false,pointerX:1,pointerY:1,
  findInspectObject:()=>({id:'home_scene_bed'}),
  CustomEvent: class { constructor(type,options){this.type=type;this.detail=options.detail;} },
  window:{dispatchEvent(event){ctx.event=event;}}};
 vm.createContext(ctx);vm.runInContext(helper+focus,ctx);return ctx;
}
test('lower scene targets resolve to IDs used by the actual display bundle',()=>{
 const ctx=setup();
 for(const [raw,id] of Object.entries({home_scene_bed:'home_bed',home_scene_chest:'home_chest',home_scene_stove:'home_stove',home_scene_flower:'houseplant',town_scene_shop:'town_shop',town_scene_rowan:'town_rowan',shop_scene_sell:'shop_sell_choice',shop_scene_buy:'shop_buy_choice',shop_scene_calendar:'shop_calendar'})){
  const source=Object.freeze({page:'home',hover_object:raw});
  ctx.state=ctx.companionState(source);
  assert.equal(ctx.focused(id),true,raw);
  assert.equal(source.hover_object,raw);
 }
});
test('ordinary items, rocks and cleared hover retain their identity',()=>{
 const ctx=setup();for(const id of ['inventory_coin','mine_rock_1','plot_0',null])
  assert.equal(ctx.companionState({hover_object:id}).hover_object,id);
});
test('local detail mode publishes highlight without server input or mutation',()=>{
 const ctx=setup();ctx.currentState=Object.freeze({page:'home',hover_object:'home_stove'});
 ctx.detailMode=true;ctx.pointerInside=true;ctx.publishCompanionState();
 assert.equal(ctx.event.detail.hover_object,'home_bed');
 assert.equal(ctx.currentState.hover_object,'home_stove');
 ctx.findInspectObject=()=>null;ctx.publishCompanionState();
 assert.equal(ctx.event.detail.hover_object,null);
 ctx.detailMode=false;ctx.publishCompanionState();
 assert.equal(ctx.event.detail.hover_object,'home_stove');
});
test('both observer channels normalize snapshots so the second cannot undo focus',()=>{
 assert.match(code,/"dotdew-state", \{detail:currentCompanionState\(state\)\}/);
 assert.match(code,/state:currentCompanionState\(data.state\), events:/);
 assert.match(code,/function inspectPointer\([\s\S]*?publishCompanionState\(\)/);
});
test('the shipped renderer draws its orange outline for a lower scene hover',()=>{
 const ctx=setup(), strokes=[];
 ctx.ctx={strokeRect(...bounds){strokes.push({color:this.strokeStyle,bounds});}};
 vm.runInContext(display.slice(display.indexOf('function outline('),display.indexOf('function fence(')),ctx);
 ctx.state=ctx.companionState({hover_object:'home_scene_bed'});
 ctx.outline(145,115,160,230,'home_bed');
 assert.equal(strokes.length,2);
 assert.equal(strokes[1].color,'#ff9a1a');
 ctx.outline(370,105,205,205,'home_chest');
 assert.equal(strokes.length,2);
});
