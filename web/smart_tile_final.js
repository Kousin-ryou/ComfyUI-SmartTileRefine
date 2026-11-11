import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const chinese = {
    image: "图像", model: "模型", positive: "正面条件", negative: "负面条件", vae: "VAE",
    upscale_model: "放大模型", upscale_by: "放大倍率", columns: "横向块数", rows: "纵向块数",
    expand_percent: "分块延展", redraw_mode: "重绘方式", seed: "种子", steps: "步数",
    cfg: "CFG", sampler_name: "采样器", scheduler: "调度器", denoise: "重绘强度",
    color_correction: "颜色校正", color_strength: "校正强度", batch_size: "单次数量",
};
const english = {
    image: "Image", model: "Model", positive: "Positive", negative: "Negative", vae: "VAE",
    upscale_model: "Upscale model", upscale_by: "Upscale factor", columns: "Columns", rows: "Rows",
    expand_percent: "Tile extension", redraw_mode: "Redraw method", seed: "Seed", steps: "Steps",
    cfg: "CFG", sampler_name: "Sampler", scheduler: "Scheduler", denoise: "Denoise",
    color_correction: "Color correction", color_strength: "Correction strength", batch_size: "Tiles per pass",
};
function language() {
    return String(app.ui.settings.getSettingValue("Comfy.Locale") || document.documentElement.lang).toLowerCase().startsWith("zh") ? "zh" : "en";
}
function localize(node) {
    const zh = language() === "zh", labels = zh ? chinese : english;
    for (const item of [...(node.inputs || []), ...(node.outputs || []), ...(node.widgets || [])]) {
        if (labels[item.name]) { item.label=labels[item.name]; item.localized_name=labels[item.name]; }
    }
    if (["SmartTileRefine", "分块高清重绘", "Tile Refine"].includes(node.title)) node.title=zh ? "分块高清重绘" : "Tile Refine";
    const mode=node.widgets?.find(w=>w.name==="redraw_mode");
    if (mode) mode.options.getOptionLabel=value=>zh ? ({"Independent tiles":"分块独立重绘", "S-shaped sequence":"S形依次重绘"}[value] || value) : value;
    node._smartTile.locale=language();
    node._smartTile.canvas.setAttribute("aria-label", zh ? "分块预览" : "Tile preview");
}
const planKeys = ["upscale_by", "columns", "rows", "expand_percent", "upscale_connected"];
const nodes = new Map();
document.addEventListener("pointermove", event=>{
    for (const node of nodes.values()) {
        const s=node._smartTile;
        if (s.hovered!=null && event.target!==s.canvas) { s.hovered=null; draw(s); }
    }
}, true);
window.addEventListener("blur",()=>{
    for (const node of nodes.values()) { node._smartTile.hovered=null; draw(node._smartTile); }
});

function values(node) {
    const v = Object.fromEntries((node.widgets || []).map(w => [w.name, w.value]));
    v.upscale_connected = node.inputs?.some(i => i.name === "upscale_model" && i.link != null) || false;
    return v;
}

function viewURL(file) {
    return api.apiURL(`/view?${new URLSearchParams({ filename: file.filename, subfolder: file.subfolder || "", type: file.type || "input" })}`);
}

function loadImage(url) {
    return new Promise((resolve, reject) => {
        const image = new Image();
        image.onload = () => resolve(image);
        image.onerror = () => reject(new Error("图片读取失败"));
        image.src = url;
    });
}

function inputNode(node, name) {
    const input = node.inputs?.find(i => i.name === name);
    const link = app.graph?.links?.[input?.link];
    return link ? app.graph.getNodeById(link.origin_id) : null;
}

function sourceDescriptor(node, seen = new Set()) {
    if (!node || seen.has(node.id) || seen.size > 16) return null;
    seen.add(node.id);
    const v = values(node);
    if (node.type === "LoadImage") {
        if (!v.image) return null;
        const match = String(v.image).match(/^(.*?)(?:\s+\[(input|output|temp)\])?$/);
        return { url: viewURL({ filename: match[1], type: match[2] || "input" }), transforms: [] };
    }
    if (node.type === "Reroute") return sourceDescriptor(inputNode(node, node.inputs?.[0]?.name), seen);
    if (["ImageScale", "ImageScaleBy"].includes(node.type)) {
        const source = sourceDescriptor(inputNode(node, "image"), seen);
        if (source) { source.transforms.push({ type: node.type, ...v }); return source; }
    }
    const output = app.nodeOutputs?.[node.id];
    return output?.images?.[0] ? { url: viewURL(output.images[0]), transforms: [] } : null;
}

function rounded(value) {
    const floor = Math.floor(value);
    return value - floor === 0.5 ? floor + floor % 2 : Math.round(value);
}

