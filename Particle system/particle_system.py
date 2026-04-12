bl_info = {
    "name": "UPBGE Particle System",
    "author": "Ghost DEV",
    "version": (0, 8, 1),
    "blender": (5, 0, 0),
    "location": "Properties > Physics Properties",
    "description": "Addon creates a realtime particle system for UPBGE",
    "warning": "This beta version sill under development and is not stable at all times",
    "wiki_url": "",
    "category": "Physics",
}

import bpy
import bmesh
import math
import time
from mathutils import Vector, Matrix
import random

# Wire shape visualization
def update_wire_shape(self, context):
    """Update wire shape visualization - reuses meshes, just hides/shows them"""
    obj = context.object
    if not obj:
        return

    ps = obj.particle_system_props

    # Wire names for each shape type
    wire_box_name        = f"PS_Wire_Box_{obj.name}"
    wire_sphere_name     = f"PS_Wire_Sphere_{obj.name}"
    wire_hemisphere_name = f"PS_Wire_Hemisphere_{obj.name}"
    wire_cone_name       = f"PS_Wire_Cone_{obj.name}"
    wire_ring_name       = f"PS_Wire_Ring_{obj.name}"

    # Get existing wires
    wire_box        = bpy.data.objects.get(wire_box_name)
    wire_sphere     = bpy.data.objects.get(wire_sphere_name)
    wire_hemisphere = bpy.data.objects.get(wire_hemisphere_name)
    wire_cone       = bpy.data.objects.get(wire_cone_name)
    wire_ring       = bpy.data.objects.get(wire_ring_name)

    all_wires = (wire_box, wire_sphere, wire_hemisphere, wire_cone, wire_ring)

    # If disabled or POINT shape, hide all wires
    if not ps.enabled or ps.emission_shape == 'POINT':
        for w in all_wires:
            if w:
                w.hide_viewport = True
                w.hide_render   = True
        update_game_prop(self, context)
        return

    # Create wires if they don't exist yet
    if not wire_box:
        wire_box = create_box_wire(obj, wire_box_name)
    if not wire_sphere:
        wire_sphere = create_sphere_wire(obj, wire_sphere_name)
    if not wire_hemisphere:
        wire_hemisphere = create_hemisphere_wire(obj, wire_hemisphere_name)
    if not wire_cone:
        wire_cone = create_cone_wire(obj, wire_cone_name)
    if not wire_ring:
        wire_ring = create_ring_wire(obj, wire_ring_name)

    all_wires = (wire_box, wire_sphere, wire_hemisphere, wire_cone, wire_ring)

    # Helper: hide all then show only the active wire
    def _hide_all():
        for w in all_wires:
            w.hide_viewport = True
            w.hide_render   = True

    # Show/hide based on current shape — parent/location set permanently at creation
    if ps.emission_shape == 'BOX':
        _hide_all()
        wire_box.scale         = ps.emission_box_size
        wire_box.hide_viewport = False
        wire_box.hide_render   = True

    elif ps.emission_shape == 'SPHERE':
        _hide_all()
        r = ps.emission_sphere_radius
        wire_sphere.scale         = (r, r, r)
        wire_sphere.hide_viewport = False
        wire_sphere.hide_render   = True

    elif ps.emission_shape == 'HEMISPHERE':
        _hide_all()
        r = ps.emission_hemisphere_radius
        wire_hemisphere.scale         = (r, r, r)
        wire_hemisphere.hide_viewport = False
        wire_hemisphere.hide_render   = True

    elif ps.emission_shape == 'CONE':
        _hide_all()
        cr = ps.emission_cone_radius
        ch = ps.emission_cone_height
        br = ps.emission_cone_base_radius
        # Rebuild mesh to reflect current base_radius ring
        update_cone_wire_base(wire_cone, cr, br, ch)
        wire_cone.scale         = (cr, cr, ch)
        wire_cone.hide_viewport = False
        wire_cone.hide_render   = True

    elif ps.emission_shape == 'RING':
        _hide_all()
        r = ps.emission_ring_radius
        wire_ring.scale         = (r, r, 1.0)
        wire_ring.hide_viewport = False
        wire_ring.hide_render   = True

    update_game_prop(self, context)

def _make_wire_obj(obj, wire_name, shape_type):
    """Shared setup for all wire objects: link, parent, display flags.
    Called once at creation; parent/location are permanent after this."""
    mesh = bpy.data.meshes.new(f"PS_WireMesh_{shape_type}_{obj.name}")
    w = bpy.data.objects.new(wire_name, mesh)
    w['ps_shape_type'] = shape_type
    bpy.context.collection.objects.link(w)
    w.parent = obj
    w.matrix_parent_inverse = obj.matrix_world.__class__()
    w.location       = (0, 0, 0)
    w.rotation_euler = (0, 0, 0)
    w.display_type   = 'WIRE'
    w.show_in_front  = True
    w.hide_render    = True
    w.hide_select    = True
    w.hide_viewport  = True
    w.color          = (0, 1, 1, 1)
    try:
        w.game.physics_type = 'NO_COLLISION'
    except AttributeError:
        pass  # Not available in non-UPBGE / standard Blender
    return w

def create_box_wire(obj, wire_name):
    """Unit box wire (±0.5 per axis). Scale=(box_size_x,y,z) at show time."""
    w = _make_wire_obj(obj, wire_name, 'BOX')
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in (
        (-0.5,-0.5,-0.5),(0.5,-0.5,-0.5),(0.5,0.5,-0.5),(-0.5,0.5,-0.5),
        (-0.5,-0.5, 0.5),(0.5,-0.5, 0.5),(0.5,0.5, 0.5),(-0.5,0.5, 0.5),
    )]
    for a, b in ((0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)):
        bm.edges.new((vs[a], vs[b]))
    bm.to_mesh(w.data); bm.free()
    return w

def create_sphere_wire(obj, wire_name):
    """Three great-circle wire (XY, XZ, YZ). Scale=(r,r,r) at show time."""
    w = _make_wire_obj(obj, wire_name, 'SPHERE')
    bm = bmesh.new()
    seg = 32; tau = 2.0 * math.pi
    for plane in ('xy', 'xz', 'yz'):
        vs = []
        for i in range(seg):
            a = tau * i / seg; c, s = math.cos(a), math.sin(a)
            vs.append(bm.verts.new((c,s,0) if plane=='xy' else (c,0,s) if plane=='xz' else (0,c,s)))
        for i in range(seg):
            bm.edges.new((vs[i], vs[(i+1) % seg]))
    bm.to_mesh(w.data); bm.free()
    return w

def create_hemisphere_wire(obj, wire_name):
    """Hemisphere wire: equator ring (XY) + two upper half great-circles (XZ, YZ). Scale=(r,r,r)."""
    w = _make_wire_obj(obj, wire_name, 'HEMISPHERE')
    bm = bmesh.new(); seg = 32; tau = 2.0 * math.pi; half = seg // 2
    # Full equator ring in XY plane
    eq = [bm.verts.new((math.cos(tau*i/seg), math.sin(tau*i/seg), 0.0)) for i in range(seg)]
    for i in range(seg):
        bm.edges.new((eq[i], eq[(i+1) % seg]))
    # Upper half of XZ great circle (Z >= 0: i from 0 to half inclusive)
    xz = [bm.verts.new((math.cos(math.pi*i/half), 0.0, math.sin(math.pi*i/half))) for i in range(half+1)]
    for i in range(half):
        bm.edges.new((xz[i], xz[i+1]))
    # Upper half of YZ great circle
    yz = [bm.verts.new((0.0, math.cos(math.pi*i/half), math.sin(math.pi*i/half))) for i in range(half+1)]
    for i in range(half):
        bm.edges.new((yz[i], yz[i+1]))
    bm.to_mesh(w.data); bm.free()
    return w

def create_cone_wire(obj, wire_name):
    """Cone wire: bottom ring at Z=0 (scaled by base_radius/cone_radius), top ring at Z=+1.
    4 struts connect matching points on both rings.
    Scale=(cone_radius, cone_radius, cone_height) at show time.
    Mesh is rebuilt by update_cone_wire_base() whenever dimensions change."""
    w = _make_wire_obj(obj, wire_name, 'CONE')
    # Build with base_ratio=0 initially (point tip) — will be rebuilt on first show
    _build_cone_wire_mesh(w.data, base_ratio=0.0)
    return w

