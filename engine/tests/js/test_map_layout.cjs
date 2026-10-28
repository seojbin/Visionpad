const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.resolve(__dirname, '../..');
const folder = path.join(root, 'web/spectator');
test('detached companion renders Home at canvas centre and preserves map directions', () => {
 const source = fs.readFileSync(path.join(folder, 'viewer.js'), 'utf8');
 const fn = source.slice(source.indexOf('function map() {'), source.indexOf('function mini() {'));
 const boxes = [];
 const nodes = [['farm',16,20],['home',30,20],['town',44,20],['mine',44,6],['fishing',44,34]].map(([id,x,y])=>({id:'map_'+id,type:'node',x,y,label:id}));
 const context = {WORLD:{width:960,height:600},state:{spectator:{objects:nodes,routes:[]}},sheets:{},assetCatalog:{backgrounds:{}},focused:()=>false,text:()=>{},drawAsset:()=>{},ctx:{fillRect(){},strokeRect(...r){boxes.push(r);}}};
 vm.runInNewContext(fn+'map();',context);
 const centre = r => [r[0]+r[2]/2,r[1]+r[3]/2];
 assert.deepEqual(centre(boxes[1]),[480,300]);
 assert.ok(centre(boxes[0])[0]<480 && centre(boxes[2])[0]>480);
 assert.ok(centre(boxes[3])[1]<300 && centre(boxes[4])[1]>300);
 assert.match(fs.readFileSync(path.join(folder,'standalone.html'),'utf8'), /type="module" src="\.\/viewer.js/);
});
test('village art follows tactile left Rowan and right shop without changing sizes',()=>{
 const objects=JSON.parse(fs.readFileSync(path.join(folder,'scene-objects.json'))).scenes.town.objects;
 const shop=objects.find(o=>o.id==='general_store').bounds;
 const rowan=objects.find(o=>o.id==='rowan').bounds;
 assert.ok(rowan[0]+rowan[2]<shop[0]);
 assert.deepEqual(shop.slice(2),[250,245]);
 assert.deepEqual(rowan.slice(2),[110,205]);
});
test('every image registry texture is in the shared web assets folder',()=>{
 const textures=JSON.parse(fs.readFileSync(path.join(folder,'visual-assets.json'))).textures;
 for(const file of Object.values(textures)){
  assert.ok(file.startsWith('assets/'),file);
  assert.ok(fs.existsSync(path.join(folder,file)),file);
 }
});
