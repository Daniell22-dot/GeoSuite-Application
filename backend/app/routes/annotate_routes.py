"""
Training data annotation tool — web-based labeling for CV model training.
"""
import os
import json
import uuid
import shutil
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.geospatial import User, Annotation
from app.services.auth_service import auth_service

router = APIRouter(prefix="/api/v1/annotate", tags=["annotation"])

ANNOTATION_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'annotation_data')
IMAGES_DIR = os.path.join(ANNOTATION_DIR, 'images')
ANNOTATIONS_DIR = os.path.join(ANNOTATION_DIR, 'annotations')

os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(ANNOTATIONS_DIR, exist_ok=True)


class BeaconAnnotation(BaseModel):
    x: float
    y: float
    width: float
    height: float
    beacon_type: str = "unknown"
    label: Optional[str] = None


class BoundaryAnnotation(BaseModel):
    points: list
    label: Optional[str] = None


class TextAnnotation(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float
    text: str
    label_type: str = "annotation"


class ImageAnnotation(BaseModel):
    image_id: str
    beacons: list = []
    boundaries: list = []
    text_labels: list = []
    notes: Optional[str] = None


@router.post("/upload")
async def upload_image_for_annotation(
    file: UploadFile = File(...),
    survey_name: str = Form(""),
    description: str = Form(""),
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    image_id = str(uuid.uuid4())[:8]
    ext = os.path.splitext(file.filename)[1].lower()
    save_path = os.path.join(IMAGES_DIR, f"{image_id}{ext}")
    contents = await file.read()
    with open(save_path, 'wb') as f:
        f.write(contents)

    meta = {
        "id": image_id,
        "filename": file.filename,
        "stored_path": save_path,
        "survey_name": survey_name,
        "description": description,
        "annotated": False,
    }
    meta_path = os.path.join(ANNOTATIONS_DIR, f"{image_id}_meta.json")
    with open(meta_path, 'w') as f:
        json.dump(meta, f, indent=2)

    annotation = Annotation(
        id=uuid.uuid4(),
        user_id=user.id,
        image_id=image_id,
        image_path=save_path,
        annotations={},
        annotated=False,
    )
    db.add(annotation)
    db.commit()

    return JSONResponse(content=meta)


@router.get("/images")
async def list_annotated_images(
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    images = []
    for fname in os.listdir(ANNOTATIONS_DIR):
        if fname.endswith('_meta.json'):
            with open(os.path.join(ANNOTATIONS_DIR, fname)) as f:
                meta = json.load(f)
            ann_path = os.path.join(ANNOTATIONS_DIR, meta['id'] + '.json')
            if os.path.exists(ann_path):
                meta['annotated'] = True
            images.append(meta)
    return JSONResponse(content={"images": images, "total": len(images)})


@router.get("/image/{image_id}")
async def get_image_for_annotation(
    image_id: str,
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    meta_path = os.path.join(ANNOTATIONS_DIR, f"{image_id}_meta.json")
    if not os.path.exists(meta_path):
        raise HTTPException(status_code=404, detail="Image not found")
    with open(meta_path) as f:
        meta = json.load(f)
    ann_path = os.path.join(ANNOTATIONS_DIR, f"{image_id}.json")
    annotations = {}
    if os.path.exists(ann_path):
        with open(ann_path) as f:
            annotations = json.load(f)
    return JSONResponse(content={"meta": meta, "annotations": annotations})


@router.post("/save/{image_id}")
async def save_annotations(
    image_id: str,
    annotations: dict,
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    ann_path = os.path.join(ANNOTATIONS_DIR, f"{image_id}.json")
    with open(ann_path, 'w') as f:
        json.dump(annotations, f, indent=2)
    meta_path = os.path.join(ANNOTATIONS_DIR, f"{image_id}_meta.json")
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            meta = json.load(f)
        meta['annotated'] = True
        with open(meta_path, 'w') as f:
            json.dump(meta, f, indent=2)

    annotation = db.query(Annotation).filter(
        Annotation.user_id == user.id,
        Annotation.image_id == image_id,
    ).first()
    if annotation is None:
        annotation = Annotation(
            id=uuid.uuid4(),
            user_id=user.id,
            image_id=image_id,
            image_path=meta_path,
            annotations=annotations,
            annotated=True,
        )
        db.add(annotation)
    else:
        annotation.annotations = annotations
        annotation.annotated = True
    db.commit()

    return JSONResponse(content={"status": "saved", "image_id": image_id})


@router.delete("/image/{image_id}")
async def delete_annotation(
    image_id: str,
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    for ext in ['.jpg', '.jpeg', '.tif', '.tiff', '.png', '.pdf']:
        img_path = os.path.join(IMAGES_DIR, f"{image_id}{ext}")
        if os.path.exists(img_path):
            os.remove(img_path)
    for suffix in ['_meta.json', '.json']:
        ann_path = os.path.join(ANNOTATIONS_DIR, f"{image_id}{suffix}")
        if os.path.exists(ann_path):
            os.remove(ann_path)

    annotation = db.query(Annotation).filter(
        Annotation.user_id == user.id,
        Annotation.image_id == image_id,
    ).first()
    if annotation:
        db.delete(annotation)
        db.commit()

    return JSONResponse(content={"status": "deleted", "image_id": image_id})


@router.get("/export")
async def export_annotations(
    format: str = "coco",
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    all_annotations = []
    for fname in sorted(os.listdir(ANNOTATIONS_DIR)):
        if fname.endswith('.json') and not fname.endswith('_meta.json'):
            with open(os.path.join(ANNOTATIONS_DIR, fname)) as f:
                ann = json.load(f)
            all_annotations.append(ann)

    if format == "coco":
        images = []
        annotations = []
        categories = [
            {"id": 1, "name": "beacon", "supercategory": "survey"},
            {"id": 2, "name": "boundary", "supercategory": "survey"},
            {"id": 3, "name": "text_label", "supercategory": "survey"},
        ]
        ann_id = 1
        for img_idx, ann in enumerate(all_annotations, start=1):
            images.append({"id": img_idx, "file_name": ann.get("image_id", ""), "width": 0, "height": 0})
            for b in ann.get('beacons', []):
                annotations.append({
                    "id": ann_id,
                    "image_id": img_idx,
                    "category_id": 1,
                    "bbox": [b.get('x', 0), b.get('y', 0), b.get('width', 0), b.get('height', 0)],
                    "area": b.get('width', 0) * b.get('height', 0),
                    "iscrowd": 0,
                })
                ann_id += 1
            for b in ann.get('boundaries', []):
                annotations.append({
                    "id": ann_id,
                    "image_id": img_idx,
                    "category_id": 2,
                    "segmentation": [p for pts in b.get('points', []) for p in pts],
                    "bbox": [],
                    "area": 0,
                    "iscrowd": 0,
                })
                ann_id += 1
            for t in ann.get('text_labels', []):
                annotations.append({
                    "id": ann_id,
                    "image_id": img_idx,
                    "category_id": 3,
                    "bbox": [t.get('x1', 0), t.get('y1', 0), t.get('x2', 0) - t.get('x1', 0), t.get('y2', 0) - t.get('y1', 0)],
                    "area": abs((t.get('x2', 0) - t.get('x1', 0)) * (t.get('y2', 0) - t.get('y1', 0))),
                    "iscrowd": 0,
                })
                ann_id += 1
        return JSONResponse(content={"images": images, "annotations": annotations, "categories": categories, "format": "coco", "total_images": len(images)})
    elif format == "yolo":
        yolo_data = []
        for ann in all_annotations:
            for beacon in ann.get('beacons', []):
                yolo_data.append({
                    "image": ann.get('image_id', ''),
                    "class": 0,
                    "x_center": beacon['x'],
                    "y_center": beacon['y'],
                    "width": beacon['width'],
                    "height": beacon['height'],
                })
        return JSONResponse(content={"annotations": yolo_data, "format": "yolo", "total": len(yolo_data)})
    return JSONResponse(content={"annotations": all_annotations, "format": format})


@router.get("/stats")
async def get_annotation_stats(
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    total_images = 0
    annotated_images = 0
    total_beacons = 0
    total_boundaries = 0
    total_labels = 0
    for fname in os.listdir(ANNOTATIONS_DIR):
        if fname.endswith('_meta.json'):
            total_images += 1
            with open(os.path.join(ANNOTATIONS_DIR, fname)) as f:
                meta = json.load(f)
            ann_path = os.path.join(ANNOTATIONS_DIR, meta['id'] + '.json')
            if os.path.exists(ann_path):
                annotated_images += 1
                with open(ann_path) as f:
                    ann = json.load(f)
                total_beacons += len(ann.get('beacons', []))
                total_boundaries += len(ann.get('boundaries', []))
                total_labels += len(ann.get('text_labels', []))
    return JSONResponse(content={
        "total_images": total_images,
        "annotated_images": annotated_images,
        "pending_images": total_images - annotated_images,
        "total_beacons": total_beacons,
        "total_boundaries": total_boundaries,
        "total_labels": total_labels,
    })


@router.get("/images/{image_id}{ext:path}")
async def serve_annotation_image(image_id: str, ext: str):
    for e in ['.jpg', '.jpeg', '.tif', '.tiff', '.png', '.pdf']:
        path = os.path.join(IMAGES_DIR, f"{image_id}{e}")
        if os.path.exists(path):
            media = "image/png" if e == '.png' else "image/jpeg" if e in ('.jpg', '.jpeg') else "image/tiff" if e in ('.tif', '.tiff') else "application/pdf"
            return StreamingResponse(open(path, 'rb'), media_type=media)
    raise HTTPException(status_code=404, detail="Image not found")


@router.get("/editor", response_class=HTMLResponse)
async def get_annotation_editor():
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>KLISS Annotation Tool</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter',sans-serif;background:#0f172a;color:#f8fafc;height:100vh;display:flex;flex-direction:column}
header{background:rgba(30,41,59,0.9);padding:12px 24px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid rgba(255,255,255,0.1)}
header h1{font-size:1.2rem;font-weight:700}
header .stats{font-size:0.8rem;color:#94a3b8}
.main{flex:1;display:flex;overflow:hidden}
.sidebar{width:300px;background:rgba(30,41,59,0.5);border-right:1px solid rgba(255,255,255,0.1);overflow-y:auto;padding:16px}
.sidebar h3{font-size:0.9rem;margin-bottom:12px;color:#94a3b8;text-transform:uppercase;letter-spacing:1px;font-weight:600}
.upload-zone{border:2px dashed rgba(255,255,255,0.15);border-radius:12px;padding:24px;text-align:center;cursor:pointer;margin-bottom:16px;transition:all 0.2s}
.upload-zone:hover{border-color:#0a84ff;background:rgba(10,132,255,0.05)}
.tool-btn{display:block;width:100%;padding:10px 14px;margin-bottom:6px;background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.08);border-radius:8px;color:#f8fafc;cursor:pointer;text-align:left;font-size:0.85rem;transition:all 0.2s}
.tool-btn:hover{background:rgba(10,132,255,0.15);border-color:#0a84ff}
.tool-btn.active{background:rgba(10,132,255,0.2);border-color:#0a84ff;color:#409fff}
.canvas-area{flex:1;display:flex;align-items:center;justify-content:center;position:relative;overflow:hidden;background:rgba(0,0,0,0.3)}
canvas{cursor:crosshair;max-width:100%;max-height:100%}
.right-panel{width:280px;background:rgba(30,41,59,0.5);border-left:1px solid rgba(255,255,255,0.1);overflow-y:auto;padding:16px}
.ann-list{list-style:none}
.ann-list li{padding:8px 10px;margin-bottom:4px;background:rgba(255,255,255,0.03);border-radius:6px;font-size:0.8rem;display:flex;justify-content:space-between;align-items:center}
.ann-list li .del{color:#ef4444;cursor:pointer;font-size:0.7rem}
select,input[type=text],input[type=number]{width:100%;padding:8px 10px;margin-bottom:8px;background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);border-radius:6px;color:#f8fafc;font-size:0.85rem}
.action-bar{display:flex;gap:8px;margin-top:12px}
.action-bar button{flex:1;padding:8px;border:none;border-radius:8px;cursor:pointer;font-weight:600;font-size:0.8rem}
.btn-primary{background:#0a84ff;color:#fff}
.btn-secondary{background:rgba(255,255,255,0.1);color:#f8fafc}
.btn-danger{background:#ef4444;color:#fff}
</style>
</head>
<body>
<header>
  <h1>KLISS Annotation Tool</h1>
  <div class="stats" id="stats">Loading...</div>
</header>
<div class="main">
  <div class="sidebar">
    <h3>Upload</h3>
    <div class="upload-zone" id="dropZone">
      <input type="file" id="fileInput" accept="image/*" style="display:none" multiple>
      <p style="font-size:0.85rem">Drop survey plans here<br>or click to browse</p>
    </div>
    <h3>Tools</h3>
    <button class="tool-btn active" data-tool="beacon" onclick="setTool('beacon')">Beacon (draw box)</button>
    <button class="tool-btn" data-tool="boundary" onclick="setTool('boundary')">Boundary (draw polygon)</button>
    <button class="tool-btn" data-tool="text" onclick="setTool('text')">Text label (draw box)</button>
    <button class="tool-btn" data-tool="pan" onclick="setTool('pan')">Pan / Navigate</button>
    <h3 style="margin-top:16px">Beacon Type</h3>
    <select id="beaconType">
      <option value="iron_pin">Iron Pin</option>
      <option value="concrete">Concrete Pillar</option>
      <option value="triangle">Triangle</option>
      <option value="unknown">Unknown</option>
    </select>
    <h3 style="margin-top:16px">Text Type</h3>
    <select id="textType">
      <option value="bearing">Bearing</option>
      <option value="distance">Distance</option>
      <option value="beacon_id">Beacon ID</option>
      <option value="title_reference">Title Reference</option>
      <option value="plan_number">Plan Number</option>
      <option value="scale">Scale</option>
      <option value="annotation">Other Annotation</option>
    </select>
  </div>
  <div class="canvas-area">
    <canvas id="canvas" width="800" height="600"></canvas>
  </div>
  <div class="right-panel">
    <h3>Annotations</h3>
    <ul class="ann-list" id="annList"></ul>
    <div class="action-bar">
      <button class="btn-primary" onclick="saveAnnotations()">Save</button>
      <button class="btn-danger" onclick="clearAll()">Clear</button>
    </div>
    <h3 style="margin-top:20px">Image List</h3>
    <div id="imageList" style="font-size:0.8rem"></div>
  </div>
</div>
<script>
const canvas=document.getElementById('canvas'),ctx=canvas.getContext('2d');
let currentTool='beacon',imageLoaded=false,currentImageId=null;
let annotations={beacons:[],boundaries:[],text_labels:[]};
let drawState={drawing:false,startX:0,startY:0,points:[],tempPoints:[]};
const beaconColors={iron_pin:'#0a84ff',concrete:'#5e5ce6',triangle:'#ed6c02',unknown:'#94a3b8'};

function setTool(tool){currentTool=tool;document.querySelectorAll('.tool-btn').forEach(b=>{b.classList.toggle('active',b.dataset.tool===tool)});canvas.style.cursor=tool==='pan'?'grab':'crosshair'}

document.getElementById('dropZone').onclick=()=>document.getElementById('fileInput').click();
document.getElementById('fileInput').onchange=e=>{Array.from(e.target.files).forEach(uploadImage)};
document.getElementById('dropZone').ondragover=e=>{e.preventDefault();e.currentTarget.style.borderColor='#0a84ff'};
document.getElementById('dropZone').ondragleave=e=>{e.currentTarget.style.borderColor='rgba(255,255,255,0.15)'};
document.getElementById('dropZone').ondrop=e=>{e.preventDefault();Array.from(e.dataTransfer.files).forEach(uploadImage)};

async function uploadImage(file){
const fd=new FormData();fd.append('file',file);fd.append('survey_name',file.name);
const r=await fetch('/api/v1/annotate/upload',{method:'POST',body:fd});
const d=await r.json();loadImage(d.id);
}

async function loadImage(id){
const r=await fetch('/api/v1/annotate/image/'+id);const d=await r.json();
currentImageId=id;annotations=d.annotations||{beacons:[],boundaries:[],text_labels:[]};
const img=new Image();img.onload=()=>{canvas.width=img.width;canvas.height=img.height;ctx.drawImage(img,0,0);imageLoaded=true;redrawAnnotations()};
img.src='/api/v1/annotate/images/'+id+'.png';
}

function redrawAnnotations(){
if(!imageLoaded)return;ctx.clearRect(0,0,canvas.width,canvas.height);
annotations.beacons.forEach(b=>{ctx.strokeStyle=beaconColors[b.beacon_type]||'#0a84ff';ctx.lineWidth=2;ctx.strokeRect(b.x,b.y,b.width,b.height);ctx.fillStyle=beaconColors[b.beacon_type]||'#0a84ff';ctx.font='10px Inter';ctx.fillText(b.beacon_type,b.x,b.y-4)});
annotations.text_labels.forEach(t=>{ctx.strokeStyle='#ed6c02';ctx.lineWidth=1;ctx.setLineDash([4,4]);ctx.strokeRect(t.x1,t.y1,t.x2-t.x1,t.y2-t.y1);ctx.setLineDash([]);ctx.fillStyle='#ed6c02';ctx.font='9px Inter';ctx.fillText(t.text,t.x1,t.y1-4)});
annotations.boundaries.forEach(b=>{if(b.points.length<2)return;ctx.strokeStyle='#4caf50';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(b.points[0][0],b.points[0][1]);b.points.slice(1).forEach(p=>ctx.lineTo(p[0],p[1]));ctx.closePath();ctx.stroke()});
updateAnnList();
}

canvas.onmousedown=e=>{const rect=canvas.getBoundingClientRect();const sx=canvas.width/rect.width,sy=canvas.height/rect.height;const x=(e.clientX-rect.left)*sx,y=(e.clientY-rect.top)*sy;
if(currentTool==='pan'){drawState={drawing:true,tool:'pan',lastX:e.clientX,lastY:e.clientY};return}
if(currentTool==='boundary'){drawState.tempPoints.push([x,y]);redrawAnnotations();drawTempBoundary();return}
drawState={drawing:true,tool:currentTool,startX:x,startY:y}};

canvas.onmousemove=e=>{if(!drawState.drawing)return;if(drawState.tool==='pan'){return}};

canvas.onmouseup=e=>{if(!drawState.drawing)return;
const rect=canvas.getBoundingClientRect();const sx=canvas.width/rect.width,sy=canvas.height/rect.height;
const x=(e.clientX-rect.left)*sx,y=(e.clientY-rect.top)*sy;
if(drawState.tool==='beacon'){const bx=Math.min(drawState.startX,x),by=Math.min(drawState.startY,y);const bw=Math.abs(x-drawState.startX),bh=Math.abs(y-drawState.startY);if(bw>5&&bh>5){annotations.beacons.push({x:bx,y:by,width:bw,height:bh,beacon_type:document.getElementById('beaconType').value,label:''})}}
if(drawState.tool==='text'){const bx=Math.min(drawState.startX,x),by=Math.min(drawState.startY,y);const bw=Math.abs(x-drawState.startX),bh=Math.abs(y-drawState.startY);if(bw>5&&bh>5){const txt=prompt('Enter text content:','');if(txt)annotations.text_labels.push({x1:bx,y1:by,x2:bx+bw,y2:by+bh,text:txt,label_type:document.getElementById('textType').value})}}
drawState={drawing:false,tempPoints:drawState.tempPoints||[]};redrawAnnotations()};

canvas.ondblclick=e=>{if(currentTool==='boundary'&&drawState.tempPoints.length>=3){annotations.boundaries.push({points:[...drawState.tempPoints],label:''});drawState.tempPoints=[];redrawAnnotations()}};

function drawTempBoundary(){if(drawState.tempPoints.length<1)return;ctx.strokeStyle='#4caf50';ctx.lineWidth=2;ctx.setLineDash([6,3]);ctx.beginPath();ctx.moveTo(drawState.tempPoints[0][0],drawState.tempPoints[0][1]);drawState.tempPoints.slice(1).forEach(p=>ctx.lineTo(p[0],p[1]));ctx.stroke();ctx.setLineDash([]);drawState.tempPoints.forEach(p=>{ctx.fillStyle='#4caf50';ctx.beginPath();ctx.arc(p[0],p[1],3,0,Math.PI*2);ctx.fill()})}

function updateAnnList(){const list=document.getElementById('annList');list.innerHTML='';
annotations.beacons.forEach((b,i)=>{list.innerHTML+='<li>Beacon '+(i+1)+' ('+b.beacon_type+')<span class="del" onclick="annotations.beacons.splice('+i+',1);updateAnnList();redrawAnnotations()">x</span></li>'});
annotations.text_labels.forEach((t,i)=>{list.innerHTML+='<li>Text: '+t.text+'<span class="del" onclick="annotations.text_labels.splice('+i+',1);updateAnnList();redrawAnnotations()">x</span></li>'});
annotations.boundaries.forEach((b,i)=>{list.innerHTML+='<li>Boundary '+(i+1)+' ('+b.points.length+' pts)<span class="del" onclick="annotations.boundaries.splice('+i+',1);updateAnnList();redrawAnnotations()">x</span></li>'})}

async function saveAnnotations(){if(!currentImageId)return;await fetch('/api/v1/annotate/save/'+currentImageId,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(annotations)});alert('Saved!')}

function clearAll(){annotations={beacons:[],boundaries:[],text_labels:[]};redrawAnnotations()}

async function loadStats(){const r=await fetch('/api/v1/annotate/stats');const d=await r.json();document.getElementById('stats').textContent=d.annotated_images+'/'+d.total_images+' annotated | '+d.total_beacons+' beacons | '+d.total_boundaries+' boundaries'}
loadStats();
</script>
</body></html>"""