def _build_cone_wire_mesh(mesh, base_ratio):
    """Write cone wire geometry into mesh.
    base_ratio = base_radius / cone_radius (local space).
    base_ratio == 0  → single tip vertex at origin (classic sharp cone).
    base_ratio  > 0  → circle at Z=0 with that ratio, connected to top ring."""
    seg = 32; tau = 2.0 * math.pi
    bm = bmesh.new()

    # Top ring at Z=+1 (the wide opening, which is the inverted head in the viewport)
    top = [bm.verts.new((math.cos(tau*i/seg), math.sin(tau*i/seg), 1.0)) for i in range(seg)]
    for i in range(seg):
        bm.edges.new((top[i], top[(i+1) % seg]))

    if base_ratio > 0.0:
        # Bottom ring at Z=0 — radius = base_ratio in local space
        bot = [bm.verts.new((base_ratio*math.cos(tau*i/seg),
                              base_ratio*math.sin(tau*i/seg), 0.0)) for i in range(seg)]
        for i in range(seg):
            bm.edges.new((bot[i], bot[(i+1) % seg]))
        # 4 struts at 0°, 90°, 180°, 270°
        for i in range(0, seg, seg // 4):
            bm.edges.new((bot[i], top[i]))
    else:
        # Classic sharp tip at origin
        tip = bm.verts.new((0.0, 0.0, 0.0))
        for i in range(0, seg, seg // 4):
            bm.edges.new((tip, top[i]))

    bm.to_mesh(mesh)
    bm.free()

def update_cone_wire_base(wire_cone, cone_radius, cone_base_radius, cone_height):
    """Rebuild the cone wire mesh to reflect the current base_radius.
    Called from update_wire_shape whenever cone dimensions change."""
    if wire_cone is None:
        return
    ratio = (cone_base_radius / cone_radius) if cone_radius > 0.0 and cone_base_radius > 0.0 else 0.0
    _build_cone_wire_mesh(wire_cone.data, base_ratio=ratio)

def create_ring_wire(obj, wire_name):
    """Unit circle in XY plane. Scale=(ring_radius,ring_radius,1) at show time."""
    w = _make_wire_obj(obj, wire_name, 'RING')
    bm = bmesh.new(); seg = 32; tau = 2.0 * math.pi
    vs = [bm.verts.new((math.cos(tau*i/seg), math.sin(tau*i/seg), 0.0)) for i in range(seg)]
    for i in range(seg):
        bm.edges.new((vs[i], vs[(i+1) % seg]))
    bm.to_mesh(w.data); bm.free()
    return w

_PROPS_MAP = (
    ('enabled',                    'ps_enabled'),
    ('trigger_enabled',                    'ps_trigger'),
    ('emission_mode',                    'ps_emission_mode'),
    ('emission_shape',                    'ps_emission_shape'),
    ('emission_sphere_radius',                    'ps_emission_sphere_radius'),
    ('emission_hemisphere_radius',                'ps_emission_hemisphere_radius'),
    ('emission_cone_radius',                      'ps_emission_cone_radius'),
    ('emission_cone_height',                      'ps_emission_cone_height'),
    ('emission_cone_base_radius',                 'ps_emission_cone_base_radius'),
    ('emit_from',                                 'ps_emit_from'),
    ('emission_ring_radius',                    'ps_emission_ring_radius'),
    ('emission_ring_width',                    'ps_emission_ring_width'),
    ('max_particles',                    'ps_max_particles'),
    ('emission_rate',                    'ps_emission_rate'),
    ('emission_delay',                    'ps_emission_delay'),
    ('burst_count',                    'ps_burst_count'),
    ('is_one_shot',                    'ps_is_one_shot'),
    ('lifetime',                    'ps_lifetime'),
    ('lifetime_random',                    'ps_lifetime_random'),
    ('start_size',                    'ps_start_size'),
    ('end_size',                    'ps_end_size'),
    ('velocity_random',                    'ps_velocity_random'),
    ('simulation_space',                    'ps_simulation_space'),
    ('parent_with_emitter',                 'ps_parent_with_emitter'),
    ('movement_type',                    'ps_movement_type'),
    ('drag_enabled',                    'ps_drag_enabled'),
    ('drag_start',                    'ps_drag_start'),
    ('drag_end',                    'ps_drag_end'),
    ('resistance_strength',                    'ps_resistance'),
    ('billboard_roll_enabled',                    'ps_bb_roll_enabled'),
    ('billboard_roll_speed',                      'ps_bb_roll_speed'),
    ('billboard_roll_random',                     'ps_bb_roll_random'),
    ('billboard_facing',                          'ps_bb_facing'),
    ('enable_gravity',                    'ps_enable_gravity'),
    ('gravity_power',                    'ps_gravity_power'),
    ('enable_collision',                    'ps_enable_collision'),
    ('bounce_strength',                    'ps_bounce_strength'),
    ('stop_on_collision',                  'ps_stop_on_collision'),
    ('particle_type',                    'ps_particle_type'),
    ('start_alpha',                    'ps_start_alpha'),
    ('end_alpha',                    'ps_end_alpha'),
    ('alpha_start_time',                    'ps_alpha_start_time'),
    ('alpha_end_time',                    'ps_alpha_end_time'),
    ('color_start_time',                    'ps_color_start_time'),
    ('color_end_time',                    'ps_color_end_time'),
    ('enable_color',                    'ps_enable_color'),
    ('enable_alpha',                    'ps_enable_alpha'),
    ('enable_turbulence',                    'ps_enable_turb'),
    ('turbulence_strength',                    'ps_turb_strength'),
    ('turbulence_frequency',                    'ps_turb_frequency'),
    ('turbulence_speed',                    'ps_turb_speed'),
    ('enable_lod',                    'ps_enable_lod'),
    ('lod_start_distance',                    'ps_lod_start'),
    ('lod1_distance',                    'ps_lod1_dist'),
    ('lod1_max_particles',                    'ps_lod1_max'),
    ('lod1_emission_rate',                    'ps_lod1_rate'),
    ('lod1_burst_count',                    'ps_lod1_burst'),
    ('lod1_disable_turbulence',                    'ps_lod1_no_turb'),
    ('lod1_disable_collision',                    'ps_lod1_no_coll'),
    ('lod1_disable_emitting',                    'ps_lod1_no_emit'),
    ('lod1_destroy_particles',                    'ps_lod1_destroy'),
    ('lod2_distance',                    'ps_lod2_dist'),
    ('lod2_max_particles',                    'ps_lod2_max'),
    ('lod2_emission_rate',                    'ps_lod2_rate'),
    ('lod2_burst_count',                    'ps_lod2_burst'),
    ('lod2_disable_turbulence',                    'ps_lod2_no_turb'),
    ('lod2_disable_collision',                    'ps_lod2_no_coll'),
    ('lod2_disable_emitting',                    'ps_lod2_no_emit'),
    ('lod2_destroy_particles',                    'ps_lod2_destroy'),
    ('lod3_distance',                    'ps_lod3_dist'),
    ('lod3_max_particles',                    'ps_lod3_max'),
    ('lod3_emission_rate',                    'ps_lod3_rate'),
    ('lod3_burst_count',                    'ps_lod3_burst'),
    ('lod3_disable_turbulence',                    'ps_lod3_no_turb'),
    ('lod3_disable_collision',                    'ps_lod3_no_coll'),
    ('lod3_disable_emitting',                    'ps_lod3_no_emit'),
    ('lod3_destroy_particles',                    'ps_lod3_destroy'),
    ('enable_launcher',                    'ps_launcher_enabled'),
    ('launcher_distance',                    'ps_launcher_dist'),
    ('launcher_prewarm_distance',                    'ps_launcher_prewarm'),
    # Orbit
    ('orbit_center',                    'ps_orbit_center'),
    ('orbit_axis_x',                    'ps_orbit_axis_x'),
    ('orbit_axis_y',                    'ps_orbit_axis_y'),
    ('orbit_axis_z',                    'ps_orbit_axis_z'),
    ('orbit_axis_inverse',                    'ps_orbit_axis_inverse'),
    ('orbit_speed',                    'ps_orbit_speed'),
    ('orbit_speed_random',                    'ps_orbit_speed_random'),
    ('orbit_radius',                    'ps_orbit_radius'),
    ('orbit_radius_random',                    'ps_orbit_radius_random'),
    ('orbit_tilt',                    'ps_orbit_tilt'),
    # LOD level count — gates how many LOD entries the runtime respects
    ('lod_levels',                    'ps_lod_levels'),
    # Color/Alpha/Size mode flags
    ('color_mode',                    'ps_color_mode'),
    ('alpha_mode',                    'ps_alpha_mode'),
    ('size_mode',                     'ps_size_mode'),
    # Sub-Emitter
    ('enable_sub_emitter',                    'ps_sub_emitter_enabled'),
    ('sub_emitter_inherit_velocity',           'ps_sub_emitter_inherit_vel'),
    ('enable_sub_emitter_birth',               'ps_sub_birth_enabled'),
    ('sub_emitter_birth_inherit_velocity',     'ps_sub_birth_inherit_vel'),
    ('enable_sub_emitter_collision',           'ps_sub_coll_enabled'),
    ('sub_emitter_collision_inherit_velocity', 'ps_sub_coll_inherit_vel'),
)

def update_game_prop(self, context):
    obj = context.object
    if not obj: return

    gp = obj.game.properties   # local alias — avoids 32+ repeated attr lookups
    for addon_prop, game_prop in _PROPS_MAP:
        if game_prop in gp:
            gp[game_prop].value = getattr(self, addon_prop)

    # Vectors and compound props (per-component)
    if 'ps_start_velocity_x' in gp:
        gp['ps_start_velocity_x'].value = self.start_velocity[0]
        gp['ps_start_velocity_y'].value = self.start_velocity[1]
        gp['ps_start_velocity_z'].value = self.start_velocity[2]

    if 'ps_rotation_x' in gp:
        gp['ps_rotation_x'].value = self.rotation[0]
        gp['ps_rotation_y'].value = self.rotation[1]
        gp['ps_rotation_z'].value = self.rotation[2]

    if 'ps_force_x' in gp:
        gp['ps_force_x'].value = self.force[0]
        gp['ps_force_y'].value = self.force[1]
        gp['ps_force_z'].value = self.force[2]

    if 'ps_torque_x' in gp:
        gp['ps_torque_x'].value = self.torque[0]
        gp['ps_torque_y'].value = self.torque[1]
        gp['ps_torque_z'].value = self.torque[2]

    if 'ps_emission_box_size_x' in gp:
        gp['ps_emission_box_size_x'].value = self.emission_box_size[0]
        gp['ps_emission_box_size_y'].value = self.emission_box_size[1]
        gp['ps_emission_box_size_z'].value = self.emission_box_size[2]

    if 'ps_particle_mesh' in gp:
        gp['ps_particle_mesh'].value = self.particle_mesh.name if self.particle_mesh else 'ParticleSphere'

    if 'ps_sub_emitter' in gp:
        gp['ps_sub_emitter'].value = self.sub_emitter_object.name if self.sub_emitter_object else ' '

    if 'ps_sub_birth' in gp:
        gp['ps_sub_birth'].value = self.sub_emitter_birth_object.name if self.sub_emitter_birth_object else ' '

    if 'ps_sub_coll' in gp:
        gp['ps_sub_coll'].value = self.sub_emitter_collision_object.name if self.sub_emitter_collision_object else ' '

    if 'ps_color_start_r' in gp:
        gp['ps_color_start_r'].value = self.color_start[0]
        gp['ps_color_start_g'].value = self.color_start[1]
        gp['ps_color_start_b'].value = self.color_start[2]

    if 'ps_color_end_r' in gp:
        gp['ps_color_end_r'].value = self.color_end[0]
        gp['ps_color_end_g'].value = self.color_end[1]
        gp['ps_color_end_b'].value = self.color_end[2]

# ── Color Curve Helper ──────────────────────────────────────────────────────
# Curve node lives inside a hidden material — the only safe home for
# ShaderNodeRGBCurve in Blender 5 (node groups crash at the C level).
# The material is never assigned to any mesh; use_fake_user keeps it in the file.
CURVE_MAT_PREFIX = "PS_CurveMat_"

# ── Shared curve infrastructure ─────────────────────────────────────────────
# All curve nodes live in one hidden material per emitter (node groups crash
# Blender 5 at the C level). Each node is distinguished by node.label.

def _get_curve_node(obj_name, label):
    """Return the labeled ShaderNodeRGBCurve, or None. Read-only — safe in draw()."""
    mat = bpy.data.materials.get(CURVE_MAT_PREFIX + obj_name)
    if mat is None or not mat.use_nodes:
        return None
    for node in mat.node_tree.nodes:
        if node.bl_idname == 'ShaderNodeRGBCurve' and node.label == label:
            return node
    return None

def _ensure_curve_mat(obj):
    mat_name = CURVE_MAT_PREFIX + obj.name
    mat = bpy.data.materials.get(mat_name)
    if mat is None:
        mat = bpy.data.materials.new(name=mat_name)
    mat.use_fake_user = True
    mat.use_nodes     = True
    return mat

def _make_curve_node(mat, label):
    """Create a ShaderNodeRGBCurve with default diagonal and AUTO_CLAMPED handles."""
    node       = mat.node_tree.nodes.new('ShaderNodeRGBCurve')
    node.label = label
    mapping    = node.mapping
    mapping.use_clip   = True
    mapping.clip_min_x = 0.0; mapping.clip_max_x = 1.0
    mapping.clip_min_y = 0.0; mapping.clip_max_y = 1.0
    for curve in mapping.curves:
        curve.points[0].location    = (0.0, 0.0)
        curve.points[0].handle_type = 'AUTO_CLAMPED'
        curve.points[1].location    = (1.0, 1.0)
        curve.points[1].handle_type = 'AUTO_CLAMPED'
    mapping.update()
    return node

def _sample_curve_node(node, n=16):
    """Sample curves[3] (combined C) at n evenly-spaced points. Identity on error."""
    identity = [i / (n - 1) for i in range(n)]
    if node is None:
        return identity
    try:
        mapping = node.mapping
        curve   = mapping.curves[3]
        return [mapping.evaluate(curve, i / (n - 1)) for i in range(n)]
    except Exception:
        return identity

# ── Public accessors ─────────────────────────────────────────────────────────
def get_color_curve_node(obj_name): return _get_curve_node(obj_name, 'ColorCurve')
def get_alpha_curve_node(obj_name): return _get_curve_node(obj_name, 'AlphaCurve')
def get_size_curve_node(obj_name):  return _get_curve_node(obj_name, 'SizeCurve')

def sample_color_curve(obj_name, n=16): return _sample_curve_node(get_color_curve_node(obj_name), n)
def sample_alpha_curve(obj_name, n=64): return _sample_curve_node(get_alpha_curve_node(obj_name), n)
def sample_size_curve(obj_name, n=16):  return _sample_curve_node(get_size_curve_node(obj_name), n)

# ── Init operators ───────────────────────────────────────────────────────────
def _make_init_operator(bl_idname, bl_label, label_key):
    """Factory — returns an init operator class for the given curve label."""
    class Op(bpy.types.Operator):
        bl_options = {'REGISTER', 'UNDO'}
        def execute(self, context):
            obj = context.active_object
            if not obj:
                self.report({'ERROR'}, "No active object")
                return {'CANCELLED'}
            mat = _ensure_curve_mat(obj)
            if _get_curve_node(obj.name, label_key) is None:
                _make_curve_node(mat, label_key)
                self.report({'INFO'}, f"{label_key} initialized")
            else:
                self.report({'INFO'}, f"{label_key} already exists")
            return {'FINISHED'}
    Op.__name__    = bl_idname.replace('.', '_').replace('particle_', 'PARTICLE_OT_')
    Op.bl_idname   = bl_idname
    Op.bl_label    = bl_label
    return Op

PARTICLE_OT_init_color_curve = _make_init_operator(
    "particle.init_color_curve", "Initialize Color Curve", "ColorCurve")
PARTICLE_OT_init_alpha_curve = _make_init_operator(
    "particle.init_alpha_curve", "Initialize Alpha Curve", "AlphaCurve")
PARTICLE_OT_init_size_curve  = _make_init_operator(
    "particle.init_size_curve",  "Initialize Size Curve",  "SizeCurve")

# Particle System Properties
class ParticleSystemProperties(bpy.types.PropertyGroup):
    enabled: bpy.props.BoolProperty(
        name="Enable Particles",
        description="Master switch for the system",
        default=False,
        update=update_wire_shape
    )

    trigger_enabled: bpy.props.BoolProperty(
        name="Trigger",
        description=" Activate and Control emission via Logic Bricks",
        default=False,
        update=update_game_prop
    )

    emission_mode: bpy.props.EnumProperty(
        name="Emission Mode",
        items=[('CONTINUOUS', "Continuous", ""), ('BURST', "Burst", "")],
        default='CONTINUOUS',
        update=update_game_prop
    )

    # Emission Shape
    emission_shape: bpy.props.EnumProperty(
        name="Emission Shape",
        description="Shape from which particles are emitted",
        items=[
            ('POINT',      "Point",      "Emit from center point"),
            ('BOX',        "Box",        "Emit from random points within a box volume"),
            ('SPHERE',     "Sphere",     "Emit from random points within a sphere volume"),
            ('HEMISPHERE', "Hemisphere", "Emit from random points within the upper half-sphere (+Z)"),
            ('CONE',       "Cone",       "Emit from random points within a cone volume — tip at emitter, opening upward"),
            ('RING',       "Ring",       "Emit from a flat ring around the emitter"),
        ],
        default='POINT',
        update=update_wire_shape
    )

    emission_box_size: bpy.props.FloatVectorProperty(
        name="Box Size",
        description="Size of the emission box (X, Y, Z)",
        default=(1.0, 1.0, 1.0),
        min=0.01,
        size=3,
        update=update_wire_shape
    )

    emission_sphere_radius: bpy.props.FloatProperty(
        name="Sphere Radius",
        description="Radius of the emission sphere",
        default=1.0,
        min=0.01,
        max=100.0,
        update=update_wire_shape
    )
    emission_hemisphere_radius: bpy.props.FloatProperty(
        name="Hemisphere Radius",
        description="Radius of the emission hemisphere",
        default=1.0,
        min=0.01,
        max=100.0,
        update=update_wire_shape
    )
    emission_cone_radius: bpy.props.FloatProperty(
        name="Cone Radius",
        description="Radius of the cone base",
        default=1.0,
        min=0.01,
        max=100.0,
        update=update_wire_shape
    )
    emission_cone_height: bpy.props.FloatProperty(
        name="Cone Height",
        description="Height of the cone",
        default=2.0,
        min=0.01,
        max=100.0,
        update=update_wire_shape
    )
    emission_cone_base_radius: bpy.props.FloatProperty(
        name="Base Radius",
        description="Radius of the opening at the top of the cone (the wide inverted end). "
                    "When Emit From is set to Base, particles spawn from this disk",
        default=0.0,
        min=0.0,
        max=100.0,
        update=update_wire_shape
    )
    emission_ring_radius: bpy.props.FloatProperty(
        name="Ring Radius",
        description="Distance from center to the ring",
        default=1.0,
        min=0.01,
        max=100.0,
        update=update_wire_shape
    )
    emission_ring_width: bpy.props.FloatProperty(
        name="Ring Width",
        description="Radial thickness of the ring (0 = infinitely thin)",
        default=0.1,
        min=0.0,
        max=100.0,
        update=update_wire_shape
    )

    emit_from: bpy.props.EnumProperty(
        name="Emit From",
        description="Where within the emission shape particles spawn",
        items=[
            ('VOLUME',  "Volume",  "Spawn at random positions throughout the full interior volume"),
            ('SURFACE', "Surface", "Spawn only on the outer surface of the shape"),
            ('BASE',    "Base",    "Spawn only on the base disk of the cone (cone shape only)"),
        ],
        default='VOLUME',
        update=update_game_prop
    )

    max_particles: bpy.props.IntProperty(name="Max Particles", default=100, min=1, max=5000, update=update_game_prop)
    emission_rate: bpy.props.FloatProperty(name="Emission Rate", default=10.0, min=0.0, max=1000, update=update_game_prop)

    # NEW: Delay for Burst Mode
    emission_delay: bpy.props.FloatProperty(name="Burst Delay", description="Time between bursts (seconds)", default=1.0, min=0.1, max=100.0, update=update_game_prop)

    burst_count: bpy.props.IntProperty(name="Burst Count", default=30, min=1, max=1500, update=update_game_prop)
    is_one_shot: bpy.props.BoolProperty(name="One Shot", description="Fire once when triggered, reset when trigger stops", default=False, update=update_game_prop)

    lifetime: bpy.props.FloatProperty(name="Lifetime", default=3.0, min=0.1, max=100.0, update=update_game_prop)
    lifetime_random: bpy.props.FloatProperty(name="Random Lifetime", default=0.5, min=0.0, max=1.0, update=update_game_prop)
    start_size: bpy.props.FloatProperty(name="Start Size", default=0.1, min=0.001, max=50.0, update=update_game_prop)
    end_size: bpy.props.FloatProperty(name="End Size", default=0.05, min=0.001, max=50.0, update=update_game_prop)

    size_mode: bpy.props.EnumProperty(
        name="Size Mode",
        description="How size transitions over particle lifetime",
        items=[
            ('SIMPLE', "Simple", "Linear interpolation from Start to End size"),
            ('CURVE',  "Curve",  "Size shaped by a custom curve — hit Apply Material to bake"),
        ],
        default='SIMPLE',
    )

    start_velocity: bpy.props.FloatVectorProperty(name="Start Velocity", default=(0.0, 0.0, 2.0), size=3, update=update_game_prop)
    velocity_random: bpy.props.FloatProperty(name="Random Velocity", default=0.5, min=0.0, max=10.0, update=update_game_prop)
    enable_gravity: bpy.props.BoolProperty(
        name="Enable Gravity",
        description="Enable gravity along the Z axis",
        default=False,
        update=update_game_prop
    )
    gravity_power: bpy.props.FloatProperty(
        name="Gravity Power",
        description="Gravity strength on Z axis",
        default=-9.8, min=-100.0, max=100.0,
        update=update_game_prop
    )

    # Movement Type
    movement_type: bpy.props.EnumProperty(
        name="Movement Type",
        description="How particles move through space",
        items=[
            ('SIMPLE', "Simple",      "Direct velocity"),
            ('FORCE',  "Force-Based", "Acceleration/deceleration"),
            ('ORBIT',  "Orbit",       "Particles revolve around a center point"),
        ],
        default='SIMPLE',
        update=update_game_prop
    )

    # ── Orbit Properties ─────────────────────────────────────────────
    orbit_center: bpy.props.EnumProperty(
        name="Orbit Center",
        description="Point around which particles orbit",
        items=[
            ('EMITTER',      "Emitter",      "Revolve around the emitter's world position (baked at spawn)"),
            ('WORLD_ORIGIN', "World Origin", "Revolve around the world origin (0, 0, 0)"),
        ],
        default='EMITTER',
        update=update_game_prop
    )
    orbit_axis_x: bpy.props.BoolProperty(
        name="X", description="Include X axis in orbit plane",
        default=False, update=update_game_prop
    )
    orbit_axis_y: bpy.props.BoolProperty(
        name="Y", description="Include Y axis in orbit plane",
        default=False, update=update_game_prop
    )
    orbit_axis_z: bpy.props.BoolProperty(
        name="Z", description="Include Z axis in orbit plane",
        default=True, update=update_game_prop
    )
    orbit_axis_inverse: bpy.props.BoolProperty(
        name="Inverse", description="Reverse the orbit axis direction, flipping which way the orbit plane faces",
        default=False, update=update_game_prop
    )
    orbit_speed: bpy.props.FloatProperty(
        name="Orbit Speed",
        description="Revolutions per second (negative = reverse direction)",
        default=0.5,
        min=-20.0, max=20.0,
        update=update_game_prop
    )
    orbit_speed_random: bpy.props.FloatProperty(
        name="Speed Random",
        description="Per-particle random variance added to orbit speed",
        default=0.0,
        min=0.0, max=10.0,
        update=update_game_prop
    )
    orbit_radius: bpy.props.FloatProperty(
        name="Orbit Radius",
        description="Distance from center for POINT/CONE emission (ignored for BOX/SPHERE)",
        default=2.0,
        min=0.001, max=100.0,
        update=update_game_prop
    )
    orbit_radius_random: bpy.props.FloatProperty(
        name="Radius Random",
        description="Per-particle random variance on orbit radius",
        default=0.0,
        min=0.0, max=10.0,
        update=update_game_prop
    )
    orbit_tilt: bpy.props.FloatProperty(
        name="Tilt",
        description="Tilt the orbit plane around an axis perpendicular to the selected orbit axis (0–360°)",
        default=0.0,
        min=0.0, max=360.0,
        update=update_game_prop
    )
    # Force-Based Properties
    force: bpy.props.FloatVectorProperty(
        name="Force",
        description="Applied force (acceleration)",
        default=(0.0, 0.0, 0.0),
        size=3,
        update=update_game_prop
    )

    torque: bpy.props.FloatVectorProperty(
        name="Torque",
        description="Angular force (rotational acceleration)",
        default=(0.0, 0.0, 0.0),
        size=3,
        update=update_game_prop
    )
    billboard_roll_enabled: bpy.props.BoolProperty(
        name="Billboard Roll",
        description="Spin billboard particles around the camera-facing axis — good for smoke and soft effects",
        default=False,
        update=update_game_prop
    )
    billboard_roll_speed: bpy.props.FloatProperty(
        name="Roll Speed",
        description="Revolutions per second — negative reverses spin direction",
        default=0.3, min=-20.0, max=20.0,
        update=update_game_prop
    )
    billboard_roll_random: bpy.props.FloatProperty(
        name="Roll Random",
        description="Per-particle random variance on roll speed",
        default=0.2, min=0.0, max=10.0,
        update=update_game_prop
    )

    billboard_facing: bpy.props.EnumProperty(
        name="Rotation Method",
        description=(
            "How each billboard orients itself toward the camera.\n"
            "Camera Rotation: copies the camera's own orientation matrix — all particles "
            "share one matrix, cheapest, best for flat effects (rain, sparks).\n"
            "Look-At: each particle independently builds a 3D rotation that points its "
            "normal directly at the camera — slightly more expensive but gives correct "
            "depth layering for volumetric effects like fire and smoke"
        ),
        items=[
            ('CAM_ROT', "Camera Rotation",
             "Copy camera orientation — all particles share one matrix per frame (default)"),
            ('LOOK_AT', "Look-At",
             "Each particle faces the camera in true 3D — better for fire and volumetric effects"),
        ],
        default='CAM_ROT',
        update=update_game_prop
    )

    drag_enabled: bpy.props.BoolProperty(
        name="Drag over Lifetime",
        description="Apply air resistance that changes over the particle lifetime",
        default=False,
        update=update_game_prop
    )
    drag_start: bpy.props.FloatProperty(
        name="Start",
        description="Air resistance at birth",
        default=0.0, min=0.0, max=1.0,
        update=update_game_prop
    )
    drag_end: bpy.props.FloatProperty(
        name="End",
        description="Air resistance at death",
        default=0.5, min=0.0, max=1.0,
        update=update_game_prop
    )
    resistance_strength: bpy.props.FloatProperty(
        name="Resistance Strength",
        description="Global multiplier for all drag",
        default=1.0, min=0.0, max=10.0,
        update=update_game_prop
    )

    # Simulation Space
    simulation_space: bpy.props.EnumProperty(
        name="Simulation Space",
        description="Coordinate system for particle movement",
        items=[
            ('WORLD', "Global", "Particles use world coordinates (independent of emitter)"),
            ('LOCAL', "Local", "Particles follow emitter's local space and movement"),
        ],
        default='WORLD',
        update=update_game_prop
    )

    parent_with_emitter: bpy.props.BoolProperty(
        name="Parent with Emitter",
        description="Particles follow the emitter position and rotation as if parented, while still simulating physics freely",
        default=False,
        update=update_game_prop
    )

    # Particle Type
    particle_type: bpy.props.EnumProperty(
        name="Particle Type",
        description="How each particle is rendered",
        items=[
            ('BILLBOARD', "Billboard", "Plane that always faces the active camera"),
            ('MESH',      "Mesh",      "Use a custom mesh object as the particle"),
        ],
        default='BILLBOARD',
        update=update_game_prop
    )

    def particle_mesh_poll(self, object):
        """Only allow MESH objects as particle mesh"""
        return object.type == 'MESH'

    particle_mesh: bpy.props.PointerProperty(
        name="Particle Mesh",
        type=bpy.types.Object,
        poll=particle_mesh_poll,
        update=update_game_prop
    )

    enable_texture: bpy.props.BoolProperty(
        name="Enable Texture",
        description=(
            "Apply textures to the particle"
        ),
        default=False,
        update=update_game_prop
    )

    billboard_texture: bpy.props.PointerProperty(
        name="Texture",
        type=bpy.types.Image,
        description="Image to apply to the billboard material",
    )

    texture_render: bpy.props.EnumProperty(
        name="Texture Render",
        description=(
            "Quality of the particle material blending. "
            "High (Blended): correct transparency sorting, higher GPU cost. "
            "Low (Dithered): faster forward-render approximation, better performance"
        ),
        items=[
            ('HIGH', "High", "Blended — correct alpha transparency, higher GPU cost"),
            ('LOW',  "Low",  "Dithered — faster approximation, better performance"),
        ],
        default='HIGH',
    )

    # Collision Properties
    enable_collision: bpy.props.BoolProperty(
        name="Enable Collision",
        description="Enable particle collision with surfaces",
        default=False,
        update=update_game_prop
    )

    bounce_strength: bpy.props.FloatProperty(
        name="Bounce Strength",
        description="How much particles bounce",
        default=0.5,
        min=0.0,
        max=1.0,
        update=update_game_prop
    )

    stop_on_collision: bpy.props.BoolProperty(
        name="Stop Movement",
        description="Freeze particle in place when it hits a surface (only active when Bounce is 0)",
        default=False,
        update=update_game_prop
    )

    # Rotation Property (XYZ like velocity)
    rotation: bpy.props.FloatVectorProperty(
        name="Rotation",
        description="Rotation in degrees per lifetime",
        default=(0.0, 0.0, 0.0),
        min=-3600.0,
        max=3600.0,
        size=3,
        update=update_game_prop
    )

    # Color over lifetime
    enable_color: bpy.props.BoolProperty(
        name="Color over Lifetime",
        description="Enable color interpolation over the particle's lifetime",
        default=False,
        update=update_game_prop
    )

    # Flat base color — used when Color over Lifetime is off.
    # Baked into the material node as a plain RGB value when Apply Material is clicked.
    base_color: bpy.props.FloatVectorProperty(
        name="Color",
        description="Flat particle color baked into the material. "
                    "Only active when Color over Lifetime is disabled",
        default=(1.0, 1.0, 1.0),
        min=0.0, max=1.0,
        size=3,
        subtype='COLOR',
        update=update_base_color,
    )

    color_start: bpy.props.FloatVectorProperty(
        name="Color Start",
        description="Particle color at birth",
        default=(1.0, 1.0, 1.0),
        min=0.0, max=1.0,
        size=3,
        subtype='COLOR',
        update=update_game_prop
    )

    color_end: bpy.props.FloatVectorProperty(
        name="Color End",
        description="Particle color at death",
        default=(1.0, 0.0, 0.0),
        min=0.0, max=1.0,
        size=3,
        subtype='COLOR',
        update=update_game_prop
    )

    color_start_time: bpy.props.FloatProperty(
        name="Start Time",
        description="Lifetime ratio when color transition begins",
        default=0.0,
        min=0.0, max=10.0,
        update=update_game_prop
    )

    color_end_time: bpy.props.FloatProperty(
        name="End Time",
        description="Lifetime ratio when color transition ends",
        default=10.0,
        min=0.0, max=10.0,
        update=update_game_prop
    )

    color_mode: bpy.props.EnumProperty(
        name="Color Mode",
        description="How the color transitions over particle lifetime",
        items=[
            ('SIMPLE', "Simple", "Linear blend between Start and End, controlled by From/To"),
            ('CURVE',  "Curve",  "Blend shaped by a custom curve — hit Apply Material to bake"),
        ],
        default='SIMPLE',
    )

    # Alpha over lifetime
    enable_alpha: bpy.props.BoolProperty(
        name="Alpha over Lifetime",
        description="Enable alpha fade over the particle's lifetime",
        default=False,
        update=update_game_prop
    )

    start_alpha: bpy.props.FloatProperty(
        name="Start Alpha",
        description="Opacity at birth (1.0 = fully opaque, 0.0 = invisible)",
        default=1.0, min=0.0, max=1.0,
        update=update_game_prop
    )
    end_alpha: bpy.props.FloatProperty(
        name="End Alpha",
        description="Opacity at death (0.0 = fully transparent)",
        default=0.0, min=0.0, max=1.0,
        update=update_game_prop
    )
    alpha_start_time: bpy.props.FloatProperty(
        name="From",
        description="Lifetime ratio (0-10) when alpha transition begins",
        default=0.0, min=0.0, max=10.0,
        update=update_game_prop
    )
    alpha_end_time: bpy.props.FloatProperty(
        name="To",
        description="Lifetime ratio (0-10) when alpha transition ends",
        default=10.0, min=0.0, max=10.0,
        update=update_game_prop
    )

    alpha_mode: bpy.props.EnumProperty(
        name="Alpha Mode",
        description="How alpha transitions over particle lifetime",
        items=[
            ('SIMPLE', "Simple", "Linear fade between Start and End, controlled by From/To"),
            ('CURVE',  "Curve",  "Fade shaped by a custom curve — hit Apply Material to bake"),
        ],
        default='SIMPLE',
    )

    # Turbulence
    enable_turbulence: bpy.props.BoolProperty(
        name="Enable Turbulence",
        description="Add a continuously changing noise force that pushes particles every frame",
        default=False,
        update=update_game_prop
    )
    turbulence_strength: bpy.props.FloatProperty(
        name="Strength",
        description="How hard the noise field pushes",
        default=0.5, min=0.0, max=100.0,
        update=update_game_prop
    )
    turbulence_frequency: bpy.props.FloatProperty(
        name="Frequency",
        description="Noise field zoom",
        default=0.5, min=0.01, max=100.0,
        update=update_game_prop
    )
    turbulence_speed: bpy.props.FloatProperty(
        name="Speed",
        description="How fast the noise field evolves over time",
        default=0.5, min=0.0, max=100.0,
        update=update_game_prop
    )

    # LOD Properties
    enable_lod: bpy.props.BoolProperty(
        name="Enable LOD",
        description="Reduces simulation cost at distance",
        default=False,
        update=update_game_prop
    )

    lod_levels: bpy.props.EnumProperty(
        name="LOD Levels",
        description="How many LOD levels to use",
        items=[
            ('1', "1 Level",  "1 level of LOD"),
            ('2', "2 Levels", "2 levels of LOD"),
            ('3', "3 Levels", "3 levels of LOD"),
        ],
        default='1',
        update=update_game_prop
    )

    lod_start_distance: bpy.props.FloatProperty(
        name="Start LOD",
        description="Distance from the active camera at which LOD begins",
        default=20.0, min=0.0, max=10000.0,
        update=update_game_prop
    )

    # LOD 1
    lod1_distance: bpy.props.FloatProperty(
        name="Distance",
        description="Distance at which LOD 1 activates",
        default=40.0, min=0.0, max=10000.0,
        update=update_game_prop
    )
    lod1_max_particles: bpy.props.IntProperty(
        name="Max Particles",
        description="Maximum active particles at LOD 1",
        default=50, min=0, max=5000,
        update=update_game_prop
    )
    lod1_emission_rate: bpy.props.FloatProperty(
        name="Emission Rate",
        description="Particles per second at LOD 1 (Continuous mode)",
        default=10.0, min=0.0, max=1000.0,
        update=update_game_prop
    )
    lod1_burst_count: bpy.props.IntProperty(
        name="Burst Count",
        description="Particles per burst at LOD 1 (Burst mode)",
        default=15, min=0, max=1500,
        update=update_game_prop
    )
    lod1_disable_turbulence: bpy.props.BoolProperty(
        name="Disable Turbulence",
        description="Disable turbulence at LOD Level 1 to save per-particle noise calculations",
        default=False, update=update_game_prop
    )
    lod1_disable_collision: bpy.props.BoolProperty(
        name="Disable Collision",
        default=False, update=update_game_prop
    )
    lod1_disable_emitting: bpy.props.BoolProperty(
        name="Disable Emitting",
        default=False, update=update_game_prop
    )
    lod1_destroy_particles: bpy.props.BoolProperty(
        name="Destroy Particles",
        description="Return all active particles to the pool immediately when this LOD activates",
        default=False, update=update_game_prop
    )

    # LOD 2
    lod2_distance: bpy.props.FloatProperty(
        name="Distance",
        description="Distance at which LOD 2 activates",
        default=80.0, min=0.0, max=10000.0,
        update=update_game_prop
    )
    lod2_max_particles: bpy.props.IntProperty(
        name="Max Particles",
        description="Maximum active particles at LOD 2",
        default=20, min=0, max=5000,
        update=update_game_prop
    )
    lod2_emission_rate: bpy.props.FloatProperty(
        name="Emission Rate",
        description="Particles per second at LOD 2 (Continuous mode)",
        default=5.0, min=0.0, max=1000.0,
        update=update_game_prop
    )
    lod2_burst_count: bpy.props.IntProperty(
        name="Burst Count",
        description="Particles per burst at LOD 2 (Burst mode)",
        default=8, min=0, max=1500,
        update=update_game_prop
    )
    lod2_disable_turbulence: bpy.props.BoolProperty(
        name="Disable Turbulence",
        description="Disable turbulence at LOD Level 2 to save per-particle noise calculations",
        default=True, update=update_game_prop
    )
    lod2_disable_collision: bpy.props.BoolProperty(
        name="Disable Collision",
        default=True, update=update_game_prop
    )
    lod2_disable_emitting: bpy.props.BoolProperty(
        name="Disable Emitting",
        default=False, update=update_game_prop
    )
    lod2_destroy_particles: bpy.props.BoolProperty(
        name="Destroy Particles",
        description="Return all active particles to the pool immediately when this LOD activates",
        default=False, update=update_game_prop
    )

    # LOD 3
    lod3_distance: bpy.props.FloatProperty(
        name="Distance",
        description="Distance at which LOD 3 activates",
        default=150.0, min=0.0, max=10000.0,
        update=update_game_prop
    )
    lod3_max_particles: bpy.props.IntProperty(
        name="Max Particles",
        description="Maximum active particles at LOD 3",
        default=5, min=0, max=5000,
        update=update_game_prop
    )
    lod3_emission_rate: bpy.props.FloatProperty(
        name="Emission Rate",
        description="Particles per second at LOD 3 (Continuous mode)",
        default=1.0, min=0.0, max=1000.0,
        update=update_game_prop
    )
    lod3_burst_count: bpy.props.IntProperty(
        name="Burst Count",
        description="Particles per burst at LOD 3 (Burst mode)",
        default=3, min=0, max=1500,
        update=update_game_prop
    )
    lod3_disable_turbulence: bpy.props.BoolProperty(
        name="Disable Turbulence",
        description="Disable turbulence at LOD Level 3 to save per-particle noise calculations",
        default=True, update=update_game_prop
    )
    lod3_disable_collision: bpy.props.BoolProperty(
        name="Disable Collision",
        default=True, update=update_game_prop
    )
    lod3_disable_emitting: bpy.props.BoolProperty(
        name="Disable Emitting",
        default=True, update=update_game_prop
    )
    lod3_destroy_particles: bpy.props.BoolProperty(
        name="Destroy Particles",
        description="Return all active particles to the pool immediately when this LOD activates",
        default=True, update=update_game_prop
    )

    # System Launcher
    enable_launcher: bpy.props.BoolProperty(
        name="System Launcher",
        description=(
            "Activates the emitter only when the camera is within range, "
            "destroying all particles and the pool when out of range to save VRAM"
        ),
        default=False,
        update=update_game_prop
    )
    launcher_distance: bpy.props.FloatProperty(
        name="Active Distance",
        description=(
            "Camera distance at which the system fully activates and starts emitting. "
            "If LOD is enabled, LOD takes over inside this range"
        ),
        default=50.0, min=0.1, max=10000.0,
        update=update_game_prop
    )
    launcher_prewarm_distance: bpy.props.FloatProperty(
        name="Pre-warm Distance",
        description=(
            "Camera distance at which the particle pool is silently created in advance, "
            "before the Active Distance is reached — eliminates the hitch on activation"
        ),
        default=70.0, min=0.1, max=10000.0,
        update=update_game_prop
    )

    # Sub-Emitter — On Death
    enable_sub_emitter: bpy.props.BoolProperty(
        name="On Death",
        description="Spawn a burst from another particle system when each particle dies",
        default=False,
        update=update_game_prop
    )

    def sub_emitter_poll(self, object):
        """Only allow objects that have been initialized as a particle emitter"""
        return 'ps_enabled' in object.game.properties

    sub_emitter_object: bpy.props.PointerProperty(
        name="Sub-Emitter (Death)",
        type=bpy.types.Object,
        description="Particle emitter to burst at the death position of each particle",
        poll=sub_emitter_poll,
    )

    sub_emitter_inherit_velocity: bpy.props.BoolProperty(
        name="Inherit Velocity",
        description="Add the dying particle's velocity to the sub-emitter's start velocity",
        default=False,
        update=update_game_prop
    )

    # Sub-Emitter — On Birth
    enable_sub_emitter_birth: bpy.props.BoolProperty(
        name="On Birth",
        description="Spawn a burst from another particle system when each particle is born",
        default=False,
        update=update_game_prop
    )

    sub_emitter_birth_object: bpy.props.PointerProperty(
        name="Sub-Emitter (Birth)",
        type=bpy.types.Object,
        description="Particle emitter to burst at the spawn position of each new particle",
        poll=sub_emitter_poll,
    )

    sub_emitter_birth_inherit_velocity: bpy.props.BoolProperty(
        name="Inherit Velocity",
        description="Add the newborn particle's velocity to the birth sub-emitter's start velocity",
        default=False,
        update=update_game_prop
    )

    # Sub-Emitter — On Collision
    enable_sub_emitter_collision: bpy.props.BoolProperty(
        name="On Collision",
        description="Spawn a burst from another particle system when each particle hits a surface",
        default=False,
        update=update_game_prop
    )

    sub_emitter_collision_object: bpy.props.PointerProperty(
        name="Sub-Emitter (Collision)",
        type=bpy.types.Object,
        description="Particle emitter to burst at the collision point when a particle hits a surface",
        poll=sub_emitter_poll,
    )

    sub_emitter_collision_inherit_velocity: bpy.props.BoolProperty(
        name="Inherit Velocity",
        description="Add the colliding particle's velocity to the collision sub-emitter's start velocity",
        default=False,
        update=update_game_prop
    )

    # Preview mode property
    preview_active: bpy.props.BoolProperty(
        name="Preview Active",
        description="Internal property to track preview state",
        default=False
    )


# Particle System Panel
class PARTICLE_PT_upbge_panel(bpy.types.Panel):
    bl_label = "UPBGE Particle System"
    bl_idname = "PARTICLE_PT_upbge_panel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "physics"

    @classmethod
    def poll(cls, context):
        """Only show panel for valid emitter object types"""
        obj = context.object
        if obj is None:
            return False

        # ALLOWED: Mesh, Light, Empty
        # REJECTED: Camera, Curve, Surface, Meta, Text, Armature, Lattice, Speaker, etc.
        allowed_types = {'MESH', 'LIGHT', 'EMPTY'}
        return obj.type in allowed_types

    def draw(self, context):
        layout = self.layout
        obj = context.object

        if obj is None:
            return

        # Double-check object type
        if obj.type not in {'MESH', 'LIGHT', 'EMPTY'}:
            layout.label(text="Particle system not available for this object type", icon='ERROR')
            return

        box = layout.box()
        box.label(text="Setup:", icon='INFO')
        row = box.row(align=True)
        row.operator("particle.setup_logic", text="Initialize", icon='PLUS')

        # Preview Play/Stop button
        ps = obj.particle_system_props
        if ps.preview_active:
            row.operator("particle.preview_toggle", text="Stop Preview", icon='PAUSE', depress=True)
        else:
            row.operator("particle.preview_toggle", text="Play Preview", icon='PLAY')

        # Clean-up row — remove script and/or game props before re-initializing
        clean_row = box.row(align=True)
        clean_row.operator("particle.remove_script", text="Remove Script", icon='SCRIPT')
        clean_row.operator("particle.remove_props",  text="Remove Props",  icon='TRASH')

        layout.separator()
        layout.prop(ps, "enabled", text="Particle Emitter")
        #Trigger
        layout.prop(ps, "trigger_enabled", text="Emission Trigger")
        if ps.enabled:
            box = layout.box()
            box.label(text="Emission:", icon="PARTICLE_DATA")

            box.prop(ps, "emission_mode", text="Mode", icon= "POINTCLOUD_DATA")
            box.prop(ps, "emission_shape", text="Shape", icon="MESH_CONE")
            
            # Emit From — only for shapes with a meaningful interior or surface
            if ps.emission_shape not in ('POINT', 'RING'):
                emit_row = box.row()
                emit_row.prop(ps, "emit_from", text="Emit From")
                # BASE is cone-only — warn if selected on another shape
                if ps.emit_from == 'BASE' and ps.emission_shape != 'CONE':
                    box.label(text="'Base' is only available for Cone shape", icon='ERROR')

            # Show shape-specific size controls
            if ps.emission_shape == 'BOX':
                box.prop(ps, "emission_box_size")
            elif ps.emission_shape == 'SPHERE':
                box.prop(ps, "emission_sphere_radius")
            elif ps.emission_shape == 'HEMISPHERE':
                box.prop(ps, "emission_hemisphere_radius", text="Radius")
            elif ps.emission_shape == 'CONE':
                box.prop(ps, "emission_cone_radius",      text="Cone Radius")
                box.prop(ps, "emission_cone_height",      text="Cone Height")
                box.prop(ps, "emission_cone_base_radius", text="Base Radius")
            elif ps.emission_shape == 'RING':
                box.prop(ps, "emission_ring_radius", text="Ring Radius")
                box.prop(ps, "emission_ring_width",  text="Ring Width")

            box.prop(ps, "max_particles")

            if ps.emission_mode == 'CONTINUOUS':
                box.prop(ps, "emission_rate")
            else: # BURST MODE
                box.prop(ps, "burst_count")
                box.prop(ps, "is_one_shot")
                # HIDE DELAY IF ONE SHOT IS ACTIVE
                if not ps.is_one_shot:
                    box.prop(ps, "emission_delay")

            box.prop(ps, "lifetime")
            box.prop(ps, "lifetime_random")

            box = layout.box()
            box.label(text="Appearance:", icon="MESH_ICOSPHERE")

            # Particle type selector
            box.prop(ps, "particle_type", text="Particle Type", icon="MESH_DATA")

            if ps.particle_type == 'MESH':
                # Lock particle mesh during preview to prevent crashes
                mesh_row = box.row()
                mesh_row.enabled = not ps.preview_active
                mesh_row.prop(ps, "particle_mesh")
                if ps.preview_active:
                    box.label(text="(Mesh locked during preview)", icon='LOCKED')
            else:
                # Billboard mode plane info
                bb_name = f"PS_BP_{obj.name}"
                if bb_name in bpy.data.objects:
                    box.label(text=f"Plane: {bb_name}", icon='MESH_PLANE')
                # Rotation method — only meaningful for billboards
                box.prop(ps, "billboard_facing", text="Rotation Method", icon='ORIENTATION_GIMBAL')

            box.prop(ps, "size_mode", text="Size Mode")
            size_row = box.row(align=True)
            size_row.prop(ps, "start_size")
            size_row.prop(ps, "end_size")
            if ps.size_mode == 'CURVE':
                obj_active = context.active_object
                if obj_active:
                    size_curve_node = get_size_curve_node(obj_active.name)
                    if size_curve_node is None:
                        box.label(text="No curve yet — click to create:", icon='INFO')
                        box.operator("particle.init_size_curve",
                                     text="Initialize Size Curve", icon='IPO_EASE_IN_OUT')
                    else:
                        box.template_curve_mapping(size_curve_node, "mapping", type='NONE',
                                                   levels=False, brush=False,
                                                   use_negative_slope=False)
                        box.label(text="Hit Apply Material to bake", icon='INFO')
            box.separator()
            # Material settings
            box = layout.box()
            box.label(text="Material:", icon='MATERIAL')

            # Material type — Emission (unlit) or BSDF (lit)
            box.prop(ps, "material_type", text="Type", icon='NODE_MATERIAL')
            if ps.material_type == 'EMISSION':
                box.prop(ps, "emission_strength", text="Strength")

            # Texture
            box.prop(ps, "enable_texture", text="Enable Texture")
            if ps.enable_texture:
                row = box.row(align=True)
                row.template_ID(ps, "billboard_texture", open="image.open", unlink="image.unlink")
                if not ps.billboard_texture:
                    box.label(text="No image selected — texture slot will be empty", icon='ERROR')
                box.prop(ps, "texture_render", text="Texture Render")

            # Color over Lifetime
            box.prop(ps, "enable_color", text="Color over Lifetime")
            if ps.enable_color:
                box.prop(ps, "color_mode", text="Mode")
                row2 = box.row()
                row2.prop(ps, "color_start", text="Start")
                row2.prop(ps, "color_end",   text="End")
                if ps.color_mode == 'SIMPLE':
                    row3 = box.row(align=True)
                    row3.prop(ps, "color_start_time", text="From")
                    row3.prop(ps, "color_end_time",   text="To")
                else:  # CURVE
                    obj_active = context.active_object
                    if obj_active:
                        curve_node = get_color_curve_node(obj_active.name)
                        if curve_node is None:
                            box.label(text="No curve yet — click to create:", icon='INFO')
                            box.operator("particle.init_color_curve",
                                         text="Initialize Color Curve", icon='IPO_EASE_IN_OUT')
                        else:
                            box.template_curve_mapping(curve_node, "mapping", type='NONE',
                                                       levels=False, brush=False,
                                                       use_negative_slope=False)
                            box.label(text="Hit Apply Material to bake", icon='INFO')

            # Alpha over Lifetime
            box.prop(ps, "enable_alpha", text="Alpha over Lifetime")
            if ps.enable_alpha:
                box.prop(ps, "alpha_mode", text="Mode")
                if ps.alpha_mode == 'SIMPLE':
                    alpha_row = box.row(align=True)
                    alpha_row.prop(ps, "start_alpha", text="Start", slider=True)
                    alpha_row.prop(ps, "end_alpha",   text="End",   slider=True)
                    alpha_time_row = box.row(align=True)
                    alpha_time_row.prop(ps, "alpha_start_time", text="From")
                    alpha_time_row.prop(ps, "alpha_end_time",   text="To")
                else:  # CURVE
                    obj_active = context.active_object
                    if obj_active:
                        alpha_curve_node = get_alpha_curve_node(obj_active.name)
                        if alpha_curve_node is None:
                            box.label(text="No curve yet — click to create:", icon='INFO')
                            box.operator("particle.init_alpha_curve",
                                         text="Initialize Alpha Curve", icon='IPO_EASE_IN_OUT')
                        else:
                            box.template_curve_mapping(alpha_curve_node, "mapping", type='NONE',
                                                       levels=False, brush=False,
                                                       use_negative_slope=False)
                            box.label(text="Hit Apply Material to bake", icon='INFO')

            # Apply Material button
            box.separator()
            box.operator("particle.apply_material", text="Apply Material", icon='NODE_MATERIAL')

            # Physics
            box = layout.box()
            box.label(text="Physics:", icon="DRIVER_TRANSFORM")

            box.prop(ps, "simulation_space", text="Space", icon= "OBJECT_ORIGIN")
            if ps.simulation_space == 'LOCAL':
                box.prop(ps, "parent_with_emitter", text="Parent with Emitter")
            box.prop(ps, "movement_type", text="Movement", icon= "EMPTY_ARROWS")

            # Conditional UI based on movement type
            is_bb = (ps.particle_type == 'BILLBOARD')
            if ps.movement_type == 'SIMPLE':
                # Simple mode
                box.prop(ps, "start_velocity")
                if not is_bb:
                    box.prop(ps, "rotation")
                box.prop(ps, "velocity_random")
                box.separator()
                box.prop(ps, "enable_gravity", text="Enable Gravity")
                if ps.enable_gravity:
                    box.prop(ps, "gravity_power", text="Gravity Power")
            elif ps.movement_type == 'ORBIT':
                # Orbit mode
                orb_box = box.box()
                orb_box.label(text="Orbit Settings", icon='FORCE_VORTEX')
                orb_box.prop(ps, "orbit_center",       text="Center", icon="ORIENTATION_GIMBAL")
                axis_row = orb_box.row(align=True)
                axis_row.label(text="Axis:")
                axis_row.prop(ps, "orbit_axis_x", toggle=True)
                axis_row.prop(ps, "orbit_axis_y", toggle=True)
                axis_row.prop(ps, "orbit_axis_z", toggle=True)
                axis_row.separator()
                axis_row.prop(ps, "orbit_axis_inverse", toggle=True, icon='ARROW_LEFTRIGHT')
                if not ps.orbit_axis_x and not ps.orbit_axis_y and not ps.orbit_axis_z:
                    orb_box.label(text="Select at least one axis", icon='ERROR')
                orb_box.prop(ps, "orbit_speed",        text="Speed")
                orb_box.prop(ps, "orbit_speed_random", text="Speed Random")
                orb_box.prop(ps, "orbit_radius",       text="Radius")
                orb_box.prop(ps, "orbit_radius_random",text="Radius Random")
                orb_box.prop(ps, "orbit_tilt",         text="Tilt", icon="DRIVER_ROTATIONAL_DIFFERENCE", slider=True)
                box.separator()
                box.prop(ps, "enable_gravity", text="Enable Gravity")
                if ps.enable_gravity:
                    box.prop(ps, "gravity_power", text="Gravity Power")
            else:
                # Force-based mode
                force_box = box.box()
                force_box.label(text="Force Settings:", icon='FORCE_DRAG')
                force_box.prop(ps, "start_velocity", text="Initial Velocity")
                force_box.prop(ps, "force")
                if not is_bb:
                    force_box.prop(ps, "torque")
                box.prop(ps, "billboard_roll_enabled", text="Billboard Roll")
                if ps.billboard_roll_enabled:
                    roll_row = box.row(align=True)
                    roll_row.prop(ps, "billboard_roll_speed",  text="Speed")
                    roll_row.prop(ps, "billboard_roll_random", text="Random")
                box.prop(ps, "drag_enabled", text="Drag over Lifetime")
                if ps.drag_enabled:
                    drag_row = box.row(align=True)
                    drag_row.prop(ps, "drag_start", text="Start", slider=True)
                    drag_row.prop(ps, "drag_end",   text="End",   slider=True)
                    box.prop(ps, "resistance_strength", text="Resistance Strength", slider=True)
                box.prop(ps, "velocity_random")
                box.separator()
                box.prop(ps, "enable_gravity", text="Enable Gravity")
                if ps.enable_gravity:
                    box.prop(ps, "gravity_power", text="Gravity Power")

            # Collision section
            box.separator()
            box.prop(ps, "enable_collision", text="Enable Collision")
            if ps.enable_collision:
                box.prop(ps, "bounce_strength", slider=True)
                if ps.bounce_strength == 0.0:
                    box.prop(ps, "stop_on_collision", text="Stop Movement")

            # Turbulence section
            box.separator()
            box.prop(ps, "enable_turbulence", text="Enable Turbulence")
            if ps.enable_turbulence:
                box.prop(ps, "turbulence_strength",  text="Strength")
                box.prop(ps, "turbulence_frequency", text="Frequency")
                box.prop(ps, "turbulence_speed",     text="Speed")

            # Sub-Emitter section
            box = layout.box()
            box.label(text="Sub-Emitter:", icon="PARTICLES")

            def _draw_sub_event(box, enable_prop, obj_prop, inherit_prop, label, obj_ref):
                row = box.row(align=True)
                row.prop(ps, enable_prop, text=label)
                if getattr(ps, enable_prop):
                    box.prop(ps, obj_prop, text="")
                    if obj_ref is None:
                        box.label(text="Assign an initialized emitter", icon='INFO')
                    elif obj_ref == obj:
                        box.label(text="Cannot be the emitter itself", icon='ERROR')
                    else:
                        box.prop(ps, inherit_prop, text="Inherit Velocity")

            _draw_sub_event(box,
                "enable_sub_emitter", "sub_emitter_object", "sub_emitter_inherit_velocity",
                "On Death", ps.sub_emitter_object)
            _draw_sub_event(box,
                "enable_sub_emitter_birth", "sub_emitter_birth_object", "sub_emitter_birth_inherit_velocity",
                "On Birth", ps.sub_emitter_birth_object)
            # On Collision only makes sense when collision is enabled
            coll_row = box.row(align=True)
            if not ps.enable_collision:
                coll_row.enabled = False
                coll_row.prop(ps, "enable_sub_emitter_collision", text="On Collision")
                box.label(text="Enable Collision to use On Collision sub-emitter", icon='INFO')
            else:
                _draw_sub_event(box,
                    "enable_sub_emitter_collision", "sub_emitter_collision_object",
                    "sub_emitter_collision_inherit_velocity",
                    "On Collision", ps.sub_emitter_collision_object)

            # Render / LOD box / System launcher
            box = layout.box()
            box.label(text="Render:",  icon="RESTRICT_RENDER_OFF")
            box.separator()
            box.prop(ps, "enable_launcher", text="System Launcher")
            if ps.enable_launcher:
                sl_box = box.box()
                sl_box.label(text="System Launcher", icon='DRIVER_DISTANCE')

                # Warn if prewarm <= active distance
                if ps.enable_lod:
                    # Active threshold = last enabled LOD level distance
                    lod_lvl_count = int(ps.lod_levels)
                    if lod_lvl_count == 1:
                        active_thresh_val = ps.lod1_distance
                    elif lod_lvl_count == 2:
                        active_thresh_val = ps.lod2_distance
                    else:
                        active_thresh_val = ps.lod3_distance
                    if ps.launcher_prewarm_distance <= active_thresh_val:
                        sl_box.label(text="Pre-warm Distance should be > Active Distance", icon='ERROR')
                    sl_box.label(text=f"Active threshold: LOD {lod_lvl_count} dist ({active_thresh_val:.1f}m)", icon='INFO')
                else:
                    if ps.launcher_prewarm_distance <= ps.launcher_distance:
                        sl_box.label(text="Pre-warm Distance should be > Active Distance", icon='ERROR')
                    sl_box.prop(ps, "launcher_distance", text="Active Distance")

                sl_box.prop(ps, "launcher_prewarm_distance", text="Pre-warm Distance")

            box.prop(ps, "enable_lod", text="Enable LOD")
            # LOD
            if ps.enable_lod:
                box.prop(ps, "lod_levels", text="LOD Levels", icon="MOD_PARTICLE_INSTANCE")

                # Start LOD — always shown
                lod0_box = box.box()
                lod0_box.label(text="Start LOD")
                lod0_box.prop(ps, "lod_start_distance", text="Start LOD")

                # Level 1 — always shown (minimum 1 level)
                lod1_box = box.box()
                lod1_box.label(text="Level 1")
                lod1_box.prop(ps, "lod1_distance", text="Distance")
                lod1_emit_off = ps.lod1_disable_emitting
                lod1_row_max  = lod1_box.row(); lod1_row_max.enabled = not lod1_emit_off
                lod1_row_max.prop(ps, "lod1_max_particles", text="Max Particles")
                lod1_row_rate = lod1_box.row(); lod1_row_rate.enabled = not lod1_emit_off
                if ps.emission_mode == 'BURST':
                    lod1_row_rate.prop(ps, "lod1_burst_count", text="Burst Count")
                else:
                    lod1_row_rate.prop(ps, "lod1_emission_rate", text="Emission Rate")
                lod1_box.prop(ps, "lod1_disable_turbulence", text="Disable Turbulence")
                lod1_box.prop(ps, "lod1_disable_collision", text="Disable Collision")
                lod1_box.prop(ps, "lod1_disable_emitting",  text="Disable Emitting")
                if ps.lod1_disable_emitting:
                    lod1_box.prop(ps, "lod1_destroy_particles", text="Destroy Particles")

                # Level 2 — shown for 2 or 3 levels
                if ps.lod_levels in ('2', '3'):
                    lod2_box = box.box()
                    lod2_box.label(text="Level 2")
                    lod2_box.prop(ps, "lod2_distance", text="Distance")
                    lod2_emit_off = ps.lod2_disable_emitting
                    lod2_row_max  = lod2_box.row(); lod2_row_max.enabled = not lod2_emit_off
                    lod2_row_max.prop(ps, "lod2_max_particles", text="Max Particles")
                    lod2_row_rate = lod2_box.row(); lod2_row_rate.enabled = not lod2_emit_off
                    if ps.emission_mode == 'BURST':
                        lod2_row_rate.prop(ps, "lod2_burst_count", text="Burst Count")
                    else:
                        lod2_row_rate.prop(ps, "lod2_emission_rate", text="Emission Rate")
                    lod2_box.prop(ps, "lod2_disable_turbulence", text="Disable Turbulence")
                    lod2_box.prop(ps, "lod2_disable_collision", text="Disable Collision")
                    lod2_box.prop(ps, "lod2_disable_emitting",  text="Disable Emitting")
                    if ps.lod2_disable_emitting:
                        lod2_box.prop(ps, "lod2_destroy_particles", text="Destroy Particles")

                # Level 3 — shown only for 3 levels
                if ps.lod_levels == '3':
                    lod3_box = box.box()
                    lod3_box.label(text="Level 3")
                    lod3_box.prop(ps, "lod3_distance", text="Distance")
                    lod3_emit_off = ps.lod3_disable_emitting
                    lod3_row_max  = lod3_box.row(); lod3_row_max.enabled = not lod3_emit_off
                    lod3_row_max.prop(ps, "lod3_max_particles", text="Max Particles")
                    lod3_row_rate = lod3_box.row(); lod3_row_rate.enabled = not lod3_emit_off
                    if ps.emission_mode == 'BURST':
                        lod3_row_rate.prop(ps, "lod3_burst_count", text="Burst Count")
                    else:
                        lod3_row_rate.prop(ps, "lod3_emission_rate", text="Emission Rate")
                    lod3_box.prop(ps, "lod3_disable_turbulence", text="Disable Turbulence")
                    lod3_box.prop(ps, "lod3_disable_collision", text="Disable Collision")
                    lod3_box.prop(ps, "lod3_disable_emitting",  text="Disable Emitting")
                    if ps.lod3_disable_emitting:
                        lod3_box.prop(ps, "lod3_destroy_particles", text="Destroy Particles")

class PARTICLE_OT_preview_toggle(bpy.types.Operator):
    """Toggle viewport particle preview"""
    bl_idname = "particle.preview_toggle"
    bl_label = "Toggle Particle Preview"

    _timer = None
    _particles = None
    _time_accumulator = 0.0
    _last_time = 0.0
    _burst_timer = 0.0
    _burst_triggered = False
    _original_object = None
    _default_sphere = None
    _billboard_mesh = None

    def modal(self, context, event):
        # Check if user pressed
        if event.type == 'P' and event.value == 'PRESS':
            self.cancel(context)
            return {'CANCELLED'}

        if event.type == 'TIMER':
            # Check if active object changed
            if context.object != self._original_object:
                self.cancel(context)
                return {'CANCELLED'}

            obj = context.object
            if not obj or not obj.particle_system_props.preview_active:
                self.cancel(context)
                return {'CANCELLED'}

            ps = obj.particle_system_props

            # Calculate delta time
            current_time = time.time()
            if self._last_time == 0:
                dt = 0.016
            else:
                dt = current_time - self._last_time
            self._last_time = current_time
            dt = min(dt, 0.1)

            # Update existing particles
            if self._particles is None:
                self._particles = []  # Safety guard — normally set in execute()

            # Hoist per-frame constants out of the particle loop
            gravity       = Vector((0.0, 0.0, ps.gravity_power if ps.enable_gravity else 0.0))
            enable_coll   = ps.enable_collision
            bounce        = ps.bounce_strength
            movement_type = ps.movement_type
            is_force      = (movement_type == 'FORCE')

            # FORCE mode constants
            if is_force:
                force_vec    = Vector(ps.force)
                prev_drag_on  = ps.drag_enabled
                prev_drag_s   = ps.drag_start          if prev_drag_on else 0.0
                prev_drag_e   = ps.drag_end            if prev_drag_on else 0.0
                prev_resist   = ps.resistance_strength if prev_drag_on else 1.0
                acc           = (force_vec + gravity) * dt
                torque_xyz   = ps.torque
                has_torque   = (torque_xyz[0] != 0 or torque_xyz[1] != 0 or torque_xyz[2] != 0)
                if has_torque:
                    torque_rad = Vector((math.radians(torque_xyz[0]),
                                        math.radians(torque_xyz[1]),
                                        math.radians(torque_xyz[2]))) * dt
            else:
                grav_dt = gravity * dt   # SIMPLE: gravity only

            # SIMPLE rotation constants
            rot_xyz      = ps.rotation
            has_rotation = (rot_xyz[0] != 0 or rot_xyz[1] != 0 or rot_xyz[2] != 0)
            if has_rotation:
                rot_rad = (math.radians(rot_xyz[0]),
                           math.radians(rot_xyz[1]),
                           math.radians(rot_xyz[2]))

            # Sample curves once per tick (not per particle) — None means Simple mode
            _preview_curve       = (sample_color_curve(obj.name)
                                    if (ps.enable_color and ps.color_mode == 'CURVE') else None)
            _preview_size_curve  = (sample_size_curve(obj.name)
                                    if ps.size_mode == 'CURVE' else None)
            _preview_alpha_curve = (sample_alpha_curve(obj.name)
                                    if (ps.enable_alpha and ps.alpha_mode == 'CURVE') else None)

            # Fetch viewport camera data once per tick.
            # _cam_rot_mat — used by CAM_ROT mode (shared matrix for all particles).
            # _cam_eye     — used by LOOK_AT mode (per-particle direction vector).
            _cam_eye = None
            _cam_rot_mat = None
            if ps.particle_type == 'BILLBOARD':
                for area in context.screen.areas:
                    if area.type == 'VIEW_3D':
                        rv3d = area.spaces.active.region_3d
                        if rv3d:
                            view_inv = rv3d.view_matrix.inverted()
                            _cam_eye = view_inv.translation.copy()
                            # Camera orientation + 90° X correction so the XZ plane
                            # faces the camera rather than lying parallel to it.
                            _cam_rot_mat = view_inv.to_3x3() @ Matrix.Rotation(math.pi / 2.0, 3, 'X')
                        break

            to_remove = []
            for i, particle_data in enumerate(self._particles):
                particle_obj, age, lifetime, start_size, end_size, velocity, angular_velocity, rotation, is_billboard, col_start, col_end, col_t0, col_t1, p_start_alpha, p_end_alpha, p_alpha_t0, p_alpha_t1 = particle_data
                age += dt

                if age >= lifetime:
                    to_remove.append(i)
                    try:
                        bpy.data.objects.remove(particle_obj, do_unlink=True)
                    except ReferenceError:
                        pass
                    continue

                # Physics
                if is_force:
                    # Apply force + gravity then drag over lifetime
                    velocity += acc
                    if prev_drag_on:
                        life_r = age / lifetime
                        velocity *= 1.0 - (prev_drag_s + (prev_drag_e - prev_drag_s) * life_r) * prev_resist * dt
                else:
                    # SIMPLE: gravity only
                    velocity += grav_dt

                # Turbulence — sample noise at particle world position using the same
                # value-noise hash as the runtime script, so preview matches in-game.
                if ps.enable_turbulence:
                    def _preview_noise(x, y, z):
                        ix, iy, iz = int(x) & 255, int(y) & 255, int(z) & 255
                        fx, fy, fz = x - int(x), y - int(y), z - int(z)
                        ux = fx * fx * (3.0 - 2.0 * fx)
                        uy = fy * fy * (3.0 - 2.0 * fy)
                        uz = fz * fz * (3.0 - 2.0 * fz)
                        def h(a, b, c):
                            n = (a * 1619 + b * 31337 + c * 6971) & 0x7fffffff
                            n = (n >> 13) ^ n
                            return ((n * (n * n * 60493 + 19990303) + 1376312589) & 0x7fffffff) / 1073741824.0 - 1.0
                        def lerp(a, b, t): return a + t * (b - a)
                        return lerp(
                            lerp(lerp(h(ix,iy,iz),   h(ix+1,iy,iz),   ux),
                                 lerp(h(ix,iy+1,iz), h(ix+1,iy+1,iz), ux), uy),
                            lerp(lerp(h(ix,iy,iz+1),   h(ix+1,iy,iz+1),   ux),
                                 lerp(h(ix,iy+1,iz+1), h(ix+1,iy+1,iz+1), ux), uy),
                            uz)
                    _tt = time.time() * ps.turbulence_speed
                    _tf = ps.turbulence_frequency
                    _ts = ps.turbulence_strength
                    px = particle_obj.location.x * _tf
                    py = particle_obj.location.y * _tf
                    pz = particle_obj.location.z * _tf
                    velocity.x += _preview_noise(px,        py,        pz        + _tt) * _ts * dt
                    velocity.y += _preview_noise(px + 31.7, py,        pz        + _tt) * _ts * dt
                    velocity.z += _preview_noise(px,        py + 57.3, pz        + _tt) * _ts * dt

                # Position integration + collision (ground plane Z=0 for preview)
                if enable_coll:
                    next_pos = particle_obj.location + velocity * dt
                    if next_pos.z < 0:
                        if ps.stop_on_collision:
                            velocity.x = velocity.y = velocity.z = 0.0
                            next_pos.z = 0.0
                        else:
                            velocity.z = -velocity.z * bounce
                            next_pos.z = 0.01
                    particle_obj.location = next_pos
                else:
                    particle_obj.location += velocity * dt

                # Size interpolation
                life_ratio = age / lifetime
                if _preview_size_curve:
                    n1  = len(_preview_size_curve) - 1
                    idx = life_ratio * n1
                    lo  = int(idx)
                    hi  = min(lo + 1, n1)
                    t_s = _preview_size_curve[lo] + (_preview_size_curve[hi] - _preview_size_curve[lo]) * (idx - lo)
                    size = start_size + (end_size - start_size) * t_s
                else:
                    size = start_size + (end_size - start_size) * life_ratio
                particle_obj.scale = Vector((size, size, size))

                # Color over lifetime
                if ps.enable_color or ps.enable_alpha:
                    if ps.enable_color:
                        t = (life_ratio - col_t0) / max(col_t1 - col_t0, 0.0001)
                        t = max(0.0, min(1.0, t))
                        if _preview_curve:
                            n1  = len(_preview_curve) - 1
                            idx = t * n1
                            lo  = int(idx)
                            hi  = min(lo + 1, n1)
                            t   = _preview_curve[lo] + (_preview_curve[hi] - _preview_curve[lo]) * (idx - lo)
                        cr = col_start[0] + (col_end[0] - col_start[0]) * t
                        cg = col_start[1] + (col_end[1] - col_start[1]) * t
                        cb = col_start[2] + (col_end[2] - col_start[2]) * t
                    else:
                        cr, cg, cb = 1.0, 1.0, 1.0

                    if ps.enable_alpha:
                        t_a = (life_ratio - p_alpha_t0) / max(p_alpha_t1 - p_alpha_t0, 0.0001)
                        t_a = max(0.0, min(1.0, t_a))
                        if _preview_alpha_curve:
                            # Curve mode: Y value IS the alpha
                            n1  = len(_preview_alpha_curve) - 1
                            idx = t_a * n1
                            lo  = int(idx)
                            hi  = min(lo + 1, n1)
                            ca  = _preview_alpha_curve[lo] + (_preview_alpha_curve[hi] - _preview_alpha_curve[lo]) * (idx - lo)
                            ca  = max(0.0, min(1.0, ca))
                        else:
                            ca = p_start_alpha + (p_end_alpha - p_start_alpha) * t_a
                    else:
                        ca = 1.0

                    particle_obj.color = (cr, cg, cb, ca)

                # Billboard orientation — mirrors the runtime's two-method system.
                if is_billboard:
                    if ps.billboard_facing == 'LOOK_AT' and _cam_eye is not None:
                        # Per-particle 3D look-at: build rotation from particle→camera vector.
                        world_z = Vector((0.0, 0.0, 1.0))
                        to_cam  = (_cam_eye - particle_obj.location).normalized()
                        ref     = Vector((0.0, 1.0, 0.0)) if abs(to_cam.dot(world_z)) > 0.999 else world_z
                        right   = ref.cross(to_cam).normalized()
                        up      = to_cam.cross(right).normalized()
                        # col0=right(X), col1=to_cam(Y/normal), col2=up(Z)
                        align_mat = Matrix((
                            (right.x, to_cam.x, up.x),
                            (right.y, to_cam.y, up.y),
                            (right.z, to_cam.z, up.z),
                        ))
                    elif _cam_rot_mat is not None:
                        # CAM_ROT (default): shared camera matrix for all particles.
                        align_mat = _cam_rot_mat
                    else:
                        align_mat = None

                    if align_mat is not None:
                        if ps.billboard_roll_enabled:
                            angular_velocity = Vector(angular_velocity)
                            angular_velocity.y += ps.billboard_roll_speed * math.pi * 2.0 * dt
                            roll_y = rotation[1] + angular_velocity.y
                            roll_mat = Matrix.Rotation(roll_y, 3, 'Y')
                            rotation = (rotation[0], roll_y, rotation[2])
                            particle_obj.rotation_euler = (align_mat @ roll_mat).to_euler()
                        else:
                            particle_obj.rotation_euler = align_mat.to_euler()

                # Rotation (only for MESH type — billboard handles its own orientation)
                if not is_billboard:
                    if is_force and has_torque:
                        # Torque accumulates angular velocity, drag applied
                        angular_velocity += torque_rad
                        if prev_drag_on:
                            life_r = age / lifetime
                            angular_velocity *= 1.0 - (prev_drag_s + (prev_drag_e - prev_drag_s) * life_r) * prev_resist * dt
                        rotation = (rotation[0] + angular_velocity[0] * dt,
                                    rotation[1] + angular_velocity[1] * dt,
                                    rotation[2] + angular_velocity[2] * dt)
                        particle_obj.rotation_euler.x = rotation[0]
                        particle_obj.rotation_euler.y = rotation[1]
                        particle_obj.rotation_euler.z = rotation[2]
                    elif has_rotation:
                        rx = rotation[0] + (rot_rad[0] / lifetime) * dt
                        ry = rotation[1] + (rot_rad[1] / lifetime) * dt
                        rz = rotation[2] + (rot_rad[2] / lifetime) * dt
                        particle_obj.rotation_euler.x = rx
                        particle_obj.rotation_euler.y = ry
                        particle_obj.rotation_euler.z = rz
                        rotation = (rx, ry, rz)

                self._particles[i] = (particle_obj, age, lifetime, start_size, end_size,
                                      velocity, angular_velocity, rotation, is_billboard,
                                      col_start, col_end, col_t0, col_t1,
                                      p_start_alpha, p_end_alpha, p_alpha_t0, p_alpha_t1)

            # Remove dead particles
            for i in reversed(to_remove):
                self._particles.pop(i)

            # Emit new particles
            if ps.enabled and ps.trigger_enabled:
                if ps.emission_mode == 'CONTINUOUS':
                    self._time_accumulator += dt
                    interval = 1.0 / ps.emission_rate if ps.emission_rate > 0 else float('inf')

                    while self._time_accumulator >= interval:
                        self.spawn_particle(context)
                        self._time_accumulator -= interval

                elif ps.emission_mode == 'BURST':
                    if ps.is_one_shot:
                        if not self._burst_triggered:
                            for _ in range(ps.burst_count):
                                self.spawn_particle(context)
                            self._burst_triggered = True
                    else:
                        self._burst_timer += dt
                        if self._burst_timer >= ps.emission_delay:
                            for _ in range(ps.burst_count):
                                self.spawn_particle(context)
                            self._burst_timer = 0.0

            # Force viewport update
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()

        return {'PASS_THROUGH'}

    def spawn_particle(self, context):
        obj = context.object
        ps = obj.particle_system_props

        # Limit max particles
        if len(self._particles) >= ps.max_particles:
            old_particle = self._particles.pop(0)
            try:
                if old_particle[0] and old_particle[0].name in bpy.data.objects:
                    bpy.data.objects.remove(old_particle[0], do_unlink=True)
            except ReferenceError:
                pass  # Object already removed

        # Calculate spawn position based on emission shape
        emission_shape = ps.emission_shape
        mat = obj.matrix_world
        emit_from = ps.emit_from

        if emission_shape == 'BOX':
            box_size = ps.emission_box_size
            if emit_from == 'SURFACE':
                # Pick one of 6 faces, then random point on that face
                axis = random.randint(0, 2)
                side = random.choice([-1, 1])
                half = [box_size[i] * 0.5 for i in range(3)]
                coords = [(random.random() - 0.5) * box_size[i] for i in range(3)]
                coords[axis] = side * half[axis]
                local_offset = Vector(coords)
            else:  # VOLUME
                local_offset = Vector((
                    (random.random() - 0.5) * box_size[0],
                    (random.random() - 0.5) * box_size[1],
                    (random.random() - 0.5) * box_size[2]
                ))
            spawn_pos = mat @ local_offset

        elif emission_shape == 'SPHERE':
            radius = ps.emission_sphere_radius
            u = random.random()
            v = random.random()
            theta = 2 * math.pi * u
            phi   = math.acos(2 * v - 1)
            sin_phi = math.sin(phi)
            if emit_from == 'SURFACE':
                r = radius
            else:  # VOLUME
                r = radius * (random.random() ** (1.0 / 3.0))
            local_offset = Vector((
                r * sin_phi * math.cos(theta),
                r * sin_phi * math.sin(theta),
                r * math.cos(phi)
            ))
            spawn_pos = mat @ local_offset

        elif emission_shape == 'HEMISPHERE':
            # Upper half-sphere (Z >= 0). Uses rejection-free formula:
            # phi in [0, pi/2] gives the upper hemisphere.
            radius = ps.emission_hemisphere_radius
            theta  = random.random() * 2.0 * math.pi
            # cos(phi) uniform in [0,1] gives uniform surface on upper hemisphere
            cos_phi = random.random()
            sin_phi = math.sqrt(1.0 - cos_phi * cos_phi)
            if emit_from == 'SURFACE':
                r = radius
            else:  # VOLUME
                r = radius * (random.random() ** (1.0 / 3.0))
            local_offset = Vector((
                r * sin_phi * math.cos(theta),
                r * sin_phi * math.sin(theta),
                r * cos_phi
            ))
            spawn_pos = mat @ local_offset

        elif emission_shape == 'CONE':
            cone_r  = ps.emission_cone_radius
            cone_h  = ps.emission_cone_height
            cone_br = ps.emission_cone_base_radius
            if emit_from == 'BASE':
                # Uniform disk at Z=0 (the bottom circle at the emitter origin)
                base_r = cone_br if cone_br > 0.0 else cone_r
                r      = base_r * math.sqrt(random.random())
                angle  = random.random() * 2.0 * math.pi
                local_offset = Vector((r * math.cos(angle), r * math.sin(angle), 0.0))
            elif emit_from == 'SURFACE':
                h_frac = math.sqrt(random.random())
                r      = cone_r * h_frac
                angle  = random.random() * 2.0 * math.pi
                local_offset = Vector((r * math.cos(angle), r * math.sin(angle), cone_h * h_frac))
            else:  # VOLUME
                h_frac  = random.random()
                r_max   = cone_r * h_frac
                r       = r_max * math.sqrt(random.random())
                angle   = random.random() * 2.0 * math.pi
                local_offset = Vector((r * math.cos(angle), r * math.sin(angle), cone_h * h_frac))
            spawn_pos = mat @ local_offset

        elif emission_shape == 'RING':
            ring_r = ps.emission_ring_radius
            ring_w = ps.emission_ring_width
            angle  = random.random() * 2.0 * math.pi
            # Random radius within [ring_r - ring_w/2, ring_r + ring_w/2]
            r      = ring_r + (random.random() - 0.5) * ring_w
            local_offset = Vector((r * math.cos(angle), r * math.sin(angle), 0.0))
            spawn_pos = mat @ local_offset

        else:  # POINT
            spawn_pos = mat.translation.copy()

        is_billboard = (ps.particle_type == 'BILLBOARD')

        if is_billboard:
            # Auto-create a plane (shared mesh, instanced objects)
            if self._billboard_mesh is None:
                bm_data = bpy.data.meshes.new("PS_BillboardMesh")
                bm = bmesh.new()
                s = 0.5
                v0 = bm.verts.new((-s, 0.0, -s))
                v1 = bm.verts.new(( s, 0.0, -s))
                v2 = bm.verts.new(( s, 0.0,  s))
                v3 = bm.verts.new((-s, 0.0,  s))
                bm.faces.new((v0, v1, v2, v3))
                bm.to_mesh(bm_data)
                bm.free()
                self._billboard_mesh = bm_data
            particle_obj = bpy.data.objects.new("PS_Billboard", self._billboard_mesh)
        elif ps.particle_mesh:
            particle_obj = ps.particle_mesh.copy()
            particle_obj.data = ps.particle_mesh.data
        else:
            # Fallback default sphere
            if self._default_sphere is None or self._default_sphere.name not in bpy.data.objects:
                prev_active = context.view_layer.objects.active
                bpy.ops.mesh.primitive_uv_sphere_add(radius=0.05, location=(0, 0, 0))
                self._default_sphere = context.view_layer.objects.active
                context.view_layer.objects.active = prev_active
            particle_obj = self._default_sphere.copy()
            particle_obj.data = self._default_sphere.data

        # Link to scene
        context.collection.objects.link(particle_obj)

        # Set initial properties
        particle_obj.location = spawn_pos
        particle_obj.scale = Vector((ps.start_size, ps.start_size, ps.start_size))

        # Calculate random velocity
        base_vel = Vector(ps.start_velocity)
        random_offset = Vector((
            (random.random() - 0.5) * 2.0 * ps.velocity_random,
            (random.random() - 0.5) * 2.0 * ps.velocity_random,
            (random.random() - 0.5) * 2.0 * ps.velocity_random
        ))
        local_vel = base_vel + random_offset
        # LOCAL space: rotate velocity by emitter orientation, matching runtime behaviour
        if ps.simulation_space == 'LOCAL':
            velocity = mat.to_3x3() @ local_vel
        else:
            velocity = local_vel

        # Calculate lifetime
        lifetime = ps.lifetime * (1.0 + (random.random() - 0.5) * ps.lifetime_random)

        # Capture color/alpha settings at spawn time so they stay consistent
        # even if the user changes panel values mid-preview
        p_col_start   = tuple(ps.color_start) if ps.enable_color else (1.0, 1.0, 1.0)
        p_col_end     = tuple(ps.color_end)   if ps.enable_color else (1.0, 1.0, 1.0)
        # Curve mode spans full lifetime — From/To only used in Simple
        if ps.enable_color and ps.color_mode == 'CURVE':
            p_col_t0 = 0.0; p_col_t1 = 1.0
        else:
            p_col_t0  = (ps.color_start_time / 10.0) if ps.enable_color else 0.0
            p_col_t1  = max(ps.color_end_time / 10.0, p_col_t0 + 0.0001) if ps.enable_color else 1.0
        p_start_alpha = ps.start_alpha       if ps.enable_alpha else 1.0
        p_end_alpha   = ps.end_alpha         if ps.enable_alpha else 1.0
        if ps.enable_alpha and ps.alpha_mode == 'CURVE':
            p_alpha_t0 = 0.0; p_alpha_t1 = 1.0
        else:
            p_alpha_t0    = (ps.alpha_start_time / 10.0) if ps.enable_alpha else 0.0
            p_alpha_t1    = max(ps.alpha_end_time / 10.0, p_alpha_t0 + 0.0001) if ps.enable_alpha else 1.0

        # Assign the billboard material so colors/textures show in viewport
        if is_billboard:
            mat_name = f"PS_BillboardMat_{obj.name}"
            mat_data = bpy.data.materials.get(mat_name)
            if mat_data and not particle_obj.data.materials:
                particle_obj.data.materials.append(mat_data)
            elif mat_data and particle_obj.data.materials:
                particle_obj.data.materials[0] = mat_data

        # Store: (obj, age, lifetime, start_size, end_size, velocity, angular_velocity, rotation,
        #         is_billboard, col_start, col_end, col_t0, col_t1, start_alpha)
        self._particles.append((particle_obj, 0.0, lifetime, ps.start_size, ps.end_size,
                                velocity, Vector((0.0, 0.0, 0.0)), (0.0, 0.0, 0.0), is_billboard,
                                p_col_start, p_col_end, p_col_t0, p_col_t1,
                                p_start_alpha, p_end_alpha, p_alpha_t0, p_alpha_t1))

    def execute(self, context):
        obj = context.object
        ps = obj.particle_system_props

        if ps.preview_active:
            # Stop preview
            ps.preview_active = False
            self.cancel(context)
            return {'CANCELLED'}
        else:
            # Start preview - always reinitialize instance state to prevent bleed
            ps.preview_active = True
            self._particles = []
            self._time_accumulator = 0.0
            self._last_time = 0.0
            self._burst_timer = 0.0
            self._burst_triggered = False
            self._original_object = obj  # Track which object started preview
            self._default_sphere = None  # Reset per-session so stale mesh isn't reused
            self._billboard_mesh = None  # Reset billboard plane mesh per-session

            wm = context.window_manager
            self._timer = wm.event_timer_add(0.016, window=context.window)
            wm.modal_handler_add(self)
            return {'RUNNING_MODAL'}

    def cancel(self, context):
        wm = context.window_manager
        if self._timer:
            wm.event_timer_remove(self._timer)
            self._timer = None

        # Clean up all particles
        if self._particles:
            for particle_data in self._particles:
                particle_obj = particle_data[0]
                try:
                    if particle_obj and particle_obj.name in bpy.data.objects:
                        bpy.data.objects.remove(particle_obj, do_unlink=True)
                except ReferenceError:
                    pass
        self._particles = []

        # Clean up shared billboard mesh data block
        if self._billboard_mesh is not None:
            bpy.data.meshes.remove(self._billboard_mesh)
            self._billboard_mesh = None

        # Reset preview_active on the original object (in case context changed)
        if self._original_object and hasattr(self._original_object, 'particle_system_props'):
            self._original_object.particle_system_props.preview_active = False

        # Also try current object as fallback
        obj = context.object
        if obj and hasattr(obj, 'particle_system_props'):
            obj.particle_system_props.preview_active = False

        # Force UI update
        for area in context.screen.areas:
            if area.type == 'PROPERTIES':
                area.tag_redraw()

class PARTICLE_OT_setup_logic(bpy.types.Operator):
    """Setup logic brick and Initialize Game Properties"""
    bl_idname = "particle.setup_logic"
    bl_label = "Setup Particle System"
    bl_options = {'REGISTER', 'UNDO'}

    def _ensure_billboard_template(self, context, init_obj):
        """Create PS_BillboardPlane as an inactive-layer template if not present.
        UPBGE's addObject() spawns from objectsInactive — objects that exist in
        the blend but are not on any active layer at game start.  We create a
        1x1 upright plane (Y-normal faces camera after billboard rotation),
        link it to the scene collection, and mark it hidden so it stays off-screen
        until a particle system spawns an instance from it."""

        # Unique name per emitter so multiple emitters don't share the same template
        plane_name = f'PS_BP_{init_obj.name}'

        # If this emitter already has its own template, nothing to do
        if plane_name in bpy.data.objects:
            return plane_name

        mesh = bpy.data.meshes.new(plane_name)
        bm = bmesh.new()
        s = 0.5
        v0 = bm.verts.new((-s, 0.0, -s))
        v1 = bm.verts.new(( s, 0.0, -s))
        v2 = bm.verts.new(( s, 0.0,  s))
        v3 = bm.verts.new((-s, 0.0,  s))
        face = bm.faces.new((v0, v1, v2, v3))

        # Generate a proper UV map so Image Texture nodes work correctly.
        # Standard unwrap: bottom-left=(0,0) → top-right=(1,1)
        uv_layer = bm.loops.layers.uv.new("UVMap")
        uvs = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
        for loop, uv in zip(face.loops, uvs):
            loop[uv_layer].uv = uv

        bm.to_mesh(mesh)
        bm.free()

        plane_obj = bpy.data.objects.new(plane_name, mesh)
        context.collection.objects.link(plane_obj)

        # Keep visible in viewport so users can select it and manage material slots.
        plane_obj.hide_render = False
        plane_obj.hide_select = False   # Must be selectable so users can add/remove material slots
        plane_obj['ps_auto_billboard'] = True

        # Disable all physics so billboard instances never collide
        plane_obj.game.physics_type = 'NO_COLLISION'

        # Create material and build nodes via the shared helper on PARTICLE_OT_apply_material.
        # This keeps node logic in one place — Apply Material button uses the same code.
        mat_name = f"PS_BillboardMat_{init_obj.name}"
        mat = bpy.data.materials.get(mat_name) or bpy.data.materials.new(name=mat_name)
        PARTICLE_OT_apply_material._build_nodes(mat, init_obj.particle_system_props)
        plane_obj.data.materials.append(mat)

        return plane_name

    def execute(self, context):
        scene = context.scene

        # Camera Check
        if not scene.camera:
            for obj in scene.objects:
                if obj.type == 'CAMERA':
                    scene.camera = obj
                    break

        init_obj = context.active_object
        if not init_obj:
            self.report({'ERROR'}, "Please select an object first")
            return {'CANCELLED'}

        # Validate object type
        if init_obj.type not in {'MESH', 'LIGHT', 'EMPTY'}:
            self.report({'ERROR'}, f"Particle system cannot be used on {init_obj.type} objects. Only MESH, LIGHT, and EMPTY are supported.")
            return {'CANCELLED'}

        added = []  # Track what was added so we can report it

        # Sensor - add only if missing
        if not any(s.name == "ParticleInit" for s in init_obj.game.sensors):
            bpy.ops.logic.sensor_add(type='ALWAYS', name="ParticleInit", object=init_obj.name)
            init_obj.game.sensors[-1].name = "ParticleInit"
            init_obj.game.sensors[-1].use_pulse_true_level = False
            added.append("Sensor")

        # Controller - add only if missing
        existing_ctrl = next((c for c in init_obj.game.controllers if c.name == "ParticleController"), None)
        if not existing_ctrl:
            bpy.ops.logic.controller_add(type='PYTHON', name="ParticleController", object=init_obj.name)
            existing_ctrl = init_obj.game.controllers[-1]
            existing_ctrl.name = "ParticleController"
            existing_ctrl.mode = 'SCRIPT'
            added.append("Controller")
        controller = existing_ctrl

        script_text = """# UPBGE Particle System Runtime v0.9.0

from bge import logic
from mathutils import Vector, Matrix
import random
import math

# Module-level math cache: avoid repeated attribute lookups inside the hot loop
_random = random.random
_pi     = math.pi
_acos   = math.acos
_sqrt   = math.sqrt
_sin    = math.sin
_cos    = math.cos
_radians = math.radians
_atan2  = math.atan2

class Particle:
    __slots__ = ('position', 'velocity', 'age', 'lifetime', 'size',
                 'obj', 'rotation', 'angular_velocity', 'local_offset', 'is_active',
                 'pool_idx',
                 'orbit_angle', 'orbit_speed', 'orbit_radius',
                 'orbit_center', 'orbit_basis_u', 'orbit_basis_v',
                 'roll_angle', 'roll_speed',
                 'is_stopped')
    def __init__(self):
        self.position        = Vector((0.0, 0.0, 0.0))
        self.velocity        = Vector((0.0, 0.0, 0.0))
        self.age             = 0.0
        self.lifetime        = 1.0
        self.size            = 0.1
        self.obj             = None
        self.rotation        = Vector((0.0, 0.0, 0.0))
        self.angular_velocity = Vector((0.0, 0.0, 0.0))
        self.local_offset    = Vector((0.0, 0.0, 0.0))
        self.pool_idx        = -1
        self.is_active       = False
        self.orbit_angle     = 0.0
        self.orbit_speed     = 0.0
        self.orbit_radius    = 1.0
        self.orbit_center    = Vector((0.0, 0.0, 0.0))
        self.orbit_basis_u   = Vector((1.0, 0.0, 0.0))
        self.orbit_basis_v   = Vector((0.0, 1.0, 0.0))
        self.roll_angle      = 0.0
        self.roll_speed      = 0.0
        self.is_stopped      = False
class ParticleSystem:
    __slots__ = (
        # Identity & pool
        'emitter', 'particle_pool', 'inactive_stack',
        'particle_template', 'time_since_emit', 'burst_triggered', 'props',
        # Cached frame constants — hoisted out of hot loop
        '_props_raw',
        '_grav', '_is_local', '_parent_with_emitter', '_is_force', '_is_billboard',
        '_acc', '_acc_per_sec',
        '_lifetime', '_lifetime_random',
        '_start_velocity', '_velocity_random', '_emission_shape',
        '_size_start', '_size_delta', '_size_curve',
        '_drag_start', '_drag_end', '_resistance',
        '_enable_collision', '_bounce', '_stop_on_collision',
        '_enable_color', '_color_start', '_color_end', '_color_curve',
        '_color_t_start', '_color_t_end',
        '_enable_alpha', '_start_alpha', '_end_alpha', '_alpha_t_start', '_alpha_t_end', '_alpha_curve',
        '_has_torque', '_torque_per_sec', '_torque_rad',
        '_rot_has_value', '_rot_rad',
        # Turbulence
        '_turb_enabled', '_turb_strength', '_turb_frequency', '_turb_speed', '_turb_time',
        # LOD
        '_lod_enabled', '_lod_level', '_lod_start', '_lod_table', '_lod_levels_count',
        # System Launcher
        '_launcher_enabled', '_launcher_dist', '_launcher_prewarm',
        '_launcher_active_thresh',  # precomputed: last LOD dist or launcher_dist
        '_launcher_state',   # 'INACTIVE' | 'PREWARM' | 'ACTIVE'
        '_pool_built',       # True once the pool has been created at least once
        '_first_frame',
        # Orbit
        '_is_orbit', '_orbit_use_emitter', '_orbit_axis_vec', '_orbit_tilt_rad',
        '_orbit_radius', '_orbit_radius_random', '_orbit_speed_val', '_orbit_speed_random',
        '_orbit_basis_u', '_orbit_basis_v',   # cached basis vectors for ORBIT mode
        # Billboard Roll
        '_bb_roll_enabled', '_bb_roll_speed', '_bb_roll_random',
        # Billboard facing method: 'CAM_ROT' | 'LOOK_AT'
        '_bb_facing',
        # Sub-Emitter (on-death, on-birth, on-collision)
        '_sub_emitter_enabled', '_sub_emitter_name', '_sub_emitter_inherit_vel',
        '_sub_birth_enabled',   '_sub_birth_name',   '_sub_birth_inherit_vel',
        '_sub_coll_enabled',    '_sub_coll_name',    '_sub_coll_inherit_vel',
    )

    def __init__(self, emitter_obj):
        self.emitter          = emitter_obj
        self.particle_pool    = []
        self.inactive_stack   = []   # FAST O(1) pool: stack of inactive indices
        self.time_since_emit  = 0.0
        self.particle_template = None
        self.burst_triggered  = False
        self.props            = {}
        # Cached per-frame scalars hoisted out of the particle loop
        self._is_local             = False
        self._parent_with_emitter  = False
        self._is_force             = False
        self._lifetime         = 2.0
        self._lifetime_random  = 0.0
        self._start_velocity   = (0.0, 0.0, 1.0)
        self._velocity_random  = 0.0
        self._emission_shape   = 'POINT'
        self._size_start       = 0.1
        self._size_delta      = 0.0   # end_size - start_size, pre-subtracted
        self._size_curve      = None  # None = Simple linear; list of floats = Curve mode
        self._alpha_curve     = None  # None = Simple linear; list of floats = Curve mode
        self._drag_start      = 0.0
        self._drag_end        = 0.0
        self._resistance      = 1.0
        self._enable_collision  = False
        self._bounce            = 0.5
        self._stop_on_collision = False
        self._props_raw       = ()   # Dirty-flag cache: last known raw prop tuple
        self._is_billboard    = False
        self._color_curve     = None   # None = Simple linear; list of floats = Curve mode
        self._turb_time       = 0.0  # Turbulence time accumulator
        self._lod_level       = 0    # Current active LOD level (0 = full sim)
        self._lod_levels_count = 3   # How many LOD entries are active (1/2/3)
        # System Launcher
        self._launcher_enabled       = False
        self._launcher_dist          = 50.0
        self._launcher_prewarm       = 70.0
        self._launcher_active_thresh = 50.0
        self._launcher_state         = 'INACTIVE'
        self._pool_built             = False
        # Orbit
        self._is_orbit           = False
        self._orbit_use_emitter  = True
        self._orbit_axis_vec     = Vector((0.0, 0.0, 1.0))
        self._orbit_tilt_rad     = 0.0
        self._orbit_radius       = 1.0
        self._orbit_radius_random = 0.0
        self._orbit_speed_val    = 1.0
        self._orbit_speed_random = 0.0
        self._orbit_basis_u      = Vector((1.0, 0.0, 0.0))
        self._orbit_basis_v      = Vector((0.0, 1.0, 0.0))
        self._first_frame        = True
        # Billboard Roll
        self._bb_roll_enabled    = False
        self._bb_roll_speed      = 0.3
        self._bb_roll_random     = 0.2
        # Billboard facing method
        self._bb_facing          = 'CAM_ROT'
        # Sub-Emitter
        self._sub_emitter_enabled     = False
        self._sub_emitter_name        = ''
        self._sub_emitter_inherit_vel = False
        self._sub_birth_enabled       = False
        self._sub_birth_name          = ''
        self._sub_birth_inherit_vel   = False
        self._sub_coll_enabled        = False
        self._sub_coll_name           = ''
        self._sub_coll_inherit_vel    = False
        self.load_properties()
        self.create_particle_template()
        self.initialize_pool()
        self._pool_built = True

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    def _read_raw_props(self):
        '''Read all game properties into a flat tuple for cheap equality comparison.
        Costs N attribute reads but no dict allocation — called every frame.'''
        g = self.emitter.get
        return (
            g('ps_enabled',             True),   # 0
            g('ps_trigger',             True),   # 1
            g('ps_emission_mode',       'CONTINUOUS'),  # 2
            g('ps_emission_shape',      'POINT'),       # 3
            g('ps_emission_box_size_x', 1.0),    # 4
            g('ps_emission_box_size_y', 1.0),    # 5
            g('ps_emission_box_size_z', 1.0),    # 6
            g('ps_emission_sphere_radius', 1.0), # 7
            g('ps_emission_cone_radius',   1.0), # 8
            g('ps_emission_cone_height',   2.0), # 9
            g('ps_max_particles',       100),    # 10
            g('ps_emission_rate',       10.0),   # 11
            g('ps_emission_delay',      1.0),    # 12
            g('ps_burst_count',         30),     # 13
            g('ps_is_one_shot',         False),  # 14
            g('ps_lifetime',            3.0),    # 15
            g('ps_lifetime_random',     0.5),    # 16
            g('ps_start_size',          0.1),    # 17
            g('ps_end_size',            0.05),   # 18
            g('ps_start_velocity_x',    0.0),    # 19
            g('ps_start_velocity_y',    0.0),    # 20
            g('ps_start_velocity_z',    2.0),    # 21
            g('ps_velocity_random',     0.5),    # 22
            g('ps_enable_gravity',      True),   # 23
            g('ps_gravity_power',       -9.8),   # 24
            g('ps_particle_mesh',       'ParticleSphere'),  # 25
            g('ps_simulation_space',    'WORLD'),           # 26
            g('ps_parent_with_emitter', False),             # 27
            g('ps_movement_type',       'SIMPLE'),          # 28
            g('ps_force_x',             0.0),    # 29
            g('ps_force_y',             0.0),    # 30
            g('ps_force_z',             0.0),    # 31
            g('ps_torque_x',            0.0),    # 32
            g('ps_torque_y',            0.0),    # 33
            g('ps_torque_z',            0.0),    # 34
            g('ps_drag_enabled',        False),  # 35
            g('ps_drag_start',           0.0),   # 36
            g('ps_drag_end',             0.5),   # 37
            g('ps_resistance',           1.0),   # 38
            g('ps_enable_collision',    False),  # 39
            g('ps_bounce_strength',     0.5),    # 40
            g('ps_stop_on_collision',   False),  # 41
            g('ps_rotation_x',          0.0),    # 42
            g('ps_rotation_y',          0.0),    # 43
            g('ps_rotation_z',          0.0),    # 44
            g('ps_particle_type',       'MESH'), # 45
            g('ps_billboard_template',  '  '),   # 46
            g('ps_color_start_r',       1.0),    # 47
            g('ps_color_start_g',       1.0),    # 48
            g('ps_color_start_b',       1.0),    # 49
            g('ps_color_end_r',         1.0),    # 50
            g('ps_color_end_g',         0.0),    # 51
            g('ps_color_end_b',         0.0),    # 52
            g('ps_color_start_time',    0.0),    # 53
            g('ps_color_end_time',      10.0),   # 54
            g('ps_start_alpha',         1.0),    # 55
            g('ps_end_alpha',            0.0),   # 56
            g('ps_alpha_start_time',     0.0),   # 57
            g('ps_alpha_end_time',       10.0),  # 58
            g('ps_enable_color',        False),  # 59
            g('ps_enable_alpha',        False),  # 60
            g('ps_enable_turb',         False),  # 61
            g('ps_turb_strength',       0.5),    # 62
            g('ps_turb_frequency',      0.5),    # 63
            g('ps_turb_speed',          0.5),    # 64
            g('ps_enable_lod',          False),  # 65
            g('ps_lod_start',           20.0),   # 66
            g('ps_lod1_dist',           40.0),   # 67
            g('ps_lod1_max',            50),     # 68
            g('ps_lod1_rate',           10.0),   # 69
            g('ps_lod1_burst',          15),     # 70
            g('ps_lod1_no_turb',        False),  # 71
            g('ps_lod1_no_coll',        False),  # 72
            g('ps_lod1_no_emit',        False),  # 73
            g('ps_lod1_destroy',        False),  # 74
            g('ps_lod2_dist',           80.0),   # 75
            g('ps_lod2_max',            20),     # 76
            g('ps_lod2_rate',           5.0),    # 77
            g('ps_lod2_burst',          8),      # 78
            g('ps_lod2_no_turb',        True),   # 79
            g('ps_lod2_no_coll',        True),   # 80
            g('ps_lod2_no_emit',        False),  # 81
            g('ps_lod2_destroy',        False),  # 82
            g('ps_lod3_dist',           150.0),  # 83
            g('ps_lod3_max',            5),      # 84
            g('ps_lod3_rate',           1.0),    # 85
            g('ps_lod3_burst',          3),      # 86
            g('ps_lod3_no_turb',        True),   # 87
            g('ps_lod3_no_coll',        True),   # 88
            g('ps_lod3_no_emit',        True),   # 89
            g('ps_lod3_destroy',        True),   # 90
            # System Launcher
            g('ps_launcher_enabled',    False),  # 91
            g('ps_launcher_dist',       50.0),   # 92
            g('ps_launcher_prewarm',    70.0),   # 93
            # Orbit
            g('ps_orbit_center',        'EMITTER'),  # 94
            g('ps_orbit_axis_x',        False),      # 95
            g('ps_orbit_axis_y',        False),      # 96
            g('ps_orbit_axis_z',        True),       # 97
            g('ps_orbit_speed',         0.5),        # 98
            g('ps_orbit_speed_random',  0.0),        # 99
            g('ps_orbit_radius',        2.0),        # 100
            g('ps_orbit_radius_random', 0.0),        # 101
            g('ps_orbit_axis_inverse',  False),      # 102
            # Billboard Roll
            g('ps_bb_roll_enabled',     False),      # 103
            g('ps_bb_roll_speed',       0.3),        # 104
            g('ps_bb_roll_random',      0.2),        # 105
            g('ps_color_curve',         '  '),       # 106 — baked curve samples, '  ' = Simple
            g('ps_size_curve',          '  '),       # 107 — baked size curve, '  ' = Simple
            g('ps_alpha_curve',         '  '),       # 108 — baked alpha curve, '  ' = Simple
            g('ps_emission_ring_radius', 1.0),       # 109
            g('ps_emission_ring_width',  0.1),       # 110
            g('ps_orbit_tilt',                0.0),        # 111
            g('ps_emit_from',                 'VOLUME'),   # 112
            g('ps_emission_hemisphere_radius', 1.0),       # 113
            g('ps_emission_cone_base_radius',  0.0),       # 114
            g('ps_lod_levels',                '3'),        # 115 — '1'/'2'/'3'
            g('ps_color_mode',                'SIMPLE'),   # 116 — 'SIMPLE'/'CURVE'
            g('ps_alpha_mode',                'SIMPLE'),   # 117
            g('ps_size_mode',                 'SIMPLE'),   # 118
            g('ps_bb_facing',                 'CAM_ROT'),  # 119 — 'CAM_ROT'/'LOOK_AT'
            # Sub-Emitter
            g('ps_sub_emitter_enabled',       False),      # 120
            g('ps_sub_emitter',               ' '),         # 121 — name of sub-emitter object (' ' = none)
            g('ps_sub_emitter_inherit_vel',   False),      # 122
            g('ps_sub_birth_enabled',         False),      # 123
            g('ps_sub_birth',                 ' '),         # 124
            g('ps_sub_birth_inherit_vel',     False),      # 125
            g('ps_sub_coll_enabled',          False),      # 126
            g('ps_sub_coll',                  ' '),         # 127
            g('ps_sub_coll_inherit_vel',      False),      # 128
        )

    def _build_props_from_raw(self, r):
        '''Unpack raw tuple into structured props dict.
        Only called when a change is detected — not every frame.'''
        self.props = {
            'enabled':                r[0],
            'trigger':                r[1],
            'emission_mode':          r[2],
            'emission_shape':         r[3],
            'emission_box_size':     (r[4],  r[5],  r[6]),
            'emission_sphere_radius': r[7],
            'emission_cone_radius':   r[8],
            'emission_cone_height':   r[9],
            'emission_ring_radius':   r[109],
            'emission_ring_width':    r[110],
            'max_particles':          r[10],
            'emission_rate':          r[11],
            'emission_delay':         r[12],
            'burst_count':            r[13],
            'is_one_shot':            r[14],
            'lifetime':               r[15],
            'lifetime_random':        r[16],
            'start_size':             r[17],
            'end_size':               r[18],
            'start_velocity':        (r[19], r[20], r[21]),
            'velocity_random':        r[22],
            'enable_gravity':         r[23],
            'gravity_power':          r[24],
            'particle_mesh':          r[25],
            'simulation_space':       r[26],
            'parent_with_emitter':    r[27],
            'movement_type':          r[28],
            'force':                 (r[29], r[30], r[31]),
            'torque':                (r[32], r[33], r[34]),
            'drag_enabled':           r[35],
            'drag_start':             r[36],
            'drag_end':               r[37],
            'resistance':             r[38],
            'enable_collision':       r[39],
            'bounce_strength':        r[40],
            'stop_on_collision':      r[41],
            'rotation':              (r[42], r[43], r[44]),
            'particle_type':          r[45],
            'billboard_template':     r[46],
            'color_start':           (r[47], r[48], r[49]),
            'color_end':             (r[50], r[51], r[52]),
            'color_start_time':       r[53],
            'color_end_time':         r[54],
            'start_alpha':            r[55],
            'end_alpha':              r[56],
            'alpha_start_time':       r[57],
            'alpha_end_time':         r[58],
            'enable_color':           r[59],
            'enable_alpha':           r[60],
            'enable_turbulence':      r[61],
            'turb_strength':          r[62],
            'turb_frequency':         r[63],
            'turb_speed':             r[64],
            'enable_lod':             r[65],
            'lod_start':              r[66],
            'lod1_dist':              r[67],
            'lod1_max':               r[68],
            'lod1_rate':              r[69],
            'lod1_burst':             r[70],
            'lod1_no_turb':           r[71],
            'lod1_no_coll':           r[72],
            'lod1_no_emit':           r[73],
            'lod1_destroy':           r[74],
            'lod2_dist':              r[75],
            'lod2_max':               r[76],
            'lod2_rate':              r[77],
            'lod2_burst':             r[78],
            'lod2_no_turb':           r[79],
            'lod2_no_coll':           r[80],
            'lod2_no_emit':           r[81],
            'lod2_destroy':           r[82],
            'lod3_dist':              r[83],
            'lod3_max':               r[84],
            'lod3_rate':              r[85],
            'lod3_burst':             r[86],
            'lod3_no_turb':           r[87],
            'lod3_no_coll':           r[88],
            'lod3_no_emit':           r[89],
            'lod3_destroy':           r[90],
            # System Launcher
            'launcher_enabled':       r[91],
            'launcher_dist':          r[92],
            'launcher_prewarm':       r[93],
            # Orbit
            'orbit_center':           r[94],
            'orbit_axis_x':           r[95],
            'orbit_axis_y':           r[96],
            'orbit_axis_z':           r[97],
            'orbit_speed':            r[98],
            'orbit_speed_random':     r[99],
            'orbit_radius':           r[100],
            'orbit_radius_random':    r[101],
            'orbit_axis_inverse':     r[102],
            'orbit_tilt':                   r[111],
            'emit_from':                    r[112],
            'emission_hemisphere_radius':   r[113],
            'emission_cone_base_radius':    r[114],
            # Billboard Roll
            'bb_roll_enabled':        r[103],
            'bb_roll_speed':          r[104],
            'bb_roll_random':         r[105],
            'color_curve':            r[106],
            'size_curve':             r[107],
            'alpha_curve':            r[108],
            # LOD level count and mode flags
            'lod_levels':             r[115],
            'color_mode':             r[116],
            'alpha_mode':             r[117],
            'size_mode':              r[118],
            # Billboard facing method
            'bb_facing':              r[119],
            # Sub-Emitter
            'sub_emitter_enabled':    r[120],
            'sub_emitter':            r[121],
            'sub_emitter_inherit_vel': r[122],
            'sub_birth_enabled':      r[123],
            'sub_birth':              r[124],
            'sub_birth_inherit_vel':  r[125],
            'sub_coll_enabled':       r[126],
            'sub_coll':               r[127],
            'sub_coll_inherit_vel':   r[128],
        }

    def load_properties(self):
        '''Full load on first call — reads and caches all properties.'''
        raw = self._read_raw_props()
        self._props_raw = raw
        self._build_props_from_raw(raw)

    def sync_properties(self):
        '''Called every frame. Compares a single tuple — only rebuilds props dict
        if something actually changed. Zero dict allocation on stable frames.
        Returns True if props changed (so caller can recache frame constants).'''
        raw = self._read_raw_props()
        if raw == self._props_raw:
            return False        # Nothing changed — skip everything
        self._props_raw = raw
        self._build_props_from_raw(raw)
        return True

    def _cache_frame_constants(self, dt):
        '''Hoist props that are constant for all particles this frame.
        Called once per update() instead of once per particle.'''
        p = self.props
        self._is_local            = (p['simulation_space'] == 'LOCAL')
        self._parent_with_emitter = p['parent_with_emitter'] and self._is_local
        self._is_force   = (p['movement_type']    == 'FORCE')
        self._lifetime        = p['lifetime']
        self._lifetime_random = p['lifetime_random']
        sv = p['start_velocity']
        self._start_velocity  = (sv[0], sv[1], sv[2])  # tuple copy
        self._velocity_random = p['velocity_random']
        self._emission_shape  = p['emission_shape']
        self._size_start = p['start_size']
        self._size_delta = p['end_size'] - p['start_size']
        self._size_curve = self._parse_curve(p.get('size_curve', ''))
        self._enable_collision  = p['enable_collision']
        self._bounce            = p['bounce_strength']
        self._stop_on_collision = p['stop_on_collision']

        grav_z = p['gravity_power'] if p['enable_gravity'] else 0.0
        grav_w = Vector((0.0, 0.0, grav_z))

        if self._is_force:
            force_t = p['force']
            force_w = Vector(force_t)
            if p['drag_enabled']:
                self._drag_start  = p['drag_start']
                self._drag_end    = p['drag_end']
                self._resistance  = p['resistance']
            else:
                self._drag_start  = 0.0
                self._drag_end    = 0.0
                self._resistance  = 1.0
            if self._is_local:
                ori = self.emitter.worldOrientation
                self._acc_per_sec = ori @ force_w + ori @ grav_w
            else:
                self._acc_per_sec = force_w + grav_w
            self._acc = self._acc_per_sec * dt
            # Pre-convert torque to radians/sec² — store per-sec so dt can be reapplied cheaply
            torq = p['torque']
            self._torque_per_sec = Vector((_radians(torq[0]),
                                           _radians(torq[1]),
                                           _radians(torq[2])))
            self._torque_rad = self._torque_per_sec * dt
        else:
            self._drag_start = 0.0
            self._drag_end   = 0.0
            self._resistance = 1.0
            if self._is_local:
                ori = self.emitter.worldOrientation
                self._acc_per_sec = ori @ grav_w
            else:
                self._acc_per_sec = grav_w.copy()
            self._acc = self._acc_per_sec * dt

        # Pre-convert SIMPLE rotation speed to rad/frame-unit (divided by lifetime
        # later per particle, but store the radians part now)
        rot = p['rotation']
        self._rot_has_value = (rot[0] != 0.0 or rot[1] != 0.0 or rot[2] != 0.0)
        self._rot_rad = Vector((_radians(rot[0]),
                                _radians(rot[1]),
                                _radians(rot[2])))

        # Pre-check torque for FORCE mode — if all zero, skip worldOrientation writes
        torq_vals = p['torque']
        self._has_torque = (torq_vals[0] != 0.0 or torq_vals[1] != 0.0 or torq_vals[2] != 0.0)

        # Billboard mode flag
        self._is_billboard = (p['particle_type'] == 'BILLBOARD')

        # Color over lifetime
        self._enable_color     = p['enable_color']
        self._color_start      = p['color_start']
        self._color_end        = p['color_end']
        # Parse baked curve samples (comma-sep floats). Non-empty = Curve mode.
        self._color_curve = self._parse_curve(p.get('color_curve', ''))
        # Curve mode spans the full lifetime (0→1); From/To only used in Simple mode
        if self._color_curve:
            self._color_t_start = 0.0
            self._color_t_end   = 1.0
        else:
            self._color_t_start = p['color_start_time'] / 10.0
            self._color_t_end   = max(p['color_end_time'] / 10.0, self._color_t_start + 0.0001)

        # Alpha over lifetime
        self._enable_alpha   = p['enable_alpha']
        self._start_alpha    = p['start_alpha']
        self._end_alpha      = p['end_alpha']
        self._alpha_curve = self._parse_curve(p.get('alpha_curve', ''))
        # Curve mode spans full lifetime — From/To only used in Simple
        if self._alpha_curve:
            self._alpha_t_start = 0.0
            self._alpha_t_end   = 1.0
        else:
            self._alpha_t_start  = p['alpha_start_time'] / 10.0
            self._alpha_t_end    = max(p['alpha_end_time'] / 10.0, self._alpha_t_start + 0.0001)

        # Turbulence settings
        self._turb_enabled   = p['enable_turbulence']
        self._turb_strength  = p['turb_strength']
        self._turb_frequency = p['turb_frequency']
        self._turb_speed     = p['turb_speed']

        # LOD settings — cache the full table once per props change
        self._lod_enabled  = p['enable_lod']
        self._lod_start    = p['lod_start']
        self._lod_table    = (
            # (dist, max_p, rate, burst, no_turb, no_coll, no_emit, destroy)
            (p['lod1_dist'], p['lod1_max'], p['lod1_rate'], p['lod1_burst'],
             p['lod1_no_turb'],  p['lod1_no_coll'], p['lod1_no_emit'], p['lod1_destroy']),
            (p['lod2_dist'], p['lod2_max'], p['lod2_rate'], p['lod2_burst'],
             p['lod2_no_turb'],  p['lod2_no_coll'], p['lod2_no_emit'], p['lod2_destroy']),
            (p['lod3_dist'], p['lod3_max'], p['lod3_rate'], p['lod3_burst'],
             p['lod3_no_turb'],  p['lod3_no_coll'], p['lod3_no_emit'], p['lod3_destroy']),
        )

        # System Launcher settings
        self._launcher_enabled = p['launcher_enabled']
        self._launcher_dist    = p['launcher_dist']
        self._launcher_prewarm = p['launcher_prewarm']
        # Precompute the active threshold once — avoids a tuple index lookup every frame.
        # When LOD is on: last *active* LOD level distance. When LOD is off: manual launcher dist.
        self._lod_levels_count = int(p.get('lod_levels', '3'))
        if self._lod_enabled:
            self._launcher_active_thresh = self._lod_table[self._lod_levels_count - 1][0]
        else:
            self._launcher_active_thresh = self._launcher_dist

        # Orbit — precompute axis vector and mode flags once per props change.
        # The axis vector is the normalized sum of the enabled XYZ booleans.
        # Fallback to Z if none are selected to avoid zero-vector division.
        self._is_orbit          = (p['movement_type'] == 'ORBIT')
        self._orbit_use_emitter = (p['orbit_center'] == 'EMITTER')
        ax = 1.0 if p['orbit_axis_x'] else 0.0
        ay = 1.0 if p['orbit_axis_y'] else 0.0
        az = 1.0 if p['orbit_axis_z'] else 0.0
        mag = (ax * ax + ay * ay + az * az) ** 0.5
        if mag < 0.0001:
            az = 1.0; mag = 1.0   # fallback: Z
        sign  = -1.0 if p['orbit_axis_inverse'] else 1.0
        axis  = Vector((sign * ax / mag, sign * ay / mag, sign * az / mag))
        # Tilt: rotate the axis itself around a perpendicular vector.
        # Rodrigues (rot ⊥ axis, so axis·rot = 0):
        #   axis' = axis·cos(θ) + (rot × axis)·sin(θ)
        tilt_deg = p.get('orbit_tilt', 0.0)
        if tilt_deg != 0.0:
            theta = tilt_deg * (_pi / 180.0)
            ref   = Vector((0.0, 1.0, 0.0)) if abs(axis.y) < 0.9 else Vector((1.0, 0.0, 0.0))
            rot   = ref - ref.dot(axis) * axis
            r_len = (rot.x*rot.x + rot.y*rot.y + rot.z*rot.z) ** 0.5
            if r_len > 0.0001:
                rot /= r_len
            ct = _cos(theta); st = _sin(theta)
            cr = rot.cross(axis)
            axis = Vector((axis.x * ct + cr.x * st,
                            axis.y * ct + cr.y * st,
                            axis.z * ct + cr.z * st))
            a_len = (axis.x*axis.x + axis.y*axis.y + axis.z*axis.z) ** 0.5
            if a_len > 0.0001:
                axis /= a_len
        self._orbit_axis_vec  = axis
        self._orbit_tilt_rad  = tilt_deg * (_pi / 180.0)
        # Pre-build the orbit plane basis vectors once per props change.
        # emit_particle uses these directly instead of rebuilding per spawn.
        _ref = Vector((0.0, 1.0, 0.0)) if abs(axis.y) < 0.9 else Vector((1.0, 0.0, 0.0))
        _u   = _ref - _ref.dot(axis) * axis
        _ul  = (_u.x*_u.x + _u.y*_u.y + _u.z*_u.z) ** 0.5
        if _ul > 0.0001:
            _u /= _ul
        self._orbit_basis_u = _u
        self._orbit_basis_v = axis.cross(_u)
        # Orbit emission attrs -- cached so emit_particle skips dict lookups
        self._orbit_radius          = p['orbit_radius']
        self._orbit_radius_random   = p['orbit_radius_random']
        self._orbit_speed_val       = p['orbit_speed']
        self._orbit_speed_random    = p['orbit_speed_random']

        # Billboard Roll — precompute once per props change
        self._bb_roll_enabled = p['bb_roll_enabled']
        self._bb_roll_speed   = p['bb_roll_speed']
        self._bb_roll_random  = p['bb_roll_random']

        # Billboard facing method — 'CAM_ROT' copies camera matrix, 'LOOK_AT' per-particle 3D
        self._bb_facing = p.get('bb_facing', 'CAM_ROT')

        # Sub-Emitter — name looked up in ParticleManager.systems at event time
        self._sub_emitter_enabled     = p.get('sub_emitter_enabled',    False)
        self._sub_emitter_name        = p.get('sub_emitter',            ' ').strip()
        self._sub_emitter_inherit_vel = p.get('sub_emitter_inherit_vel', False)
        self._sub_birth_enabled       = p.get('sub_birth_enabled',      False)
        self._sub_birth_name          = p.get('sub_birth',              ' ').strip()
        self._sub_birth_inherit_vel   = p.get('sub_birth_inherit_vel',  False)
        self._sub_coll_enabled        = p.get('sub_coll_enabled',       False)
        self._sub_coll_name           = p.get('sub_coll',               ' ').strip()
        self._sub_coll_inherit_vel    = p.get('sub_coll_inherit_vel',   False)

    # ------------------------------------------------------------------
    # Turbulence noise
    # ------------------------------------------------------------------
    @staticmethod
    def _value_noise3(x, y, z):
        ix, iy, iz = int(x) & 255, int(y) & 255, int(z) & 255
        fx, fy, fz = x - int(x), y - int(y), z - int(z)
        ux = fx * fx * (3.0 - 2.0 * fx)
        uy = fy * fy * (3.0 - 2.0 * fy)
        uz = fz * fz * (3.0 - 2.0 * fz)
        def h(a, b, c):
            n = (a * 1619 + b * 31337 + c * 6971) & 0x7fffffff
            n = (n >> 13) ^ n
            return ((n * (n * n * 60493 + 19990303) + 1376312589) & 0x7fffffff) / 1073741824.0 - 1.0
        def lerp(a, b, t): return a + t * (b - a)
        return lerp(
            lerp(lerp(h(ix,iy,iz),   h(ix+1,iy,iz),   ux),
                 lerp(h(ix,iy+1,iz), h(ix+1,iy+1,iz), ux), uy),
            lerp(lerp(h(ix,iy,iz+1),   h(ix+1,iy,iz+1),   ux),
                 lerp(h(ix,iy+1,iz+1), h(ix+1,iy+1,iz+1), ux), uy),
            uz)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_curve(raw):
        # Parse comma-separated floats into a list.
        # Returns None for Simple mode (blank/whitespace-only value).
        if not raw or not raw.strip():
            return None
        try:
            return [float(v) for v in raw.split(',')]
        except Exception:
            return None
    # Pool management
    # ------------------------------------------------------------------
    def create_particle_template(self):
        scene = logic.getCurrentScene()
        particle_type = self.props.get('particle_type', 'MESH')

        if particle_type == 'BILLBOARD':
            # Read the per-emitter template name stored by the addon at init time
            billboard_name = self.props.get('billboard_template', '')
            if billboard_name and billboard_name in scene.objectsInactive:
                self.particle_template = scene.objectsInactive[billboard_name]
                print(f"✓ Billboard template: {billboard_name}")
            else:
                print(f"✗ Billboard: template '{billboard_name}' not in objectsInactive. Re-initialize the emitter.")
        else:
            mesh_name = self.props.get('particle_mesh', 'ParticleSphere')
            if mesh_name in scene.objectsInactive:
                self.particle_template = scene.objectsInactive[mesh_name]
                print(f"✓ Template: {mesh_name}")
            else:
                print(f"✗ ERROR: '{mesh_name}' not in objectsInactive!")

    def initialize_pool(self):
        if not self.particle_template:
            return
        scene = logic.getCurrentScene()
        max_p = self.props['max_particles']
        print(f"Creating particle pool: {max_p} particles...")
        zero3 = [0.0, 0.0, 0.0]
        for i in range(max_p):
            p = Particle()
            try:
                p.obj = scene.addObject(self.particle_template, self.emitter, 0)
                p.obj.worldScale = zero3
                p.obj.visible = False
            except Exception as e:
                print(f"Pool creation error: {e}")
                continue
            p.pool_idx = i
            self.particle_pool.append(p)
            self.inactive_stack.append(i)   # All start inactive
        print(f"✓ Pool ready: {len(self.particle_pool)} particles")

    def get_inactive_particle(self):
        '''O(1) pop from inactive stack instead of O(n) linear scan'''
        if self.inactive_stack:
            return self.particle_pool[self.inactive_stack.pop()]
        return None

    def deactivate_particle(self, p):
        '''Hide particle and return its index to the free stack in O(1).
        If a sub-emitter is configured, fires a burst at the particle's death position.'''
        # Capture position before zeroing the object — used for sub-emitter spawn
        death_pos = p.position.copy() if self._sub_emitter_enabled else None
        death_vel = p.velocity.copy() if (self._sub_emitter_enabled and self._sub_emitter_inherit_vel) else None

        p.is_active  = False
        p.is_stopped = False
        if p.obj:
            p.obj.worldScale = [0.0, 0.0, 0.0]
            p.obj.visible = False
        self.inactive_stack.append(p.pool_idx)

        # Sub-emitter: burst from the death position
        if self._sub_emitter_enabled and self._sub_emitter_name and self._sub_emitter_name.strip() and death_pos is not None:
            try:
                pm = logic._pm
                sub_sys = pm.systems.get(self._sub_emitter_name)
                if sub_sys is not None:
                    sub_sys.emit_burst_at(death_pos, extra_vel=death_vel)
            except Exception:
                pass  # Never let sub-emitter errors kill the parent system

    # ------------------------------------------------------------------
    # Emission
    # ------------------------------------------------------------------
    def emit_particle(self, override_pos=None, extra_vel=None):
        p = self.get_inactive_particle()
        if not p:
            return

        emission_shape  = self._emission_shape
        emitter_pos     = self.emitter.worldPosition
        emitter_ori     = self.emitter.worldOrientation
        spawn_local_offset = Vector((0.0, 0.0, 0.0))
        emit_from = self.props.get('emit_from', 'VOLUME')

        if emission_shape == 'BOX':
            bx, by, bz = self.props['emission_box_size']
            if emit_from == 'SURFACE':
                axis = int(_random() * 3)
                side = 1.0 if _random() < 0.5 else -1.0
                half = (bx * 0.5, by * 0.5, bz * 0.5)
                coords = [(_random() - 0.5) * bx,
                          (_random() - 0.5) * by,
                          (_random() - 0.5) * bz]
                coords[axis] = side * half[axis]
                spawn_local_offset = Vector(coords)
            else:  # VOLUME
                spawn_local_offset = Vector((
                    (_random() - 0.5) * bx,
                    (_random() - 0.5) * by,
                    (_random() - 0.5) * bz,
                ))
            if self._is_local:
                spawn_pos = emitter_pos + (emitter_ori @ spawn_local_offset)
            else:
                spawn_pos = emitter_pos + spawn_local_offset

        elif emission_shape == 'SPHERE':
            radius = self.props['emission_sphere_radius']
            theta  = 2.0 * _pi * _random()
            phi    = _acos(2.0 * _random() - 1.0)
            sin_phi = _sin(phi)
            if emit_from == 'SURFACE':
                r = radius
            else:  # VOLUME
                r = radius * (_random() ** (1.0 / 3.0))
            spawn_local_offset = Vector((
                r * sin_phi * _cos(theta),
                r * sin_phi * _sin(theta),
                r * _cos(phi),
            ))
            if self._is_local:
                spawn_pos = emitter_pos + (emitter_ori @ spawn_local_offset)
            else:
                spawn_pos = emitter_pos + spawn_local_offset

        elif emission_shape == 'HEMISPHERE':
            radius  = self.props['emission_hemisphere_radius']
            theta   = 2.0 * _pi * _random()
            cos_phi = _random()          # uniform in [0,1] → upper hemisphere only
            sin_phi = _sqrt(1.0 - cos_phi * cos_phi)
            if emit_from == 'SURFACE':
                r = radius
            else:  # VOLUME
                r = radius * (_random() ** (1.0 / 3.0))
            spawn_local_offset = Vector((
                r * sin_phi * _cos(theta),
                r * sin_phi * _sin(theta),
                r * cos_phi,
            ))
            if self._is_local:
                spawn_pos = emitter_pos + (emitter_ori @ spawn_local_offset)
            else:
                spawn_pos = emitter_pos + spawn_local_offset

        elif emission_shape == 'CONE':
            cone_r  = self.props['emission_cone_radius']
            cone_h  = self.props['emission_cone_height']
            cone_br = self.props['emission_cone_base_radius']
            if emit_from == 'BASE':
                base_r = cone_br if cone_br > 0.0 else cone_r
                r      = base_r * _sqrt(_random())
                angle  = _random() * 2.0 * _pi
                spawn_local_offset = Vector((r * _cos(angle), r * _sin(angle), 0.0))
            elif emit_from == 'SURFACE':
                h_frac = _sqrt(_random())
                r      = cone_r * h_frac
                angle  = _random() * 2.0 * _pi
                spawn_local_offset = Vector((
                    r * _cos(angle),
                    r * _sin(angle),
                    cone_h * h_frac,
                ))
            else:  # VOLUME
                h_frac = _random()
                r_max  = cone_r * h_frac
                r      = r_max * _sqrt(_random())
                angle  = _random() * 2.0 * _pi
                spawn_local_offset = Vector((
                    r * _cos(angle),
                    r * _sin(angle),
                    cone_h * h_frac,
                ))
            if self._is_local:
                spawn_pos = emitter_pos + (emitter_ori @ spawn_local_offset)
            else:
                spawn_pos = emitter_pos + spawn_local_offset

        elif emission_shape == 'RING':
            ring_r = self.props['emission_ring_radius']
            ring_w = self.props['emission_ring_width']
            angle  = _random() * 2.0 * _pi
            r      = ring_r + (_random() - 0.5) * ring_w
            spawn_local_offset = Vector((r * _cos(angle), r * _sin(angle), 0.0))
            if self._is_local:
                spawn_pos = emitter_pos + (emitter_ori @ spawn_local_offset)
            else:
                spawn_pos = emitter_pos + spawn_local_offset

        else:  # POINT
            spawn_pos = emitter_pos.copy()

        # Velocity
        vr = self._velocity_random
        sv = self._start_velocity
        local_vel = Vector((
            sv[0] + (_random() - 0.5) * 2.0 * vr,
            sv[1] + (_random() - 0.5) * 2.0 * vr,
            sv[2] + (_random() - 0.5) * 2.0 * vr,
        ))
        world_vel = (emitter_ori @ local_vel) if self._is_local else local_vel
        # Parent mode uses local-space velocity so local_offset integrates correctly
        spawn_vel = local_vel if self._parent_with_emitter else world_vel

        lifetime = self._lifetime * (1.0 + (_random() - 0.5) * self._lifetime_random)

        # Sub-emitter override: replace spawn position and optionally add inherited velocity
        if override_pos is not None:
            spawn_pos = override_pos
        if extra_vel is not None:
            spawn_vel = spawn_vel + extra_vel

        # Reset particle state
        p.position.x = spawn_pos.x; p.position.y = spawn_pos.y; p.position.z = spawn_pos.z
        p.velocity.x = spawn_vel.x; p.velocity.y = spawn_vel.y; p.velocity.z = spawn_vel.z
        p.local_offset.x = spawn_local_offset.x
        p.local_offset.y = spawn_local_offset.y
        p.local_offset.z = spawn_local_offset.z
        p.age      = 0.0
        p.lifetime = lifetime
        p.size     = self._size_start
        p.rotation.x = 0.0; p.rotation.y = 0.0; p.rotation.z = 0.0
        p.angular_velocity.x = 0.0; p.angular_velocity.y = 0.0; p.angular_velocity.z = 0.0
        p.roll_angle = 0.0
        p.is_stopped = False
        p.roll_speed = (self._bb_roll_speed
                        + (_random() - 0.5) * 2.0 * self._bb_roll_random) * 2.0 * _pi
        p.is_active = True

        # Orbit — compute per-particle state at spawn.
        # Center is baked at spawn (emitter pos or world origin).
        # Radius comes from the orbit_radius prop + random variance —
        # NOT from spawn offset, which is zero for POINT/CONE and would freeze particles.
        # Basis vectors U/V span the orbit plane perpendicular to the axis (Gram-Schmidt).
        if self._is_orbit:
            center = self.emitter.worldPosition.copy() if self._orbit_use_emitter else Vector((0.0, 0.0, 0.0))
            # Zero velocity — orbit uses it solely as a gravity drift accumulator
            p.velocity.x = 0.0; p.velocity.y = 0.0; p.velocity.z = 0.0
            p.orbit_center.x = center.x
            p.orbit_center.y = center.y
            p.orbit_center.z = center.z

            # Use pre-built basis vectors from _cache_frame_constants (no per-spawn Gram-Schmidt)
            u = self._orbit_basis_u
            v = self._orbit_basis_v
            p.orbit_basis_u.x = u.x; p.orbit_basis_u.y = u.y; p.orbit_basis_u.z = u.z
            p.orbit_basis_v.x = v.x; p.orbit_basis_v.y = v.y; p.orbit_basis_v.z = v.z

            # Radius: use cached prop + random variance
            p.orbit_radius = max(
                self._orbit_radius + (_random() - 0.5) * 2.0 * self._orbit_radius_random,
                0.001)

            # Initial angle from spawn offset projected onto orbit plane
            offset = spawn_pos - center
            du = offset.dot(u)
            dv = offset.dot(v)
            p.orbit_angle = _atan2(dv, du) if (du*du + dv*dv) > 0.0001 else 0.0

            p.orbit_speed = (self._orbit_speed_val
                             + (_random() - 0.5) * 2.0 * self._orbit_speed_random)

        if p.obj:
            p.obj.worldPosition = spawn_pos
            s = self._size_start
            p.obj.worldScale = [s, s, s]
            p.obj.visible = True

        # Sub-emitter On Birth: burst at the spawn position of the new particle
        if self._sub_birth_enabled and self._sub_birth_name:
            try:
                sub_sys = logic._pm.systems.get(self._sub_birth_name)
                if sub_sys is not None:
                    birth_vel = spawn_vel.copy() if self._sub_birth_inherit_vel else None
                    sub_sys.emit_burst_at(spawn_pos, extra_vel=birth_vel)
            except Exception:
                pass

    def _emit_burst_lod(self, burst_count, max_particles):
        active_count = len(self.particle_pool) - len(self.inactive_stack)
        slots_free   = max(0, max_particles - active_count)
        count        = min(burst_count, slots_free)
        for _ in range(count):
            self.emit_particle()

    def emit_burst_at(self, pos, extra_vel=None):
        '''Spawn a burst of particles centred on `pos` (world space).
        Called by a parent system's deactivate_particle when sub-emitter is enabled.
        Respects the sub-emitter's own burst_count and max_particles cap.'''
        burst_count  = self.props.get('burst_count',  1)
        max_particles = self.props.get('max_particles', 100)
        active_count = len(self.particle_pool) - len(self.inactive_stack)
        slots_free   = max(0, max_particles - active_count)
        count        = min(burst_count, slots_free)
        for _ in range(count):
            self.emit_particle(override_pos=pos, extra_vel=extra_vel)

    # ------------------------------------------------------------------
    # Main update
    # ------------------------------------------------------------------
    def update(self, dt):
        prev_mesh = self.props.get('particle_mesh')
        prev_type = self.props.get('particle_type')

        # Sync properties only if a game property actually changed this frame.
        # On stable frames this costs one tuple comparison and nothing else.
        props_changed = self.sync_properties()

        # Particle type or mesh change: destroy pool and rebuild with new template
        type_changed = self.props.get('particle_type') != prev_type
        mesh_changed = self.props.get('particle_mesh') != prev_mesh
        if type_changed or mesh_changed:
            scene = logic.getCurrentScene()
            for p in self.particle_pool:
                if p.is_active:
                    self.deactivate_particle(p)
                try:
                    p.obj.endObject()
                except Exception:
                    pass
            self.particle_pool    = []
            self.inactive_stack   = []
            self.create_particle_template()
            self.initialize_pool()

        # Recache frame constants when props changed or on the first frame.
        # On stable frames only rescale the dt-dependent acceleration vectors.
        if props_changed or self._first_frame:
            self._cache_frame_constants(dt)
            self._first_frame = False
        else:
            self._acc = self._acc_per_sec * dt
            if self._is_force:
                self._torque_rad = self._torque_per_sec * dt

        props = self.props

        # One scene/camera fetch per update() call, shared by launcher, LOD, and billboard.
        _frame_scene = logic.getCurrentScene()
        _frame_cam   = _frame_scene.active_camera  # may be None if no camera in scene

        # ── System Launcher ────────────────────────────────────────────
        # Outer gate: controls whether the pool exists at all.
        # States: INACTIVE (beyond prewarm) → PREWARM (pool exists, silent)
        #                                   → ACTIVE (emitting normally)
        # On exit back past prewarm the pool is torn down to free VRAM.
        # When LOD is enabled, the Active threshold is lod_start so the two
        # systems hand off cleanly — LOD manages quality within the active zone.
        if self._launcher_enabled:
            if _frame_cam:
                dist = (self.emitter.worldPosition - _frame_cam.worldPosition).length
                prev_launcher_state = self._launcher_state

                # Decide the new state based purely on distance.
                # Both thresholds are precomputed in _cache_frame_constants --
                # plain float reads, zero computation here.
                active_thresh  = self._launcher_active_thresh
                prewarm_thresh = self._launcher_prewarm

                if dist <= active_thresh:
                    new_state = 'ACTIVE'
                elif dist <= prewarm_thresh:
                    new_state = 'PREWARM'
                else:
                    new_state = 'INACTIVE'

                # State transitions
                if new_state != prev_launcher_state:
                    if new_state in ('PREWARM', 'ACTIVE') and not self._pool_built:
                        self.create_particle_template()
                        self.initialize_pool()
                        self._pool_built = True

                    elif new_state == 'INACTIVE' and self._pool_built:
                        # Leaving prewarm -- tear down pool to free VRAM
                        for p in self.particle_pool:
                            if p.is_active:
                                self.deactivate_particle(p)
                            try:
                                p.obj.endObject()
                            except Exception as e:
                                print(f'endObject error: {e}')
                        self.particle_pool  = []
                        self.inactive_stack = []
                        self._pool_built     = False
                        self.burst_triggered = False
                        self.time_since_emit = 0.0
                        self._lod_level      = 0

                    elif new_state == 'ACTIVE' and prev_launcher_state == 'INACTIVE':
                        if not self._pool_built:
                            self.create_particle_template()
                            self.initialize_pool()
                            self._pool_built = True

                self._launcher_state = new_state

                if new_state != 'ACTIVE':
                    return
        # ── end System Launcher ────────────────────────────────────────

        # ── LOD evaluation ----------------------------------------------------------
        # Runs once per update() -- O(1) distance check against active camera.
        lod_max_particles = props['max_particles']   # default: main setting
        lod_emission_rate = props['emission_rate']
        lod_burst_count   = props['burst_count']
        lod_no_turb       = False
        lod_no_coll       = False
        lod_no_emit       = False
        lod_destroy       = False
        prev_lod_level    = self._lod_level

        if self._lod_enabled and _frame_cam:
            dist = (self.emitter.worldPosition - _frame_cam.worldPosition).length
            if dist <= self._lod_start:
                self._lod_level = 0
            else:
                self._lod_level = 0
                # Only iterate up to the configured number of LOD levels
                active_table = self._lod_table[:self._lod_levels_count]
                for lvl_idx, (lvl_dist, lvl_max, lvl_rate, lvl_burst,
                              lvl_no_turb, lvl_ncoll, lvl_ne, lvl_destroy) in enumerate(active_table):
                    if dist >= lvl_dist:
                        self._lod_level = lvl_idx + 1
                        lod_no_turb     = lvl_no_turb
                        lod_no_coll     = lvl_ncoll
                        lod_no_emit     = lvl_ne
                        lod_destroy     = lvl_destroy
                        # Max particles/rate/burst irrelevant when emitting disabled
                        if not lvl_ne:
                            lod_max_particles = lvl_max
                            lod_emission_rate = lvl_rate
                            lod_burst_count   = lvl_burst

            # Destroy particles when entering a new LOD level that requests it
            if lod_destroy and self._lod_level != prev_lod_level:
                for p in self.particle_pool:
                    if p.is_active:
                        self.deactivate_particle(p)
        # ── end LOD ────────────────────────────────────────────────

        # Advance turbulence time once per frame
        if self._turb_enabled:
            self._turb_time += dt * self._turb_speed

        # Spawn logic — LOD overrides max_particles, rate and burst_count
        if props['enabled'] and not lod_no_emit:
            mode    = props['emission_mode']
            trigger = props['trigger']

            if mode == 'CONTINUOUS':
                if trigger:
                    self.time_since_emit += dt
                    rate = lod_emission_rate
                    interval = 1.0 / rate if rate > 0 else float('inf')
                    while self.time_since_emit >= interval:
                        # Respect LOD max_particles soft cap
                        active_count = len(self.particle_pool) - len(self.inactive_stack)
                        if active_count < lod_max_particles:
                            self.emit_particle()
                        self.time_since_emit -= interval

            elif mode == 'BURST':
                if props['is_one_shot']:
                    if trigger and not self.burst_triggered:
                        self._emit_burst_lod(lod_burst_count, lod_max_particles)
                        self.burst_triggered = True
                    elif not trigger:
                        self.burst_triggered = False
                else:
                    if trigger:
                        self.time_since_emit += dt
                        if self.time_since_emit >= props['emission_delay']:
                            self._emit_burst_lod(lod_burst_count, lod_max_particles)
                            self.time_since_emit = 0.0

        # --- Particle update loop (hot path) ---
        acc              = self._acc
        is_force         = self._is_force
        enable_collision  = self._enable_collision and not lod_no_coll
        bounce            = self._bounce
        stop_on_collision = self._stop_on_collision
        size_start       = self._size_start
        size_delta       = self._size_delta
        size_curve       = self._size_curve   # None = Simple; list = Curve
        rot_has_value    = self._rot_has_value
        is_billboard     = self._is_billboard
        emitter_pos      = self.emitter.worldPosition
        emitter_ori      = self.emitter.worldOrientation
        parent_emitter   = self._parent_with_emitter

        if is_force:
            torque_rad   = self._torque_rad

        has_torque   = self._has_torque
        if not is_force and rot_has_value:
            rot_rad = self._rot_rad

        # Hoist billboard camera lookup outside the loop — same camera for all particles this frame
        bb_cam = _frame_cam if is_billboard else None

        # Drag over lifetime locals
        drag_start   = self._drag_start
        drag_end     = self._drag_end
        resistance   = self._resistance
        drag_active  = is_force and (drag_start > 0.0 or drag_end > 0.0)

        # Turbulence locals — hoisted outside loop, LOD can disable it
        turb_enabled   = self._turb_enabled and not lod_no_turb
        turb_strength  = self._turb_strength
        turb_freq      = self._turb_frequency
        turb_time      = self._turb_time
        _noise         = ParticleSystem._value_noise3

        # Orbit locals — hoisted outside loop for zero attribute lookup per particle
        is_orbit         = self._is_orbit
        orbit_two_pi     = 2.0 * _pi

        # Billboard roll + facing locals
        bb_roll_enabled  = self._bb_roll_enabled
        bb_facing        = self._bb_facing          # 'CAM_ROT' | 'LOOK_AT'
        _world_z         = Vector((0.0, 0.0, 1.0))  # used by LOOK_AT gimbal guard

        # Sub-emitter collision locals — hoisted so hot loop avoids attribute lookups
        sub_coll_enabled     = self._sub_coll_enabled
        sub_coll_name        = self._sub_coll_name
        sub_coll_inherit_vel = self._sub_coll_inherit_vel

        # Color & alpha locals — LOD overrides applied on top
        enable_color  = self._enable_color
        color_curve   = self._color_curve   # None = Simple; list = Curve
        enable_alpha  = self._enable_alpha
        color_start   = self._color_start
        color_end     = self._color_end
        color_t_start = self._color_t_start
        color_t_end   = self._color_t_end
        start_alpha   = self._start_alpha
        end_alpha     = self._end_alpha
        alpha_curve   = self._alpha_curve   # None = Simple; list = Curve
        alpha_t_start = self._alpha_t_start
        alpha_t_end   = self._alpha_t_end

        for p in self.particle_pool:
            if not p.is_active:
                continue

            p.age += dt
            if p.age >= p.lifetime:
                self.deactivate_particle(p)
                continue

            # Apply acceleration (gravity + optional force).
            # For orbit mode we skip this — orbit overwrites position directly.
            # Gravity drift along the free axis is handled inside the orbit branch.
            if not p.is_stopped:
                if not is_orbit:
                    p.velocity += acc

                # Drag over lifetime — interpolates Start→End across particle age
                if drag_active:
                    life_r = p.age / p.lifetime
                    p.velocity *= 1.0 - (drag_start + (drag_end - drag_start) * life_r) * resistance * dt

                # Turbulence — sample noise at particle world position
                if turb_enabled:
                    px = p.position.x * turb_freq
                    py = p.position.y * turb_freq
                    pz = p.position.z * turb_freq
                    p.velocity.x += _noise(px,        py,        pz        + turb_time) * turb_strength * dt
                    p.velocity.y += _noise(px + 31.7, py,        pz        + turb_time) * turb_strength * dt
                    p.velocity.z += _noise(px,        py + 57.3, pz        + turb_time) * turb_strength * dt

            # Capture position BEFORE integration so the ray spans exactly
            # the segment the particle travels this frame (fixes one-frame-late
            # detection and the tunneling it caused at high velocities).
            prev_pos = p.position.copy()

            # Position integration — orbit mode drives position directly from
            # angle+radius in the precomputed orbit plane (basis U/V vectors).
            # Non-orbit uses standard velocity integration.
            if is_orbit and not p.is_stopped:
                p.orbit_angle += p.orbit_speed * orbit_two_pi * dt
                a  = p.orbit_angle
                ca = _cos(a); sa = _sin(a)
                r  = p.orbit_radius
                u  = p.orbit_basis_u
                v  = p.orbit_basis_v
                cx = p.orbit_center.x
                cy = p.orbit_center.y
                cz = p.orbit_center.z
                # Pure orbital position from angle+radius in the orbit plane
                p.position.x = cx + r * (ca * u.x + sa * v.x)
                p.position.y = cy + r * (ca * u.y + sa * v.y)
                p.position.z = cz + r * (ca * u.z + sa * v.z)
                # Gravity/force drift: p.velocity accumulates as a drift vector
                # (zeroed at spawn so it starts clean). acc already has dt baked in
                # (_acc = _acc_per_sec * dt), so this is correct Euler: v += a*dt, pos += v*dt.
                p.velocity += acc
                p.position.x += p.velocity.x * dt
                p.position.y += p.velocity.y * dt
                p.position.z += p.velocity.z * dt
            else:
                if parent_emitter:
                    # Reference math from particle_system.py:
                    # velocity integrates into local_offset (local space),
                    # world position is rebuilt from emitter transform every frame.
                    p.local_offset += p.velocity * dt
                    p.position = emitter_pos + (emitter_ori @ p.local_offset)
                else:
                    p.position += p.velocity * dt

            # Collision — ray from pre-integration pos to post-integration pos.
            # rayCast(to, from, dist) — order matters.
            if enable_collision and p.obj:
                distance = p.velocity.length * dt
                if distance > 0:
                    hit_obj, hit_pos, hit_normal = p.obj.rayCast(
                        p.position,  # to   — where the particle arrived
                        prev_pos,    # from — where the particle was
                        distance     # max ray length (one frame of travel)
                    )
                    if hit_obj:
                        if stop_on_collision:
                            p.is_stopped = True
                            p.velocity.x = 0.0; p.velocity.y = 0.0; p.velocity.z = 0.0
                            p.position = hit_pos + hit_normal * 0.005
                        else:
                            dot = p.velocity.dot(hit_normal)
                            p.velocity -= 2.0 * dot * hit_normal
                            p.velocity *= bounce
                            # Push off surface to prevent sinking
                            p.position = hit_pos + hit_normal * 0.02
                        # Sub-emitter On Collision
                        if sub_coll_enabled and sub_coll_name:
                            try:
                                sub_sys = logic._pm.systems.get(sub_coll_name)
                                if sub_sys is not None:
                                    coll_vel = p.velocity.copy() if sub_coll_inherit_vel else None
                                    sub_sys.emit_burst_at(hit_pos, extra_vel=coll_vel)
                            except Exception:
                                pass

            # Write to game object
            obj = p.obj
            if obj:
                obj.worldPosition = p.position
                life_ratio = p.age / p.lifetime
                if size_curve:
                    n1  = len(size_curve) - 1
                    idx = life_ratio * n1
                    lo  = int(idx)
                    hi  = min(lo + 1, n1)
                    t_s = size_curve[lo] + (size_curve[hi] - size_curve[lo]) * (idx - lo)
                    s   = size_start + size_delta * t_s
                else:
                    s = size_start + size_delta * life_ratio
                p.size = s
                obj.worldScale = [s, s, s]

                # Color & alpha — only write obj.color if at least one feature is on,
                # avoiding an unnecessary per-particle dict write when both are disabled.
                if enable_color or enable_alpha:
                    if enable_color:
                        t = (life_ratio - color_t_start) / (color_t_end - color_t_start)
                        t = max(0.0, min(1.0, t))
                        if color_curve:
                            n1  = len(color_curve) - 1
                            idx = t * n1
                            lo  = int(idx)
                            hi  = min(lo + 1, n1)
                            t   = color_curve[lo] + (color_curve[hi] - color_curve[lo]) * (idx - lo)
                        cr = color_start[0] + (color_end[0] - color_start[0]) * t
                        cg = color_start[1] + (color_end[1] - color_start[1]) * t
                        cb = color_start[2] + (color_end[2] - color_start[2]) * t
                    else:
                        cr = cg = cb = 1.0

                    if enable_alpha:
                        t_a = (life_ratio - alpha_t_start) / (alpha_t_end - alpha_t_start)
                        t_a = max(0.0, min(1.0, t_a))
                        if alpha_curve:
                            # Curve mode: Y value IS the alpha — X is lifetime (0→1)
                            n1   = len(alpha_curve) - 1
                            idx  = t_a * n1
                            lo   = int(idx)
                            hi   = min(lo + 1, n1)
                            alpha = alpha_curve[lo] + (alpha_curve[hi] - alpha_curve[lo]) * (idx - lo)
                            alpha = max(0.0, min(1.0, alpha))
                        else:
                            alpha = start_alpha + (end_alpha - start_alpha) * t_a
                    else:
                        alpha = 1.0

                    obj.color = [cr, cg, cb, alpha]

                # Billboard orientation — two methods selectable per emitter:
                #
                # CAM_ROT: copy the camera's own orientation + 90° X correction.
                #   One matrix shared by all particles this frame — cheapest.
                #   Best for flat/uniform effects (sparks, rain, debris).
                #
                # LOOK_AT: per-particle 3D look-at toward the camera position.
                #   Builds right/up/forward from the particle→camera vector.
                #   Slightly more expensive but gives correct depth layering for
                #   volumetric effects like fire and smoke.
                if is_billboard:
                    if bb_cam:
                        if bb_facing == 'LOOK_AT':
                            # Per-particle: build rotation matrix that points
                            # the plane's Y-normal (local forward) at the camera.
                            to_cam = (bb_cam.worldPosition - p.position).normalized()
                            # Gimbal-lock guard: if to_cam is nearly parallel to Z
                            # fall back to Y as the reference up-vector
                            ref   = Vector((0.0, 1.0, 0.0)) if abs(to_cam.dot(_world_z)) > 0.999 else _world_z
                            right = ref.cross(to_cam).normalized()
                            up    = to_cam.cross(right).normalized()
                            # col0=right(X), col1=to_cam(Y/normal), col2=up(Z)
                            base_mat = Matrix((
                                (right.x, to_cam.x, up.x),
                                (right.y, to_cam.y, up.y),
                                (right.z, to_cam.z, up.z),
                            ))
                        else:  # CAM_ROT (default)
                            # Shared matrix: camera orientation + 90° X correction
                            correction = Matrix.Rotation(_pi * 0.5, 3, 'X')
                            base_mat   = bb_cam.worldOrientation.to_3x3() @ correction

                        if bb_roll_enabled:
                            p.roll_angle += p.roll_speed * dt
                            roll_mat = Matrix.Rotation(p.roll_angle, 3, 'Y')
                            obj.worldOrientation = base_mat @ roll_mat
                        else:
                            obj.worldOrientation = base_mat

                # Rotation — only for MESH type, and only when there is actual rotation.
                # worldOrientation triggers an internal matrix decomposition in UPBGE
                # so skipping it when unused saves meaningful cost per particle per frame.
                elif is_force and has_torque:
                    av = p.angular_velocity
                    av += torque_rad
                    if drag_active:
                        life_r = p.age / p.lifetime
                        av *= 1.0 - (drag_start + (drag_end - drag_start) * life_r) * resistance * dt
                    p.rotation += av * dt
                    obj.worldOrientation = [p.rotation.x, p.rotation.y, p.rotation.z]
                elif rot_has_value:
                    speed = rot_rad / p.lifetime
                    p.rotation += speed * dt
                    obj.worldOrientation = [p.rotation.x, p.rotation.y, p.rotation.z]

class ParticleManager:
    def __init__(self):
        self.systems = {}
        self.last_time = 0.0
        print("="*60)
        print("PARTICLE SYSTEM v0.9.0 - OBJECT POOLING")
        print("="*60)

    def scan(self):
        scene = logic.getCurrentScene()
        for obj in scene.objects:
            if 'ps_enabled' in obj:
                if obj.name not in self.systems:
                    self.systems[obj.name] = ParticleSystem(obj)
            elif obj.name in self.systems:
                # POOLING: Clean up pool on removal
                system = self.systems[obj.name]
                for p in system.particle_pool:
                    if p.obj:
                        p.obj.endObject()
                del self.systems[obj.name]

    def update(self):
        cur = logic.getClockTime()
        dt = cur - self.last_time if self.last_time > 0 else 0.016
        self.last_time = cur
        dt = min(dt, 0.1)

        for sys in self.systems.values():
            sys.update(dt)

def init():
    if not hasattr(logic, '_pm'):
        logic._pm = ParticleManager()
        logic.getCurrentScene().pre_draw.append(lambda c: logic._pm.update())
        logic._pm.scan()

init()
"""

        # Script — one shared text block for all emitters in the blend file.
        # If it already exists, every emitter just points its controller at it.
        # We never delete existing text blocks, so initializing a second emitter
        # never breaks the first one's controller reference.
        SHARED_SCRIPT_NAME = "ParticleSys_Runtime.py"
        existing_text = bpy.data.texts.get(SHARED_SCRIPT_NAME)
        if existing_text is None:
            # First time — create the shared script
            existing_text = bpy.data.texts.new(SHARED_SCRIPT_NAME)
            existing_text.write(script_text)
            added.append("Script")
        # Always wire this controller to the shared script
        if controller.text != existing_text:
            controller.text = existing_text

        # Link sensor to controller (safe to call even if already linked)
        sensor = next((s for s in init_obj.game.sensors if s.name == "ParticleInit"), None)
        if sensor:
            controller.link(sensor=sensor)

        # Property Creation - only adds missing props
        def ensure_prop(name, type, value):
            if name not in init_obj.game.properties:
                bpy.ops.object.game_property_new(type=type, name=name)
                init_obj.game.properties[name].value = value
                added.append(f"prop:{name}")

        props = init_obj.particle_system_props

        ensure_prop('ps_enabled', 'BOOL', props.enabled)
        ensure_prop('ps_trigger', 'BOOL', props.trigger_enabled)
        ensure_prop('ps_emission_mode', 'STRING', props.emission_mode)
        ensure_prop('ps_emission_shape', 'STRING', props.emission_shape)
        ensure_prop('ps_emission_sphere_radius', 'FLOAT', props.emission_sphere_radius)
        ensure_prop('ps_emission_hemisphere_radius', 'FLOAT', props.emission_hemisphere_radius)
        ensure_prop('ps_emission_cone_radius',   'FLOAT', props.emission_cone_radius)
        ensure_prop('ps_emission_cone_height',   'FLOAT', props.emission_cone_height)
        ensure_prop('ps_emission_cone_base_radius', 'FLOAT', props.emission_cone_base_radius)
        ensure_prop('ps_emit_from',              'STRING', props.emit_from)
        ensure_prop('ps_emission_ring_radius',   'FLOAT', props.emission_ring_radius)
        ensure_prop('ps_emission_ring_width',    'FLOAT', props.emission_ring_width)
        ensure_prop('ps_max_particles', 'INT', props.max_particles)
        ensure_prop('ps_emission_rate', 'FLOAT', props.emission_rate)
        ensure_prop('ps_emission_delay', 'FLOAT', props.emission_delay)
        ensure_prop('ps_burst_count', 'INT', props.burst_count)
        ensure_prop('ps_is_one_shot', 'BOOL', props.is_one_shot)
        ensure_prop('ps_lifetime', 'FLOAT', props.lifetime)
        ensure_prop('ps_lifetime_random', 'FLOAT', props.lifetime_random)
        ensure_prop('ps_start_size', 'FLOAT', props.start_size)
        ensure_prop('ps_end_size', 'FLOAT', props.end_size)
        ensure_prop('ps_velocity_random', 'FLOAT', props.velocity_random)

        ensure_prop('ps_emission_box_size_x', 'FLOAT', props.emission_box_size[0])
        ensure_prop('ps_emission_box_size_y', 'FLOAT', props.emission_box_size[1])
        ensure_prop('ps_emission_box_size_z', 'FLOAT', props.emission_box_size[2])

        ensure_prop('ps_start_velocity_x', 'FLOAT', props.start_velocity[0])
        ensure_prop('ps_start_velocity_y', 'FLOAT', props.start_velocity[1])
        ensure_prop('ps_start_velocity_z', 'FLOAT', props.start_velocity[2])
        ensure_prop('ps_enable_gravity', 'BOOL',  props.enable_gravity)
        ensure_prop('ps_gravity_power',  'FLOAT', props.gravity_power)

        # Simulation space
        ensure_prop('ps_simulation_space',    'STRING', props.simulation_space)
        ensure_prop('ps_parent_with_emitter', 'BOOL',   props.parent_with_emitter)

        # Collision properties
        ensure_prop('ps_enable_collision',  'BOOL',  props.enable_collision)
        ensure_prop('ps_bounce_strength',   'FLOAT', props.bounce_strength)
        ensure_prop('ps_stop_on_collision', 'BOOL',  props.stop_on_collision)

        # Movement type
        ensure_prop('ps_movement_type', 'STRING', props.movement_type)

        # Force properties (XYZ)
        ensure_prop('ps_force_x', 'FLOAT', props.force[0])
        ensure_prop('ps_force_y', 'FLOAT', props.force[1])
        ensure_prop('ps_force_z', 'FLOAT', props.force[2])

        # Torque properties (XYZ)
        ensure_prop('ps_torque_x', 'FLOAT', props.torque[0])
        ensure_prop('ps_torque_y', 'FLOAT', props.torque[1])
        ensure_prop('ps_torque_z', 'FLOAT', props.torque[2])

        # Damping
        ensure_prop('ps_drag_enabled', 'BOOL',  props.drag_enabled)
        ensure_prop('ps_drag_start',   'FLOAT', props.drag_start)
        ensure_prop('ps_drag_end',     'FLOAT', props.drag_end)
        ensure_prop('ps_resistance',   'FLOAT', props.resistance_strength)

        # Billboard Roll
        ensure_prop('ps_bb_roll_enabled', 'BOOL',  props.billboard_roll_enabled)
        ensure_prop('ps_bb_roll_speed',   'FLOAT', props.billboard_roll_speed)
        ensure_prop('ps_bb_roll_random',  'FLOAT', props.billboard_roll_random)
        ensure_prop('ps_bb_facing',       'STRING', props.billboard_facing)

        # Rotation properties (XYZ)
        ensure_prop('ps_rotation_x', 'FLOAT', props.rotation[0])
        ensure_prop('ps_rotation_y', 'FLOAT', props.rotation[1])
        ensure_prop('ps_rotation_z', 'FLOAT', props.rotation[2])

        mesh_name = props.particle_mesh.name if props.particle_mesh else 'ParticleSphere'
        ensure_prop('ps_particle_mesh', 'STRING', mesh_name)
        ensure_prop('ps_particle_type', 'STRING', props.particle_type)

        # Color over lifetime
        ensure_prop('ps_enable_color',     'BOOL',  props.enable_color)
        ensure_prop('ps_color_mode',       'STRING', props.color_mode)
        ensure_prop('ps_color_curve',      'STRING', '  ')
        ensure_prop('ps_size_curve',       'STRING', '  ')
        ensure_prop('ps_alpha_curve',      'STRING', '  ')
        ensure_prop('ps_color_start_r', 'FLOAT', props.color_start[0])
        ensure_prop('ps_color_start_g', 'FLOAT', props.color_start[1])
        ensure_prop('ps_color_start_b', 'FLOAT', props.color_start[2])
        ensure_prop('ps_color_end_r',   'FLOAT', props.color_end[0])
        ensure_prop('ps_color_end_g',   'FLOAT', props.color_end[1])
        ensure_prop('ps_color_end_b',   'FLOAT', props.color_end[2])
        ensure_prop('ps_color_start_time', 'FLOAT', props.color_start_time)
        ensure_prop('ps_color_end_time',   'FLOAT', props.color_end_time)

        # Alpha over lifetime
        ensure_prop('ps_enable_alpha', 'BOOL',  props.enable_alpha)
        ensure_prop('ps_alpha_mode',   'STRING', props.alpha_mode)
        ensure_prop('ps_size_mode',    'STRING', props.size_mode)
        ensure_prop('ps_start_alpha',      'FLOAT', props.start_alpha)
        ensure_prop('ps_end_alpha',        'FLOAT', props.end_alpha)
        ensure_prop('ps_alpha_start_time', 'FLOAT', props.alpha_start_time)
        ensure_prop('ps_alpha_end_time',   'FLOAT', props.alpha_end_time)

        # Turbulence
        ensure_prop('ps_enable_turb',      'BOOL',  props.enable_turbulence)
        ensure_prop('ps_turb_strength',    'FLOAT', props.turbulence_strength)
        ensure_prop('ps_turb_frequency',   'FLOAT', props.turbulence_frequency)
        ensure_prop('ps_turb_speed',       'FLOAT', props.turbulence_speed)

        # LOD
        ensure_prop('ps_enable_lod',      'BOOL',  props.enable_lod)
        ensure_prop('ps_lod_levels',       'STRING', props.lod_levels)   # '1'/'2'/'3'
        ensure_prop('ps_lod_start',       'FLOAT', props.lod_start_distance)
        ensure_prop('ps_lod1_dist',       'FLOAT', props.lod1_distance)
        ensure_prop('ps_lod1_max',        'INT',   props.lod1_max_particles)
        ensure_prop('ps_lod1_rate',       'FLOAT', props.lod1_emission_rate)
        ensure_prop('ps_lod1_burst',      'INT',   props.lod1_burst_count)
        ensure_prop('ps_lod1_no_turb',    'BOOL',  props.lod1_disable_turbulence)
        ensure_prop('ps_lod1_no_coll',    'BOOL',  props.lod1_disable_collision)
        ensure_prop('ps_lod1_no_emit',    'BOOL',  props.lod1_disable_emitting)
        ensure_prop('ps_lod1_destroy',    'BOOL',  props.lod1_destroy_particles)
        ensure_prop('ps_lod2_dist',       'FLOAT', props.lod2_distance)
        ensure_prop('ps_lod2_max',        'INT',   props.lod2_max_particles)
        ensure_prop('ps_lod2_rate',       'FLOAT', props.lod2_emission_rate)
        ensure_prop('ps_lod2_burst',      'INT',   props.lod2_burst_count)
        ensure_prop('ps_lod2_no_turb',    'BOOL',  props.lod2_disable_turbulence)
        ensure_prop('ps_lod2_no_coll',    'BOOL',  props.lod2_disable_collision)
        ensure_prop('ps_lod2_no_emit',    'BOOL',  props.lod2_disable_emitting)
        ensure_prop('ps_lod2_destroy',    'BOOL',  props.lod2_destroy_particles)
        ensure_prop('ps_lod3_dist',       'FLOAT', props.lod3_distance)
        ensure_prop('ps_lod3_max',        'INT',   props.lod3_max_particles)
        ensure_prop('ps_lod3_rate',       'FLOAT', props.lod3_emission_rate)
        ensure_prop('ps_lod3_burst',      'INT',   props.lod3_burst_count)
        ensure_prop('ps_lod3_no_turb',    'BOOL',  props.lod3_disable_turbulence)
        ensure_prop('ps_lod3_no_coll',    'BOOL',  props.lod3_disable_collision)
        ensure_prop('ps_lod3_no_emit',    'BOOL',  props.lod3_disable_emitting)
        ensure_prop('ps_lod3_destroy',    'BOOL',  props.lod3_destroy_particles)

        # System Launcher
        ensure_prop('ps_launcher_enabled', 'BOOL',  props.enable_launcher)
        ensure_prop('ps_launcher_dist',    'FLOAT', props.launcher_distance)
        ensure_prop('ps_launcher_prewarm', 'FLOAT', props.launcher_prewarm_distance)

        # Orbit
        ensure_prop('ps_orbit_center',        'STRING', props.orbit_center)
        ensure_prop('ps_orbit_axis_x',        'BOOL',  props.orbit_axis_x)
        ensure_prop('ps_orbit_axis_y',        'BOOL',  props.orbit_axis_y)
        ensure_prop('ps_orbit_axis_z',        'BOOL',  props.orbit_axis_z)
        ensure_prop('ps_orbit_axis_inverse',  'BOOL',  props.orbit_axis_inverse)
        ensure_prop('ps_orbit_speed',         'FLOAT', props.orbit_speed)
        ensure_prop('ps_orbit_speed_random',  'FLOAT', props.orbit_speed_random)
        ensure_prop('ps_orbit_radius',        'FLOAT', props.orbit_radius)
        ensure_prop('ps_orbit_radius_random', 'FLOAT', props.orbit_radius_random)
        ensure_prop('ps_orbit_tilt',          'FLOAT', props.orbit_tilt)

        # Sub-Emitter
        ensure_prop('ps_sub_emitter_enabled',     'BOOL',   props.enable_sub_emitter)
        ensure_prop('ps_sub_emitter',             'STRING', props.sub_emitter_object.name if props.sub_emitter_object else ' ')
        ensure_prop('ps_sub_emitter_inherit_vel', 'BOOL',   props.sub_emitter_inherit_velocity)
        ensure_prop('ps_sub_birth_enabled',       'BOOL',   props.enable_sub_emitter_birth)
        ensure_prop('ps_sub_birth',               'STRING', props.sub_emitter_birth_object.name if props.sub_emitter_birth_object else ' ')
        ensure_prop('ps_sub_birth_inherit_vel',   'BOOL',   props.sub_emitter_birth_inherit_velocity)
        ensure_prop('ps_sub_coll_enabled',        'BOOL',   props.enable_sub_emitter_collision)
        ensure_prop('ps_sub_coll',                'STRING', props.sub_emitter_collision_object.name if props.sub_emitter_collision_object else ' ')
        ensure_prop('ps_sub_coll_inherit_vel',    'BOOL',   props.sub_emitter_collision_inherit_velocity)

        # create per-emitter template and store its name
        if props.particle_type == 'BILLBOARD':
            bb_name = self._ensure_billboard_template(context, init_obj)
            # Store the unique template name so the runtime knows which plane to use
            if 'ps_billboard_template' not in init_obj.game.properties:
                bpy.ops.object.game_property_new(type='STRING', name='ps_billboard_template')
                init_obj.game.properties['ps_billboard_template'].value = bb_name
                added.append("prop:ps_billboard_template")
            else:
                init_obj.game.properties['ps_billboard_template'].value = bb_name

        if not added:
            self.report({'WARNING'}, "Particle system already fully initialized, nothing to add!")
        else:
            # Summarise what was added - group props together for a clean message
            logic_parts = [x for x in added if not x.startswith("prop:")]
            new_props = [x for x in added if x.startswith("prop:")]
            summary = logic_parts[:]
            if new_props:
                summary.append(f"{len(new_props)} game {'property' if len(new_props) == 1 else 'properties'}")
            self.report({'INFO'}, f"Initialized! Added: {', '.join(summary)}")
        return {'FINISHED'}

# Registration
class PARTICLE_OT_apply_material(bpy.types.Operator):
    """Build or rebuild the particle material based on current settings.
    Works for both Billboard (applies to the PS_BP_ plane) and Mesh (applies to the particle mesh).
    Always rebuilds from scratch so there are no leftover nodes from previous configurations."""
    bl_idname = "particle.apply_material"
    bl_label  = "Apply Material"

    @staticmethod
    def _build_nodes(mat, ps):
        """Clear and rebuild the node tree based on ps settings."""
        mat.use_nodes = True
        mat.blend_method = 'BLEND' if ps.texture_render == 'HIGH' else 'HASHED'
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()

        use_tex      = ps.enable_texture
        use_color    = ps.enable_color
        use_alpha    = ps.enable_alpha
        is_billboard = (ps.particle_type == 'BILLBOARD')

        # Output node
        out = nodes.new('ShaderNodeOutputMaterial'); out.location = (700, 0)

        if is_billboard:
            # Billboards use Emission + Transparent mixed by alpha — fully unlit,
            # same brightness from every angle regardless of light direction.
            emission = nodes.new('ShaderNodeEmission');        emission.location = (300,  80)
            transp   = nodes.new('ShaderNodeBsdfTransparent'); transp.location   = (300, -80)
            mix_sh   = nodes.new('ShaderNodeMixShader');       mix_sh.location   = (500,   0)
            links.new(transp.outputs['BSDF'],       mix_sh.inputs[1])
            links.new(emission.outputs['Emission'], mix_sh.inputs[2])
            links.new(mix_sh.outputs['Shader'],     out.inputs['Surface'])

            obj_inf = None
            if use_color or use_alpha or use_tex:
                obj_inf = nodes.new('ShaderNodeObjectInfo'); obj_inf.location = (-300, -150)

            if use_tex:
                tex_co  = nodes.new('ShaderNodeTexCoord'); tex_co.location  = (-600, 150)
                img_tex = nodes.new('ShaderNodeTexImage'); img_tex.location = (-300, 150)
                links.new(tex_co.outputs['UV'], img_tex.inputs['Vector'])
                if ps.billboard_texture:
                    img_tex.image = ps.billboard_texture

                if use_color:
                    # ShaderNodeMix replaces ShaderNodeMixRGB in Blender 5
                    mix_col = nodes.new('ShaderNodeMix'); mix_col.location = (50, 150)
                    mix_col.data_type  = 'RGBA'
                    mix_col.blend_type = 'MULTIPLY'
                    mix_col.inputs['Factor'].default_value = 1.0
                    links.new(img_tex.outputs['Color'], mix_col.inputs['A'])
                    links.new(obj_inf.outputs['Color'], mix_col.inputs['B'])
                    links.new(mix_col.outputs['Result'], emission.inputs['Color'])
                else:
                    links.new(img_tex.outputs['Color'], emission.inputs['Color'])

                if use_alpha:
                    math_a = nodes.new('ShaderNodeMath'); math_a.location = (50, -50)
                    math_a.operation = 'MULTIPLY'
                    links.new(img_tex.outputs['Alpha'], math_a.inputs[0])
                    links.new(obj_inf.outputs['Alpha'], math_a.inputs[1])
                    links.new(math_a.outputs['Value'],  mix_sh.inputs[0])
                else:
                    links.new(img_tex.outputs['Alpha'], mix_sh.inputs[0])

            else:
                if use_color:
                    links.new(obj_inf.outputs['Color'], emission.inputs['Color'])
                if use_alpha:
                    links.new(obj_inf.outputs['Alpha'], mix_sh.inputs[0])
                else:
                    val = nodes.new('ShaderNodeValue'); val.location = (300, -180)
                    val.outputs[0].default_value = 1.0
                    links.new(val.outputs['Value'], mix_sh.inputs[0])

        else:
            # Mesh particles — Principled BSDF so scene lighting applies normally
            bsdf = nodes.new('ShaderNodeBsdfPrincipled'); bsdf.location = (300, 0)
            links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])

            obj_inf = None
            if use_color or use_alpha or use_tex:
                obj_inf = nodes.new('ShaderNodeObjectInfo'); obj_inf.location = (-250, -150)

            if use_tex:
                tex_co  = nodes.new('ShaderNodeTexCoord'); tex_co.location  = (-500, 150)
                img_tex = nodes.new('ShaderNodeTexImage'); img_tex.location = (-250, 150)
                links.new(tex_co.outputs['UV'], img_tex.inputs['Vector'])
                if ps.billboard_texture:
                    img_tex.image = ps.billboard_texture

                if use_color:
                    mix_col = nodes.new('ShaderNodeMix'); mix_col.location = (50, 150)
                    mix_col.data_type  = 'RGBA'
                    mix_col.blend_type = 'MULTIPLY'
                    mix_col.inputs['Factor'].default_value = 1.0
                    links.new(img_tex.outputs['Color'],  mix_col.inputs['A'])
                    links.new(obj_inf.outputs['Color'],  mix_col.inputs['B'])
                    links.new(mix_col.outputs['Result'], bsdf.inputs['Base Color'])
                else:
                    links.new(img_tex.outputs['Color'], bsdf.inputs['Base Color'])

                if use_alpha:
                    math_a = nodes.new('ShaderNodeMath'); math_a.location = (50, -50)
                    math_a.operation = 'MULTIPLY'
                    links.new(img_tex.outputs['Alpha'],  math_a.inputs[0])
                    links.new(obj_inf.outputs['Alpha'],  math_a.inputs[1])
                    links.new(math_a.outputs['Value'],   bsdf.inputs['Alpha'])
                else:
                    links.new(img_tex.outputs['Alpha'], bsdf.inputs['Alpha'])

            else:
                if use_color:
                    links.new(obj_inf.outputs['Color'], bsdf.inputs['Base Color'])
                if use_alpha:
                    links.new(obj_inf.outputs['Alpha'], bsdf.inputs['Alpha'])

    def execute(self, context):
        obj = context.active_object
        if not obj:
            self.report({'ERROR'}, "No active object")
            return {'CANCELLED'}

        ps = obj.particle_system_props

        if ps.particle_type == 'BILLBOARD':
            bb_name = f"PS_BP_{obj.name}"
            target  = bpy.data.objects.get(bb_name)
            if not target:
                self.report({'ERROR'}, f"Billboard plane '{bb_name}' not found — run Initialize first")
                return {'CANCELLED'}
            mat_name = f"PS_BillboardMat_{obj.name}"
        else:
            target = ps.particle_mesh
            if not target:
                self.report({'ERROR'}, "No particle mesh assigned")
                return {'CANCELLED'}
            mat_name = f"PS_Mat_{obj.name}"

        # Get or create the material
        mat = bpy.data.materials.get(mat_name)
        if mat is None:
            mat = bpy.data.materials.new(name=mat_name)
        if not target.data.materials:
            target.data.materials.append(mat)
        else:
            target.data.materials[0] = mat

        self._build_nodes(mat, ps)

        # Bake curve into game prop when Curve mode; clear it for Simple
        if ps.enable_color and ps.color_mode == 'CURVE':
            samples   = sample_color_curve(obj.name, n=16)
            curve_str = ','.join(f'{v:.4f}' for v in samples)
            if 'ps_color_curve' in obj.game.properties:
                obj.game.properties['ps_color_curve'].value = curve_str
        elif 'ps_color_curve' in obj.game.properties:
            obj.game.properties['ps_color_curve'].value = '  '

        if ps.size_mode == 'CURVE':
            samples   = sample_size_curve(obj.name, n=16)
            curve_str = ','.join(f'{v:.4f}' for v in samples)
            if 'ps_size_curve' in obj.game.properties:
                obj.game.properties['ps_size_curve'].value = curve_str
        elif 'ps_size_curve' in obj.game.properties:
            obj.game.properties['ps_size_curve'].value = '  '

        if ps.enable_alpha and ps.alpha_mode == 'CURVE':
            samples   = sample_alpha_curve(obj.name, n=16)
            curve_str = ','.join(f'{v:.4f}' for v in samples)
            if 'ps_alpha_curve' in obj.game.properties:
                obj.game.properties['ps_alpha_curve'].value = curve_str
        elif 'ps_alpha_curve' in obj.game.properties:
            obj.game.properties['ps_alpha_curve'].value = '  '

        self.report({'INFO'}, f"Material '{mat_name}' applied to '{target.name}'")
        return {'FINISHED'}