function layout(node) {
    const s = node._smartTile;
    localize(node);
    const aspect = s.image ? s.image.naturalHeight / s.image.naturalWidth : 1;
    const height = s.image ? Math.round(Math.min(240, Math.max(1,node.size[0]-24) * aspect)) : 0;
    s.wrapper.style.display=height ? "block" : "none";
    const row=s.wrapper.closest(".lg-node-widget");
    if (row) row.style.display=height ? "" : "none";
    if (height !== s.height) {
        s.height = height;
        s.wrapper.style.height = height ? "100%" : "0px";
    }
    app.graph?.setDirtyCanvas(true, true);
}

function draw(s) {
    if (s.removed) return;
    if (!s.image) return;
    const canvas = s.canvas;
    const width = canvas.clientWidth || 392, height = canvas.clientHeight || s.height;
    const ratio = Math.min(4,Math.max(2,(window.devicePixelRatio || 1)*(app.canvas?.ds?.scale || 1)));
    s.pixelRatio=ratio;
    if (canvas.width !== Math.round(width * ratio) || canvas.height !== Math.round(height * ratio)) {
        canvas.width = Math.round(width * ratio); canvas.height = Math.round(height * ratio);
    }
    const ctx = canvas.getContext("2d");
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    ctx.imageSmoothingQuality="high";
    ctx.clearRect(0, 0, width, height);
    const plan = s.plan;
    const iw=plan?.width || s.image.naturalWidth, ih=plan?.height || s.image.naturalHeight;
    const scale = Math.min(width / iw, height / ih);
    const rect = s.rect = { x: (width-iw*scale)/2, y: (height-ih*scale)/2, w: iw*scale, h: ih*scale, scale };
    ctx.save();
    ctx.beginPath(); ctx.rect(rect.x, rect.y, rect.w, rect.h); ctx.clip();
    ctx.drawImage(s.image, rect.x, rect.y, rect.w, rect.h);
    if (!plan) { ctx.restore(); return; }
    function region(coords) {
        return [rect.x+coords[0]*scale, rect.y+coords[1]*scale, (coords[2]-coords[0])*scale, (coords[3]-coords[1])*scale];
    }
    const selected = plan.tiles[s.adjusting ? 0 : (s.hovered ?? -1)];
    if (selected) {
        const core=region(selected.core), crop=region(selected.crop);
        ctx.beginPath(); ctx.rect(...crop); ctx.rect(...core);
        ctx.fillStyle = "rgba(45,145,255,.24)"; ctx.fill("evenodd");
    }
    for (const tile of plan.tiles) {
        const r = region(tile.core);
        const progress = s.tileProgress?.[tile.id];
        if (progress > 0) {
            ctx.fillStyle = `rgba(255,255,255,${progress >= 1 ? 0.035 : 0.09})`;
            ctx.fillRect(...r);
        }
    }
    ctx.beginPath();
    for (let col=1; col<plan.columns; col++) {
        const x=rect.x+plan.tiles[col].core[0]*scale;
        ctx.moveTo(x,rect.y); ctx.lineTo(x,rect.y+rect.h);
    }
    for (let row=1; row<plan.rows; row++) {
        const y=rect.y+plan.tiles[row*plan.columns].core[1]*scale;
        ctx.moveTo(rect.x,y); ctx.lineTo(rect.x+rect.w,y);
    }
    ctx.lineWidth=1.5; ctx.strokeStyle="#ffffff"; ctx.stroke();
    if (selected) {
        const crop=region(selected.crop);
        ctx.lineWidth=2; ctx.strokeStyle="#399cff";
        ctx.strokeRect(crop[0]+1,crop[1]+1,Math.max(0,crop[2]-2),Math.max(0,crop[3]-2));
    }
    ctx.restore();
    if (s.running) {
        ctx.fillStyle = "rgba(200,200,200,.85)"; ctx.fillRect(rect.x,rect.y+rect.h-2,rect.w*(s.progress || 0),2);
    }
}

