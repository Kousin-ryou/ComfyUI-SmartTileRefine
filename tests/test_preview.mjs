import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import vm from "node:vm";

const calls=[];
const ctx=new Proxy({}, {get:(_,name)=>(...args)=>calls.push([name,...args]),set:()=>true});
let locale="zh", request, imageLoads=0;
const upstream={id:1,type:"LoadImage",widgets:[{name:"image",value:"example.png"}]};
const app={ui:{settings:{getSettingValue:()=>locale}},graph:{links:{1:{origin_id:1}},getNodeById:()=>upstream,setDirtyCanvas(){}},canvas:{ds:{scale:1}},registerExtension(){}};
const api={apiURL:path=>path,addEventListener(){},fetchApi:(...args)=>request(...args)};
const context=vm.createContext({app,api,URLSearchParams,Map,Set,Math,JSON,Number,String,Object,Promise,
    document:{documentElement:{lang:"en"},addEventListener(){}},window:{devicePixelRatio:1,addEventListener(){}},setTimeout,clearTimeout,
    Image:class {naturalWidth=2688; naturalHeight=1512; set src(value) {imageLoads++; queueMicrotask(()=>this.onload());}}});
const script=(await readFile(new URL("../web/smart_tile_final.js",import.meta.url),"utf8")).replace(/^import .*;\r?\n/gm,"");
vm.runInContext(`${script}\nthis.test={draw,layout,updatePlan,localize};`,context);
const {draw,layout,updatePlan,localize}=context.test;
function node() {
    const n={title:"分块高清重绘",size:[280,1400],inputs:[{name:"image",link:1}],outputs:[{name:"image"}],
        widgets:[{name:"columns",value:2},{name:"rows",value:2},{name:"expand_percent",value:15},{name:"redraw_mode",value:"Independent tiles",options:{}},{name:"batch_size",value:1}],
        setSize(){throw Error("Preview must not resize the node");}};
    n._smartTile={node:n,wrapper:{style:{},closest:()=>({style:{}})},canvas:{clientWidth:300,clientHeight:200,getContext:()=>ctx,setAttribute(){}},
        height:0,imageVersion:0,planVersion:0,tileProgress:{},hovered:null};
    return n;
}
const plan={width:2688,height:1512,columns:2,rows:2,count:4,tiles:[
    {id:0,core:[0,0,1344,756],crop:[0,0,1546,869]},
    {id:1,core:[1344,0,2688,756],crop:[1142,0,2688,869]},
    {id:2,core:[0,756,1344,1512],crop:[0,643,1546,1512]},
    {id:3,core:[1344,756,2688,1512],crop:[1142,643,2688,1512]}]};

// A failed first plan request used to become permanently cached.
const n=node(); let attempts=0;
request=async()=>{attempts++; if(attempts===1) throw Error("temporary"); return {ok:true,json:async()=>plan};};
await updatePlan(n);
assert(n._smartTile.image);
assert(calls.some(c=>c[0]==="drawImage"));
assert(!calls.some(c=>c[0]==="fillText"));
assert.equal(n._smartTile.requestKey,null);
await updatePlan(n);
assert.equal(attempts,2); assert.equal(n._smartTile.plan.count,4);
assert.equal(imageLoads,1);

// Paint the image even while planning fails; no error/placeholder text.
calls.length=0; n._smartTile.plan=null; draw(n._smartTile);
assert(calls.some(c=>c[0]==="drawImage"));
assert(!calls.some(c=>c[0]==="fillText"));
n._smartTile.plan=plan;
calls.length=0; draw(n._smartTile);
assert(!calls.some(c=>c[0]==="strokeRect"));
assert.equal(calls.filter(c=>c[0]==="moveTo").length,2);
n._smartTile.hovered=1; calls.length=0; draw(n._smartTile);
assert.equal(calls.filter(c=>c[0]==="strokeRect").length,1);
n._smartTile.hovered=null; calls.length=0; draw(n._smartTile);
assert(!calls.some(c=>c[0]==="strokeRect"));
n._smartTile.adjusting=true; calls.length=0; draw(n._smartTile);
assert.equal(calls.filter(c=>c[0]==="strokeRect").length,1);

// Language changes preserve stored combo values and use English fallback.
localize(n); assert.equal(n.widgets.at(-1).label,"单次数量");
assert.equal(n.widgets[3].options.getOptionLabel("S-shaped sequence"),"S形依次重绘");
locale="fr"; localize(n); assert.equal(n.title,"Tile Refine");
assert.equal(n.widgets[3].options.getOptionLabel("S-shaped sequence"),"S-shaped sequence");
assert.equal(n.widgets[3].value,"Independent tiles");
layout(n); assert.deepEqual(n.size,[280,1400]);

// Disconnect hides the preview and invalidates in-flight image loading.
n.inputs[0].link=null; await updatePlan(n);
assert.equal(n._smartTile.image,null); assert.equal(n._smartTile.height,0);
assert.equal(n._smartTile.wrapper.style.display,"none");
n.inputs[0].link=1; await updatePlan(n);
assert(n._smartTile.image); assert.equal(n._smartTile.plan.count,4);
assert.equal(imageLoads,2);
console.log("Preview regressions passed: async retry, image-only fallback, hover, extension, continuous grid, locale fallback, free sizing, reconnect.");
