import math
import bpy

PROMPT = "Create a sci‑fi room with futuristic design, neon lighting, metallic surfaces and high‑tech details"
OUTPUT_FILE = "D:\\LunaAI\\data\\projects\\workspaces\\build-a-local\\blender\\luna_scene.blend"


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def make_material(name, color):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = color
    material.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.42
    material.node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value = color[3] * 0.35
    return material


def assign_material(obj, material):
    obj.data.materials.append(material)
    return obj


def add_cube(name, location, scale, material):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    assign_material(obj, material)
    return obj


def add_cylinder(name, location, radius, depth, material, vertices=48):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location)
    obj = bpy.context.object
    obj.name = name
    assign_material(obj, material)
    return obj


def add_cone(name, location, radius1, radius2, depth, material, vertices=48):
    bpy.ops.mesh.primitive_cone_add(vertices=vertices, radius1=radius1, radius2=radius2, depth=depth, location=location)
    obj = bpy.context.object
    obj.name = name
    assign_material(obj, material)
    return obj


def add_sphere(name, location, radius, material):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=radius, location=location)
    obj = bpy.context.object
    obj.name = name
    assign_material(obj, material)
    return obj


def create_rocket(materials):
    body = add_cylinder("Rocket body", (0, 0, 1.8), 0.55, 3.6, materials["silver"])
    body.rotation_euler[0] = 0
    nose = add_cone("Rocket nose", (0, 0, 3.85), 0.58, 0.02, 1.1, materials["white"])
    flame = add_cone("Engine flame", (0, 0, -0.45), 0.55, 0.08, 1.1, materials["orange"])
    flame.rotation_euler[0] = math.pi
    for index, angle in enumerate((0, 2.094, 4.188)):
        fin = add_cube(f"Stabilizer fin {index + 1}", (math.cos(angle) * 0.58, math.sin(angle) * 0.58, 0.25), (0.08, 0.38, 0.55), materials["blue"])
        fin.rotation_euler[2] = angle
    return body


def create_car(materials):
    add_cube("Car base", (0, 0, 0.45), (1.9, 0.85, 0.28), materials["blue"])
    add_cube("Car cabin", (0.2, 0, 0.9), (0.85, 0.68, 0.42), materials["white"])
    for x in (-1.15, 1.15):
        for y in (-0.62, 0.62):
            wheel = add_cylinder("Wheel", (x, y, 0.2), 0.22, 0.18, materials["dark"], vertices=32)
            wheel.rotation_euler[1] = math.pi / 2


def create_planet(materials):
    add_sphere("Planet", (0, 0, 1.3), 1.2, materials["blue"])
    ring = add_cylinder("Planet ring", (0, 0, 1.3), 1.85, 0.04, materials["silver"], vertices=96)
    ring.scale.z = 0.05
    ring.rotation_euler[0] = math.radians(82)


def create_room(materials):
    add_cube("Floor", (0, 0, -0.05), (3.4, 3.4, 0.08), materials["dark"])
    add_cube("Back wall", (0, 1.72, 1.4), (3.4, 0.08, 1.5), materials["white"])
    add_cube("Desk", (0, 0.45, 0.45), (1.7, 0.55, 0.12), materials["blue"])
    add_cube("Monitor", (0, 0.72, 1.05), (0.8, 0.05, 0.45), materials["dark"])


def create_abstract(materials):
    add_sphere("Luna core", (0, 0, 1.25), 0.75, materials["silver"])
    for index in range(8):
        angle = index * math.tau / 8
        pillar = add_cube(f"Orbit shard {index + 1}", (math.cos(angle) * 1.45, math.sin(angle) * 1.45, 1.1), (0.08, 0.28, 0.65), materials["blue"])
        pillar.rotation_euler[2] = angle


def add_label(text, materials):
    bpy.ops.object.text_add(location=(-1.9, -1.75, 0.1), rotation=(math.radians(75), 0, 0))
    label = bpy.context.object
    label.name = "Scene label"
    label.data.body = text[:72]
    label.data.align_x = "LEFT"
    label.data.size = 0.16
    label.data.extrude = 0.01
    assign_material(label, materials["white"])


def setup_camera_and_light():
    bpy.ops.object.light_add(type="AREA", location=(0, -3.2, 5.0))
    light = bpy.context.object
    light.name = "Softbox"
    light.data.energy = 650
    light.data.size = 4
    bpy.ops.object.camera_add(location=(3.3, -5.2, 3.1), rotation=(math.radians(60), 0, math.radians(34)))
    bpy.context.scene.camera = bpy.context.object


def main():
    clear_scene()
    materials = {
        "silver": make_material("lunar silver", (0.72, 0.74, 0.78, 1)),
        "white": make_material("soft white", (0.92, 0.92, 0.88, 1)),
        "blue": make_material("xeno blue", (0.08, 0.22, 0.42, 1)),
        "orange": make_material("warm engine glow", (1.0, 0.32, 0.04, 1)),
        "dark": make_material("matte black", (0.02, 0.02, 0.025, 1)),
    }
    lower_prompt = PROMPT.lower()
    if any(word in lower_prompt for word in ("rocket", "raket", "ship", "spaceship")):
        create_rocket(materials)
    elif any(word in lower_prompt for word in ("car", "auto", "vehicle")):
        create_car(materials)
    elif any(word in lower_prompt for word in ("planet", "planeta", "moon", "mesic")):
        create_planet(materials)
    elif any(word in lower_prompt for word in ("room", "mistnost", "workspace", "studio")):
        create_room(materials)
    else:
        create_abstract(materials)
    add_label(PROMPT, materials)
    setup_camera_and_light()
    bpy.ops.wm.save_as_mainfile(filepath=OUTPUT_FILE)


main()
