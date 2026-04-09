from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
import os
import shutil
from datetime import datetime
from bson import ObjectId
from ..database import get_collection
from ..dependencies import get_current_active_user, require_role

router = APIRouter()
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    description: str = "",
    current_user = Depends(get_current_active_user)
):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    doc = {
        "filename": file.filename,
        "original_name": file.filename,
        "path": file_path,
        "uploaded_by": current_user.email,
        "description": description,
        "uploaded_at": datetime.utcnow(),
        "size": os.path.getsize(file_path)
    }
    result = await get_collection("documents").insert_one(doc)
    return {"message": "File uploaded", "id": str(result.inserted_id)}

@router.get("/")
async def list_documents(current_user = Depends(get_current_active_user)):
    docs = await get_collection("documents").find().to_list(100)
    return [{"id": str(d["_id"]), **{k:v for k,v in d.items() if k != "_id"}} for d in docs]

@router.get("/download/{doc_id}")
async def download_document(doc_id: str, current_user = Depends(get_current_active_user)):
    doc = await get_collection("documents").find_one({"_id": ObjectId(doc_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    file_path = doc["path"]
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on server")
    return FileResponse(file_path, filename=doc["original_name"])

@router.delete("/{doc_id}")
async def delete_document(doc_id: str, current_user = Depends(require_role(["admin"]))):
    doc = await get_collection("documents").find_one({"_id": ObjectId(doc_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if os.path.exists(doc["path"]):
        os.remove(doc["path"])
    await get_collection("documents").delete_one({"_id": ObjectId(doc_id)})
    return {"message": "Document deleted"}