class PARTICLE_OT_remove_script(bpy.types.Operator):
    """Remove the ParticleController logic bricks and the shared runtime script.
    Use this before re-initializing to force a clean script rebuild."""
    bl_idname  = "particle.remove_script"
    bl_label   = "Remove Script"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if not obj:
            self.report({'ERROR'}, "No active object")
            return {'CANCELLED'}

        removed = []

        # Unlink and remove ParticleController controller
        ctrl = next((c for c in obj.game.controllers if c.name == "ParticleController"), None)
        if ctrl:
            bpy.ops.logic.controller_remove(controller=ctrl.name, object=obj.name)
            removed.append("controller")

        # Remove ParticleInit sensor
        sensor = next((s for s in obj.game.sensors if s.name == "ParticleInit"), None)
        if sensor:
            bpy.ops.logic.sensor_remove(sensor=sensor.name, object=obj.name)
            removed.append("sensor")

        # Remove shared runtime script text block
        script = bpy.data.texts.get("ParticleSys_Runtime.py")
        if script:
            bpy.data.texts.remove(script)
            removed.append("runtime script")

        if removed:
            self.report({'INFO'}, f"Removed: {', '.join(removed)}")
        else:
            self.report({'WARNING'}, "Nothing to remove — not initialized on this object")
        return {'FINISHED'}

