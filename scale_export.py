import bpy
import sys
import argparse
import math
from mathutils import Vector

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Caminho para o GLB de entrada")
    parser.add_argument("--output", required=True, help="Caminho do GLB de saída")
    parser.add_argument("--axis", required=True, choices=["x","y","z"], help="Eixo a medir")
    parser.add_argument("--target_cm", required=True, type=float, help="Comprimento desejado no eixo (cm)")
    return parser.parse_known_args()[0]

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    # remove meshes órfãs
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)

def import_glb(path):
    bpy.ops.import_scene.gltf(filepath=path, merge_vertices=True)
    # Junta tudo em um único objeto (opcional, mas simplifica medição)
    objs = [o for o in bpy.context.scene.objects if o.type == 'MESH' or o.type == 'EMPTY' or o.type == 'ARMATURE']
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0] if objs else None
    if len(objs) > 1:
        # Converter empties/armatures para mesh parented? Simples: juntar apenas meshes
        for o in bpy.context.selected_objects:
            o.select_set(False)
        meshes = [o for o in objs if o.type == 'MESH']
        if not meshes:
            return None
        for m in meshes:
            m.select_set(True)
        bpy.context.view_layer.objects.active = meshes[0]
        bpy.ops.object.join()
        return bpy.context.view_layer.objects.active
    else:
        return objs[0] if objs else None

def apply_all_transforms(obj):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    # Aplica localização/rotação/escala atuais
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    obj.select_set(False)

def bbox_world(obj):
    """Retorna min/max em coordenadas de mundo (Vector) do bounding box do objeto."""
    coords = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    min_v = Vector((min(v.x for v in coords), min(v.y for v in coords), min(v.z for v in coords)))
    max_v = Vector((max(v.x for v in coords), max(v.y for v in coords), max(v.z for v in coords)))
    return min_v, max_v

def measure_axis_length_m(obj, axis):
    """Mede comprimento (em metros) no eixo especificado, a partir do bounding box em world space."""
    min_v, max_v = bbox_world(obj)
    if axis == 'x':
        return (max_v.x - min_v.x)
    elif axis == 'y':
        return (max_v.y - min_v.y)
    else:
        return (max_v.z - min_v.z)

def uniform_scale(obj, factor):
    obj.scale = (obj.scale.x * factor, obj.scale.y * factor, obj.scale.z * factor)
    apply_all_transforms(obj)

def export_glb(path):
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format='GLB',
        export_texcoords=True,
        export_normals=True,
        export_materials='EXPORT',
        export_yup=True,
        export_apply=True    # aplica escala no export
    )

def main():
    args = parse_args()
    axis = args.axis.lower()
    target_cm = float(args.target_cm)
    if target_cm <= 0:
        print("target_cm must be > 0")
        sys.exit(2)

    # Blender usa metros por padrão
    target_m = target_cm / 100.0

    clear_scene()
    obj = import_glb(args.input)
    if obj is None:
        print("No object imported")
        sys.exit(3)

    # Aplica transforms iniciais e mede
    apply_all_transforms(obj)
    measured_m = measure_axis_length_m(obj, axis)

    if measured_m <= 0 or math.isnan(measured_m):
        print(f"Invalid measured length on axis {axis}: {measured_m}")
        sys.exit(4)

    factor = target_m / measured_m

    # Escala uniforme
    uniform_scale(obj, factor)

    # Exporta GLB final já escalado
    export_glb(args.output)

if __name__ == "__main__":
    main()
