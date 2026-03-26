import json
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


def vector_to_list(vector):
    return [round(float(vector.x), 6), round(float(vector.y), 6), round(float(vector.z), 6)]


def bbox_from_points(points):
    if not points:
        return [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]
    xs = [point.x for point in points]
    ys = [point.y for point in points]
    zs = [point.z for point in points]
    return [min(xs), min(ys), min(zs)], [max(xs), max(ys), max(zs)]


def centroid_from_points(points):
    if not points:
        return [0.0, 0.0, 0.0]
    acc = Vector((0.0, 0.0, 0.0))
    for point in points:
        acc += point
    acc /= len(points)
    return vector_to_list(acc)


def world_bbox_from_object(obj):
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    bbox_min, bbox_max = bbox_from_points(points)
    center = Vector(
        (
            (bbox_min[0] + bbox_max[0]) / 2.0,
            (bbox_min[1] + bbox_max[1]) / 2.0,
            (bbox_min[2] + bbox_max[2]) / 2.0,
        )
    )
    return bbox_min, bbox_max, vector_to_list(center)


def collect_selected_face_regions():
    regions = []
    for obj in bpy.context.selected_objects:
        if obj.type != "MESH" or obj.mode != "EDIT":
            continue

        bm = bmesh.from_edit_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        selected_faces = [face for face in bm.faces if face.select]
        if not selected_faces:
            continue

        all_points = []
        total_area = 0.0
        normal_sum = Vector((0.0, 0.0, 0.0))
        material_names = set()
        for face in selected_faces:
            world_points = [obj.matrix_world @ vert.co for vert in face.verts]
            all_points.extend(world_points)
            total_area += face.calc_area()
            normal_sum += obj.matrix_world.to_3x3() @ face.normal
            if obj.material_slots and 0 <= face.material_index < len(obj.material_slots):
                slot = obj.material_slots[face.material_index]
                if slot and slot.material:
                    material_names.add(slot.material.name)

        bbox_min, bbox_max = bbox_from_points(all_points)
        avg_normal = normal_sum.normalized() if normal_sum.length > 0 else Vector((0.0, 0.0, 1.0))
        regions.append(
            {
                "object_name": obj.name,
                "face_indices": [face.index for face in selected_faces],
                "face_count": len(selected_faces),
                "total_area": round(float(total_area), 6),
                "centroid": centroid_from_points(all_points),
                "bbox_min": [round(value, 6) for value in bbox_min],
                "bbox_max": [round(value, 6) for value in bbox_max],
                "average_normal": vector_to_list(avg_normal),
                "materials": sorted(material_names),
            }
        )
    return regions


def collect_selected_object_regions():
    regions = []
    for obj in bpy.context.selected_objects:
        if obj.type != "MESH":
            continue
        bbox_min, bbox_max, centroid = world_bbox_from_object(obj)
        regions.append(
            {
                "object_name": obj.name,
                "bbox_min": [round(value, 6) for value in bbox_min],
                "bbox_max": [round(value, 6) for value in bbox_max],
                "centroid": centroid,
                "polygon_count": len(obj.data.polygons),
            }
        )
    return regions


def compute_design_region_center(selected_face_regions, selected_object_regions):
    points = []
    for region in selected_face_regions:
        points.append(Vector(region["centroid"]))
    for region in selected_object_regions:
        points.append(Vector(region["centroid"]))
    if not points:
        return Vector((0.0, 0.0, 0.0))
    acc = Vector((0.0, 0.0, 0.0))
    for point in points:
        acc += point
    return acc / len(points)


def collect_environment_objects(design_region_center):
    selected_names = {obj.name for obj in bpy.context.selected_objects}
    results = []
    for obj in bpy.context.scene.objects:
        if obj.name in selected_names or obj.type != "MESH":
            continue
        bbox_min, bbox_max, centroid = world_bbox_from_object(obj)
        center_vector = Vector(centroid)
        distance = (center_vector - design_region_center).length
        results.append(
            {
                "object_name": obj.name,
                "bbox_min": [round(value, 6) for value in bbox_min],
                "bbox_max": [round(value, 6) for value in bbox_max],
                "centroid": centroid,
                "distance_to_design_region": round(float(distance), 6),
                "polygon_count": len(obj.data.polygons),
            }
        )
    return results


def resolve_output_path():
    if "--" in sys.argv:
        extra_args = sys.argv[sys.argv.index("--") + 1 :]
        if extra_args:
            return Path(extra_args[0])
    return Path.cwd() / "geometry_context.json"


def main():
    output_path = resolve_output_path()
    selected_face_regions = collect_selected_face_regions()
    selected_object_regions = collect_selected_object_regions()
    design_region_center = compute_design_region_center(selected_face_regions, selected_object_regions)
    environment_objects = collect_environment_objects(design_region_center)

    notes = []
    if not selected_face_regions and not selected_object_regions:
        notes.append("No selected mesh faces or objects were found.")
    if bpy.context.mode != "EDIT_MESH":
        notes.append("Current context is not EDIT_MESH. Face selection may be incomplete; object selection was also recorded.")

    payload = {
        "scene_name": bpy.context.scene.name,
        "active_object": bpy.context.active_object.name if bpy.context.active_object else None,
        "context_mode": bpy.context.mode,
        "selected_face_regions": selected_face_regions,
        "selected_object_regions": selected_object_regions,
        "design_region_center": vector_to_list(design_region_center),
        "environment_objects": sorted(environment_objects, key=lambda item: item["distance_to_design_region"]),
        "notes": notes,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Geometry context exported to: {output_path}")
    print(f"Selected face regions: {len(selected_face_regions)}")
    print(f"Selected object regions: {len(selected_object_regions)}")
    print(f"Environment objects: {len(environment_objects)}")


main()