class PARTICLE_OT_remove_props(bpy.types.Operator):
    """Remove all ps_ game properties from the active object.
    Use this before re-initializing to force a full property rebuild."""
    bl_idname  = "particle.remove_props"
    bl_label   = "Remove Props"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if not obj:
            self.report({'ERROR'}, "No active object")
            return {'CANCELLED'}

        # Collect indices of all ps_ props (remove in reverse so indices stay valid)
        indices = [i for i, p in enumerate(obj.game.properties)
                   if p.name.startswith("ps_")]
        if not indices:
            self.report({'WARNING'}, "No ps_ game properties found on this object")
            return {'CANCELLED'}

        for idx in reversed(indices):
            bpy.ops.object.game_property_remove(index=idx)

        self.report({'INFO'}, f"Removed {len(indices)} game properties")
        return {'FINISHED'}


_WIRE_PREFIXES = (
    "PS_Wire_Box_",
    "PS_Wire_Sphere_",
    "PS_Wire_Hemisphere_",
    "PS_Wire_Cone_",
    "PS_Wire_Ring_",
)

def _cleanup_orphaned_wires(scene, depsgraph):
    """Called after every depsgraph update.
    Scans for PS wire objects whose parent emitter no longer exists and removes them.
    Fast path: if no wire objects exist at all, returns immediately with one scan."""
    to_remove = []
    for obj in bpy.data.objects:
        for prefix in _WIRE_PREFIXES:
            if obj.name.startswith(prefix):
                emitter_name = obj.name[len(prefix):]
                if emitter_name not in bpy.data.objects:
                    to_remove.append(obj)
                break  # matched a prefix — no need to check the rest

    for obj in to_remove:
        mesh = obj.data if obj.type == 'MESH' else None
        try:
            bpy.data.objects.remove(obj, do_unlink=True)
        except ReferenceError:
            pass
        if mesh and mesh.users == 0:
            try:
                bpy.data.meshes.remove(mesh)
            except ReferenceError:
                pass