async function updatePlan(node, force=false) {
    const s = node._smartTile;
    if (!s || s.removed) return;
    if (s.running) return;
    const descriptor = sourceDescriptor(inputNode(node,"image"));
    const sourceKey = descriptor ? JSON.stringify(descriptor) : null;
    const connected=node.inputs?.some(i=>i.name==="image" && i.link!=null);
    if (!connected) {
        s.imageVersion++; s.planVersion++;
        s.sourceKey=null; s.loadingKey=null; s.sourceSize=null; s.descriptorSize=null;
        s.requestKey=null; s.pendingKey=null; s.plan=null; s.image=null; s.hovered=null;
        layout(node); return;
    }
    if (descriptor && (sourceKey !== s.sourceKey || force) && sourceKey !== s.loadingKey) {
        s.loadingKey=sourceKey;
        const version = ++s.imageVersion;
        s.planVersion++;
        try {
            const image = await loadImage(descriptor.url);
            if (s.removed || version !== s.imageVersion) return;
            let w=image.naturalWidth, h=image.naturalHeight;
            for (const transform of descriptor.transforms) {
                if (transform.type === "ImageScaleBy") { w=rounded(w*transform.scale_by); h=rounded(h*transform.scale_by); }
                else if (transform.width || transform.height) {
                    const ow=w, oh=h;
                    w=transform.width || rounded(ow*transform.height/oh);
                    h=transform.height || rounded(oh*transform.width/ow);
                }
            }
            s.sourceKey=sourceKey; s.requestKey=null; s.plan=null;
            s.image=image; s.descriptorSize=[w,h]; s.sourceSize=[w,h]; layout(node); draw(s);
        } catch {
            if (version===s.imageVersion) {
                s.image=null; s.plan=null; s.sourceSize=null; s.sourceKey=null; layout(node);
            }
            return;
        } finally { if (s.loadingKey===sourceKey) s.loadingKey=null; }
    }
    if (sourceKey!==s.sourceKey && descriptor) return;
    if (descriptor && s.descriptorSize) s.sourceSize=s.descriptorSize;
    if (!s.sourceSize) { draw(s); return; }
    const v=values(node), body={width:s.sourceSize[0], height:s.sourceSize[1]};
    for (const key of planKeys) body[key]=v[key];
    const requestKey=JSON.stringify(body);
    if ((!force && requestKey===s.requestKey) || requestKey===s.pendingKey) return;
    s.pendingKey=requestKey;
    const version=++s.planVersion;
    try {
        const response=await api.fetchApi("/smart-tile-refine/plan",{method:"POST",headers:{"Content-Type":"application/json"},body:requestKey});
        const data=await response.json();
        if (s.removed || version!==s.planVersion) return;
        if (!response.ok) { s.plan=null; draw(s); return; }
        s.plan=data; s.requestKey=requestKey;
        s.running=false; s.tileProgress={}; s.progress=0;
        layout(node);
    } catch { if (version===s.planVersion) s.plan=null; }
    finally { if (s.pendingKey===requestKey) s.pendingKey=null; }
    draw(s);
}

async function receive(node, data) {
    const s=node?._smartTile;
    if (!s) return;
    const current=values(node);
    const executing=data.running || (data.run_id && data.run_id===s.runId && s.running);
    if (!executing && data.settings && planKeys.some(k=>current[k]!==data.settings[k])) return;
    if (!executing && data.source_size && s.descriptorSize && data.source_size.some((v,i)=>v!==s.descriptorSize[i])) return;
    if (data.plan) {
        s.plan=data.plan; s.sourceSize=data.source_size || s.sourceSize;
        const body={width:s.sourceSize[0],height:s.sourceSize[1]};
        for (const key of planKeys) body[key]=data.settings?.[key] ?? current[key];
        s.requestKey=JSON.stringify(body); layout(node);
    }
    if (data.run_id && data.run_id!==s.runId) { s.runId=data.run_id; s.tileProgress={}; s.progress=0; }
    if (data.thumbnail && data.thumbnail!==s.thumbnail) {
        s.thumbnail=data.thumbnail;
        const image=await loadImage(`data:image/png;base64,${data.thumbnail}`);
        if (s.runId!==data.run_id) return;
        s.image=image; layout(node);
    }
    if (data.tile_progress) for (const [key,value] of Object.entries(data.tile_progress)) s.tileProgress[key]=Math.max(s.tileProgress[key] || 0,value);
    if (data.progress!=null) s.progress=Math.max(s.progress || 0,data.progress);
    if (data.running!=null) s.running=data.running;
    draw(s);
    if (data.running===false) setTimeout(()=>updatePlan(node),0);
}

api.addEventListener("smart-tile-refine.preview",({detail})=>receive(nodes.get(String(detail.node)),detail));
for (const event of ["execution_error","execution_interrupted"]) api.addEventListener(event,()=>{
    for (const node of nodes.values()) if (node._smartTile?.running) { node._smartTile.running=false; draw(node._smartTile); }
});

