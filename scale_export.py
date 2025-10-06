import bpy, sys, os

argv = sys.argv
argv = argv[argv.index("--") + 1:]
input_path, output_path, scale_str = argv[0], argv[1], argv[2]
scale = float(scale_str)

bpy.ops.wm.read_factory_settings(use_empty=True)

ext = os.path.splitext(input_path)[1].lower()
if ext in [".glb", ".gltf"]:
    bpy.ops.import_scene.gltf(filepath=input_path)
else:
    raise RuntimeError(f"Formato não suportado: {ext}")

for obj in bpy.context.scene.objects:
    if obj.type in {"MESH", "EMPTY"}:
        obj.scale = (obj.scale[0]*scale, obj.scale[1]*scale, obj.scale[2]*scale)

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

bpy.ops.export_scene.gltf(filepath=output_path, export_format='GLB')