classes = (
    ParticleSystemProperties,
    PARTICLE_PT_upbge_panel,
    PARTICLE_OT_preview_toggle,
    PARTICLE_OT_setup_logic,
    PARTICLE_OT_apply_material,
    PARTICLE_OT_init_color_curve,
    PARTICLE_OT_init_alpha_curve,
    PARTICLE_OT_init_size_curve,
    PARTICLE_OT_remove_script,
    PARTICLE_OT_remove_props,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Object.particle_system_props = bpy.props.PointerProperty(type=ParticleSystemProperties)
    # Auto-delete wire visualizers when their emitter is deleted
    if _cleanup_orphaned_wires not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(_cleanup_orphaned_wires)

def unregister():
    # Remove the depsgraph handler first so it can't fire during cleanup
    if _cleanup_orphaned_wires in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(_cleanup_orphaned_wires)

    # Clean up all PS wire objects from all objects in all scenes
    for obj in list(bpy.data.objects):
        if any(obj.name.startswith(prefix) for prefix in _WIRE_PREFIXES):
            mesh = obj.data if obj.type == 'MESH' else None
            bpy.data.objects.remove(obj, do_unlink=True)
            if mesh and mesh.users == 0:
                bpy.data.meshes.remove(mesh)

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Object.particle_system_props

if __name__ == "__main__":
    register()