app.registerExtension({
    name:"SmartTileRefine.Preview",
    beforeRegisterNodeDef(nodeType,nodeData) {
        if (nodeData.name!=="SmartTileRefine") return;
        const created=nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated=function() {
            const result=created?.apply(this,arguments);
            const wrapper=document.createElement("div");
            wrapper.style.cssText="width:100%;height:100%;min-height:0;position:relative;overflow:hidden;background:transparent;display:none";
            const canvas=document.createElement("canvas");
            canvas.style.cssText="display:block;width:100%;height:100%;cursor:crosshair;touch-action:none";
            canvas.setAttribute("role","img"); wrapper.append(canvas);
            const s=this._smartTile={node:this,wrapper,canvas,height:0,hovered:null,plan:null,sourceSize:null,imageVersion:0,planVersion:0,tileProgress:{}};
            const widget=this.addDOMWidget("tile_preview","SMART_TILE_PREVIEW",wrapper,{serialize:false,hideOnZoom:false,margin:0,getMinHeight:()=>0,getMaxHeight:()=>s.image ? Infinity : 0,getHeight:()=>s.height});
            widget.computeSize=width=>[width,s.height || -4];
            const placePreview=()=>{
                const row=wrapper.closest(".lg-node-widget");
                if (row) { row.style.order="-1"; row.style.display=s.image ? "" : "none"; }
            };
            localize(this);
            for (const w of this.widgets) if (english[w.name]) {
                const callback=w.callback;
                w.callback=(...args)=>{
                    const result=callback?.apply(w,args);
                    if (w.name==="expand_percent") {
                        s.adjusting=true; clearTimeout(s.extensionTimer); draw(s);
                        s.extensionTimer=setTimeout(()=>{ s.adjusting=false; draw(s); },900);
                    }
                    clearTimeout(s.debounce); s.debounce=setTimeout(()=>updatePlan(this),100);
                    return result;
                };
            }
            const select=event=>{
                event.stopPropagation();
                if (!s.rect || !s.plan) return;
                const box=canvas.getBoundingClientRect();
                const x=((event.clientX-box.left)*canvas.clientWidth/box.width-s.rect.x)/s.rect.scale;
                const y=((event.clientY-box.top)*canvas.clientHeight/box.height-s.rect.y)/s.rect.scale;
                const tile=s.plan.tiles.find(t=>x>=t.core[0] && x<t.core[2] && y>=t.core[1] && y<t.core[3]);
                const hovered=tile?.id ?? null;
                if (hovered!==s.hovered) { s.hovered=hovered; draw(s); }
            };
            canvas.addEventListener("pointerdown",select); canvas.addEventListener("pointermove",select);
            canvas.addEventListener("pointerleave",()=>{ s.hovered=null; draw(s); });
            s.observer=new ResizeObserver(()=>{ placePreview(); if (!s.frame) s.frame=requestAnimationFrame(()=>{ s.frame=null; draw(s); }); });
            s.observer.observe(wrapper);
            s.timer=setInterval(()=>{
                nodes.set(String(this.id),this); updatePlan(this);
                if (s.locale!==language()) { localize(this); app.graph?.setDirtyCanvas(true,true); }
                const ratio=Math.min(4,Math.max(2,(window.devicePixelRatio || 1)*(app.canvas?.ds?.scale || 1)));
                if (s.image && ratio!==s.pixelRatio) draw(s);
            },750);
            nodes.set(String(this.id),this);
            setTimeout(()=>{ placePreview(); layout(this); updatePlan(this); draw(s); },0);
            return result;
        };
        const configured=nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure=function() {
            const result=configured?.apply(this,arguments);
            const mode=this.widgets?.find(w=>w.name==="redraw_mode");
            if (mode?.value==="分块独立重绘") mode.value="Independent tiles";
            if (["蛇形依次重绘","S形依次重绘"].includes(mode?.value)) mode.value="S-shaped sequence";
            nodes.set(String(this.id),this);
            setTimeout(()=>{ layout(this); updatePlan(this,true); },0);
            return result;
        };
        const connected=nodeType.prototype.onConnectionsChange;
        nodeType.prototype.onConnectionsChange=function() {
            const result=connected?.apply(this,arguments);
            setTimeout(()=>updatePlan(this),0);
            return result;
        };
        const resized=nodeType.prototype.onResize;
        nodeType.prototype.onResize=function() {
            const result=resized?.apply(this,arguments);
            const s=this._smartTile;
            if (s && !s.resizing) { s.resizing=true; layout(this); s.resizing=false; draw(s); }
            return result;
        };
        const executed=nodeType.prototype.onExecuted;
        nodeType.prototype.onExecuted=function(message) {
            const result=executed?.apply(this,arguments);
            if (message.smart_tile?.[0]) receive(this,message.smart_tile[0]);
            return result;
        };
        const removed=nodeType.prototype.onRemoved;
        nodeType.prototype.onRemoved=function() {
            const s=this._smartTile; s.removed=true;
            clearInterval(s.timer); clearTimeout(s.debounce); clearTimeout(s.extensionTimer); s.observer.disconnect();
            if (s.frame) cancelAnimationFrame(s.frame);
            nodes.delete(String(this.id));
            return removed?.apply(this,arguments);
        };
    },
});
