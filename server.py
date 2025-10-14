from fastapi import FastAPI, UploadFile, File, Form, Header, HTTPException
from fastapi.responses import FileResponse, JSONResponse
import os, tempfile, shutil, subprocess

app = FastAPI()

def require_bearer(auth_header: str | None) -> None:
    token_env = os.environ.get("BLENDER_SERVICE_TOKEN", "")
    if not token_env:
        raise HTTPException(status_code=500, detail="BLENDER_SERVICE_TOKEN not set")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    provided = auth_header.split(" ", 1)[1].strip()
    if provided != token_env:
        raise HTTPException(status_code=403, detail="Invalid Bearer token")

@app.get("/health")
async def health():
    return JSONResponse({"ok": True})

def run_blender_scale(input_path: str, output_path: str, axis: str, target_cm: float) -> None:
    # Executa Blender headless chamando o script Python interno
    cmd = [
        "xvfb-run", "-a", "blender", "--background",
        "--python", "scale_export.py", "--",
        "--input", input_path,
        "--output", output_path,
        "--axis", axis.lower(),
        "--target_cm", str(target_cm)
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Blender error:\nSTDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}")

@app.post("/scale")
async def scale_model(
    model: UploadFile = File(...),
    axis: str = Form("x"),
    target_length_cm: float = Form(...)
    ,
    authorization: str | None = Header(default=None, convert_underscores=False)
):
    # Auth
    require_bearer(authorization)

    # Validações básicas
    axis = axis.lower()
    if axis not in ("x", "y", "z"):
        raise HTTPException(status_code=400, detail="axis must be one of x|y|z")
    if target_length_cm is None or float(target_length_cm) <= 0:
        raise HTTPException(status_code=400, detail="target_length_cm must be > 0")
    if not model.filename.lower().endswith(".glb"):
        # aceitamos somente GLB aqui; ajuste se quiser permitir GLTF
        raise HTTPException(status_code=415, detail="Only .glb files are supported")

    tmpdir = tempfile.mkdtemp(prefix="blender_scale_")
    try:
        src_path = os.path.join(tmpdir, model.filename)
        with open(src_path, "wb") as f:
            f.write(await model.read())

        out_name = os.path.splitext(model.filename)[0] + "_scaled.glb"
        out_path = os.path.join(tmpdir, out_name)

        # Chama Blender para medir e escalar
        run_blender_scale(src_path, out_path, axis, float(target_length_cm))

        # Retorna o GLB processado
        return FileResponse(out_path, media_type="model/gltf-binary", filename=out_name)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
