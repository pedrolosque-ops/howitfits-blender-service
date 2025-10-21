from fastapi import FastAPI, UploadFile, File, Form, Header, HTTPException
from fastapi.responses import FileResponse, JSONResponse
import os, tempfile, shutil, subprocess

app = FastAPI(title="HowItFits Blender Service", version="1.0.0")

# ---------- Auth ----------
def require_bearer(auth_header: str | None) -> None:
    token_env = os.environ.get("BLENDER_SERVICE_TOKEN", "")
    if not token_env:
        raise HTTPException(status_code=500, detail="BLENDER_SERVICE_TOKEN not set")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    provided = auth_header.split(" ", 1)[1].strip()
    if provided != token_env:
        raise HTTPException(status_code=403, detail="Invalid Bearer token")

# ---------- Probes ----------
@app.get("/")
async def root():
    return JSONResponse({"ok": True, "service": "howitfits-blender-service"})

@app.get("/health")
async def health():
    return JSONResponse({"ok": True})

# ---------- Blender runner ----------
def run_blender_scale(input_path: str, output_path: str, axis: str, target_cm: float) -> None:
    """
    Executa o Blender em modo headless chamando o script 'scale_export.py'
    que deve estar no mesmo diretório do container.
    """
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
        raise RuntimeError(
            "Blender error:\n"
            f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
        )

# ---------- API ----------
@app.post("/scale")
async def scale_model(
    model: UploadFile = File(...),               # arquivo GLB
    axis: str = Form("x"),                       # x|y|z (qual eixo representa o comprimento real)
    target_length_cm: float = Form(...),         # comprimento alvo em cm (ex.: 23)
    authorization: str | None = Header(default=None, convert_underscores=False),
):
    # Auth
    require_bearer(authorization)

    # Validações
    axis = (axis or "x").lower()
    if axis not in ("x", "y", "z"):
        raise HTTPException(status_code=400, detail="axis must be one of x|y|z")
    try:
        target_val = float(target_length_cm)
    except Exception:
        raise HTTPException(status_code=400, detail="target_length_cm must be a number")
    if target_val <= 0:
        raise HTTPException(status_code=400, detail="target_length_cm must be > 0")
    if not model.filename.lower().endswith(".glb"):
        raise HTTPException(status_code=415, detail="Only .glb files are supported")

    tmpdir = tempfile.mkdtemp(prefix="blender_scale_")
    try:
        # Salva upload em disco
        src_path = os.path.join(tmpdir, model.filename)
        with open(src_path, "wb") as f:
            f.write(await model.read())

        # Saída escalada
        out_name = os.path.splitext(model.filename)[0] + "_scaled.glb"
        out_path = os.path.join(tmpdir, out_name)

        # Chama Blender
        run_blender_scale(src_path, out_path, axis, target_val)

        # Retorna GLB escalado como binário
        return FileResponse(out_path, media_type="model/gltf-binary", filename=out_name)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
