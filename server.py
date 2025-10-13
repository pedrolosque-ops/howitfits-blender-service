from fastapi import FastAPI, UploadFile, Form, HTTPException, Header, Depends
from fastapi.responses import FileResponse
import subprocess, os, tempfile, shutil

app = FastAPI()

EXPECTED_TOKEN = os.getenv("AUTH_BEARER_TOKEN")

def require_bearer(authorization: str = Header(None)):
    if not EXPECTED_TOKEN:
        raise HTTPException(status_code=500, detail="AUTH_BEARER_TOKEN not set on server")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    token = authorization.split(" ", 1)[1].strip()
    if token != EXPECTED_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid token")

@app.get("/health")
def health():
    return {"ok": True, "service": "howitfits-blender-service"}

def run_blender_scale(input_path: str, output_path: str, scale_factor: float):
    cmd = [
        "xvfb-run", "-a", "blender", "--background",
        "--python", "scale_export.py", "--", input_path, output_path, str(scale_factor)
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Blender error:\n{result.stderr}")

@app.post("/scale", dependencies=[Depends(require_bearer)])
async def scale_model(
    model: UploadFile,
    axis: str = Form("x"),
    base_length_cm: float = Form(100),
    target_length_cm: float = Form(100)
):
    try:
        if target_length_cm <= 0 or base_length_cm <= 0:
            raise HTTPException(status_code=400, detail="base_length_cm e target_length_cm devem ser > 0")

        scale_factor = target_length_cm / base_length_cm

        tmpdir = tempfile.mkdtemp()
        src_path = os.path.join(tmpdir, model.filename)
        with open(src_path, "wb") as f:
            f.write(await model.read())

        out_name = os.path.splitext(model.filename)[0] + "_scaled.glb"
        out_path = os.path.join(tmpdir, out_name)

        run_blender_scale(src_path, out_path, scale_factor)

        return FileResponse(out_path, media_type="model/gltf-binary", filename=out_name)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
