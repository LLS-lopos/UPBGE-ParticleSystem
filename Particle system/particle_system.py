bl_info = {
    "name": "UPBGE Particle System",
    "author": "Ghost DEV",
    "version": (0, 7, 1),
    "blender": (5, 0, 0),
    "location": "Properties > Physics Properties",
    "description": "Simple particle system for UPBGE using mesh instances (NO GPU)",
    "warning": "It is still an alpha version and it is not stable at all times",
    "wiki_url": "",
    "category": "Physics",
}

import bpy
from mathutils import Vector
import random

# Wire shape visualization
def update_wire_shape(self, context):
    """Update wire shape visualization - reuses meshes, just hides/shows them"""
    obj = context.object
    if not obj:
        return
    
    ps = obj.particle_system_props
    
    # Wire names for each shape type
    wire_box_name = f"PS_Wire_Box_{obj.name}"
    wire_sphere_name = f"PS_Wire_Sphere_{obj.name}"
    
    # Get existing wires
    wire_box = bpy.data.objects.get(wire_box_name)
    wire_sphere = bpy.data.objects.get(wire_sphere_name)
    
    # If disabled or POINT shape, hide all wires
    if not ps.enabled or ps.emission_shape == 'POINT':
        if wire_box:
            wire_box.hide_viewport = True
            wire_box.hide_render = True
        if wire_sphere:
            wire_sphere.hide_viewport = True
            wire_sphere.hide_render = True
        update_game_prop(self, context)
        return
    
    # Create Box wire if it doesn't exist
    if not wire_box:
        wire_box = create_box_wire(obj, wire_box_name)
    
    # Create Sphere wire if it doesn't exist
    if not wire_sphere:
        wire_sphere = create_sphere_wire(obj, wire_sphere_name)
    
    # Show/hide based on current shape
    if ps.emission_shape == 'BOX':

        wire_box.parent = obj
        wire_box.matrix_parent_inverse = obj.matrix_world.__class__()
        
        # Keep wire centered on emitter in local space
        wire_box.location = (0, 0, 0)
        wire_box.rotation_euler = (0, 0, 0)
        
        wire_box.hide_viewport = False
        wire_box.hide_render = True
        wire_box.scale = ps.emission_box_size
        if wire_sphere:
            wire_sphere.hide_viewport = True
            wire_sphere.hide_render = True
    
    elif ps.emission_shape == 'SPHERE':
        # Parent to emitter with identity inverse so local origin = emitter origin
        wire_sphere.parent = obj
        wire_sphere.matrix_parent_inverse = obj.matrix_world.__class__()
        
        # Keep wire centered on emitter in local space
        wire_sphere.location = (0, 0, 0)
        wire_sphere.rotation_euler = (0, 0, 0)
        
        wire_sphere.hide_viewport = False
        wire_sphere.hide_render = True
        radius = ps.emission_sphere_radius
        wire_sphere.scale = (radius, radius, radius)
        if wire_box:
            wire_box.hide_viewport = True
            wire_box.hide_render = True
    
    update_game_prop(self, context)

def create_box_wire(obj, wire_name):
    """Create box wire mesh (called once, reused forever)"""
    import bmesh
    
    mesh = bpy.data.meshes.new(f"PS_WireMesh_Box_{obj.name}")
    wire_obj = bpy.data.objects.new(wire_name, mesh)
    
    # Store shape type
    wire_obj['ps_shape_type'] = 'BOX'
    
    # Link to collection
    bpy.context.collection.objects.link(wire_obj)
    
    # Parent to emitter with identity inverse so wire is always at emitter's local origin
    wire_obj.parent = obj
    wire_obj.matrix_parent_inverse = obj.matrix_world.__class__()
    
    # Create bmesh (UNIT box)
    bm = bmesh.new()
    
    verts = [
        bm.verts.new((-0.5, -0.5, -0.5)),
        bm.verts.new((0.5, -0.5, -0.5)),
        bm.verts.new((0.5, 0.5, -0.5)),
        bm.verts.new((-0.5, 0.5, -0.5)),
        bm.verts.new((-0.5, -0.5, 0.5)),
        bm.verts.new((0.5, -0.5, 0.5)),
        bm.verts.new((0.5, 0.5, 0.5)),
        bm.verts.new((-0.5, 0.5, 0.5)),
    ]
    
    edges = [
        (0,1), (1,2), (2,3), (3,0),  # Bottom
        (4,5), (5,6), (6,7), (7,4),  # Top
        (0,4), (1,5), (2,6), (3,7),  # Vertical
    ]
    for e in edges:
        bm.edges.new((verts[e[0]], verts[e[1]]))
    
    bm.to_mesh(mesh)
    bm.free()
    
    # Display properties
    wire_obj.display_type = 'WIRE'
    wire_obj.show_in_front = True
    wire_obj.hide_render = True
    wire_obj.hide_select = True
    wire_obj.color = (0, 1, 1, 1)
    
    return wire_obj

def create_sphere_wire(obj, wire_name):
    """Create sphere wire mesh (called once, reused forever)"""
    import bmesh
    import math
    
    mesh = bpy.data.meshes.new(f"PS_WireMesh_Sphere_{obj.name}")
    wire_obj = bpy.data.objects.new(wire_name, mesh)
    
    # Store shape type
    wire_obj['ps_shape_type'] = 'SPHERE'
    
    # Link to collection
    bpy.context.collection.objects.link(wire_obj)
    
    # Parent to emitter with identity inverse so wire is always at emitter's local origin
    wire_obj.parent = obj
    wire_obj.matrix_parent_inverse = obj.matrix_world.__class__()
    
    # Create bmesh
    bm = bmesh.new()
    segments = 32
    
    # XY circle
    verts_xy = []
    for i in range(segments):
        angle = 2 * math.pi * i / segments
        x = math.cos(angle)
        y = math.sin(angle)
        verts_xy.append(bm.verts.new((x, y, 0)))
    
    for i in range(segments):
        bm.edges.new((verts_xy[i], verts_xy[(i+1) % segments]))
    
    # XZ circle
    verts_xz = []
    for i in range(segments):
        angle = 2 * math.pi * i / segments
        x = math.cos(angle)
        z = math.sin(angle)
        verts_xz.append(bm.verts.new((x, 0, z)))
    
    for i in range(segments):
        bm.edges.new((verts_xz[i], verts_xz[(i+1) % segments]))
    
    # YZ circle
    verts_yz = []
    for i in range(segments):
        angle = 2 * math.pi * i / segments
        y = math.cos(angle)
        z = math.sin(angle)
        verts_yz.append(bm.verts.new((0, y, z)))
    
    for i in range(segments):
        bm.edges.new((verts_yz[i], verts_yz[(i+1) % segments]))
    
    bm.to_mesh(mesh)
    bm.free()
    
    # Display properties
    wire_obj.display_type = 'WIRE'
    wire_obj.show_in_front = True
    wire_obj.hide_render = True
    wire_obj.hide_select = True
    wire_obj.color = (0, 1, 1, 1)
    
    return wire_obj

def update_game_prop(self, context):
    obj = context.object
    if not obj: return
    
    # Mapping between Addon props and Game props
    props_map = {
        'enabled': 'ps_enabled',
        'trigger_enabled': 'ps_trigger',
        'emission_mode': 'ps_emission_mode',
        'emission_shape': 'ps_emission_shape',
        'emission_sphere_radius': 'ps_emission_sphere_radius',
        'max_particles': 'ps_max_particles',
        'emission_rate': 'ps_emission_rate',
        'emission_delay': 'ps_emission_delay',
        'burst_count': 'ps_burst_count',
        'is_one_shot': 'ps_is_one_shot',
        'lifetime': 'ps_lifetime',
        'lifetime_random': 'ps_lifetime_random',
        'start_size': 'ps_start_size',
        'end_size': 'ps_end_size',
        'velocity_random': 'ps_velocity_random',
        'simulation_space': 'ps_simulation_space',
        'movement_type': 'ps_movement_type',
        'damping': 'ps_damping',
        'enable_collision': 'ps_enable_collision',
        'bounce_strength': 'ps_bounce_strength',
        'particle_type': 'ps_particle_type',
        'start_alpha': 'ps_start_alpha',
        'color_start_time': 'ps_color_start_time',
        'color_end_time': 'ps_color_end_time',
        'enable_color': 'ps_enable_color',
        'enable_alpha': 'ps_enable_alpha',
        'enable_lod':               'ps_enable_lod',
        'lod_start_distance':       'ps_lod_start',
        'lod1_distance':            'ps_lod1_dist',
        'lod1_max_particles':       'ps_lod1_max',
        'lod1_emission_rate':       'ps_lod1_rate',
        'lod1_burst_count':         'ps_lod1_burst',
        'lod1_disable_collision':   'ps_lod1_no_coll',
        'lod1_disable_emitting':    'ps_lod1_no_emit',
        'lod1_destroy_particles':   'ps_lod1_destroy',
        'lod2_distance':            'ps_lod2_dist',
        'lod2_max_particles':       'ps_lod2_max',
        'lod2_emission_rate':       'ps_lod2_rate',
        'lod2_burst_count':         'ps_lod2_burst',
        'lod2_disable_collision':   'ps_lod2_no_coll',
        'lod2_disable_emitting':    'ps_lod2_no_emit',
        'lod2_destroy_particles':   'ps_lod2_destroy',
        'lod3_distance':            'ps_lod3_dist',
        'lod3_max_particles':       'ps_lod3_max',
        'lod3_emission_rate':       'ps_lod3_rate',
        'lod3_burst_count':         'ps_lod3_burst',
        'lod3_disable_collision':   'ps_lod3_no_coll',
        'lod3_disable_emitting':    'ps_lod3_no_emit',
        'lod3_destroy_particles':   'ps_lod3_destroy',
    }
    
    for addon_prop, game_prop in props_map.items():
        if game_prop in obj.game.properties:
            obj.game.properties[game_prop].value = getattr(self, addon_prop)

    # Vectors Handlers
    if 'ps_start_velocity_x' in obj.game.properties:
        obj.game.properties['ps_start_velocity_x'].value = self.start_velocity[0]
        obj.game.properties['ps_start_velocity_y'].value = self.start_velocity[1]
        obj.game.properties['ps_start_velocity_z'].value = self.start_velocity[2]

    if 'ps_gravity_x' in obj.game.properties:
        obj.game.properties['ps_gravity_x'].value = self.gravity[0]
        obj.game.properties['ps_gravity_y'].value = self.gravity[1]
        obj.game.properties['ps_gravity_z'].value = self.gravity[2]
    
    if 'ps_rotation_x' in obj.game.properties:
        obj.game.properties['ps_rotation_x'].value = self.rotation[0]
        obj.game.properties['ps_rotation_y'].value = self.rotation[1]
        obj.game.properties['ps_rotation_z'].value = self.rotation[2]
    
    if 'ps_force_x' in obj.game.properties:
        obj.game.properties['ps_force_x'].value = self.force[0]
        obj.game.properties['ps_force_y'].value = self.force[1]
        obj.game.properties['ps_force_z'].value = self.force[2]
    
    if 'ps_torque_x' in obj.game.properties:
        obj.game.properties['ps_torque_x'].value = self.torque[0]
        obj.game.properties['ps_torque_y'].value = self.torque[1]
        obj.game.properties['ps_torque_z'].value = self.torque[2]
    
    if 'ps_emission_box_size_x' in obj.game.properties:
        obj.game.properties['ps_emission_box_size_x'].value = self.emission_box_size[0]
        obj.game.properties['ps_emission_box_size_y'].value = self.emission_box_size[1]
        obj.game.properties['ps_emission_box_size_z'].value = self.emission_box_size[2]

    if 'ps_particle_mesh' in obj.game.properties:
        mesh_name = self.particle_mesh.name if self.particle_mesh else 'ParticleSphere'
        obj.game.properties['ps_particle_mesh'].value = mesh_name

    if 'ps_color_start_r' in obj.game.properties:
        obj.game.properties['ps_color_start_r'].value = self.color_start[0]
        obj.game.properties['ps_color_start_g'].value = self.color_start[1]
        obj.game.properties['ps_color_start_b'].value = self.color_start[2]

    if 'ps_color_end_r' in obj.game.properties:
        obj.game.properties['ps_color_end_r'].value = self.color_end[0]
        obj.game.properties['ps_color_end_g'].value = self.color_end[1]
        obj.game.properties['ps_color_end_b'].value = self.color_end[2]

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
        description="Control emission via Logic Bricks (True = Emit, False = Stop)",
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
            ('POINT', "Point", "Emit from center point"),
            ('BOX', "Box", "Emit from random points within a box volume"),
            ('SPHERE', "Sphere", "Emit from random points within a sphere volume"),
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
    
    max_particles: bpy.props.IntProperty(name="Max Particles", default=100, min=1, max=5000, update=update_game_prop)
    emission_rate: bpy.props.FloatProperty(name="Emission Rate", default=10.0, min=0.0, max=1000, update=update_game_prop)
    
    # NEW: Delay for Burst Mode
    emission_delay: bpy.props.FloatProperty(name="Burst Delay", description="Time between bursts (seconds)", default=1.0, min=0.1, max=100.0, update=update_game_prop)
    
    burst_count: bpy.props.IntProperty(name="Burst Count", default=30, min=1, max=1500, update=update_game_prop)
    is_one_shot: bpy.props.BoolProperty(name="One Shot", description="Fire once when triggered, reset when trigger stops", default=False, update=update_game_prop)
    
    lifetime: bpy.props.FloatProperty(name="Lifetime", default=3.0, min=0.1, max=100.0, update=update_game_prop)
    lifetime_random: bpy.props.FloatProperty(name="Random Lifetime", default=0.5, min=0.0, max=1.0, update=update_game_prop)
    start_size: bpy.props.FloatProperty(name="Start Size", default=0.1, min=0.001, max=10.0, update=update_game_prop)
    end_size: bpy.props.FloatProperty(name="End Size", default=0.05, min=0.001, max=10.0, update=update_game_prop)
    
    start_velocity: bpy.props.FloatVectorProperty(name="Start Velocity", default=(0.0, 0.0, 2.0), size=3, update=update_game_prop)
    velocity_random: bpy.props.FloatProperty(name="Random Velocity", default=0.5, min=0.0, max=10.0, update=update_game_prop)
    gravity: bpy.props.FloatVectorProperty(name="Gravity", default=(0.0, 0.0, -9.8), size=3, update=update_game_prop)
    
    # Movement Type
    movement_type: bpy.props.EnumProperty(
        name="Movement Type",
        description="How particles move through space",
        items=[
            ('SIMPLE', "Simple", "Direct velocity - instant motion (current behavior)"),
            ('FORCE', "Force-Based", "Acceleration/deceleration - realistic physics"),
        ],
        default='SIMPLE',
        update=update_game_prop
    )
    
    # Force-Based Properties
    force: bpy.props.FloatVectorProperty(
        name="Force",
        description="Applied force (acceleration) in units/sec²",
        default=(0.0, 0.0, 0.0),
        size=3,
        update=update_game_prop
    )
    
    torque: bpy.props.FloatVectorProperty(
        name="Torque",
        description="Angular force (rotational acceleration) in degrees/sec²",
        default=(0.0, 0.0, 0.0),
        size=3,
        update=update_game_prop
    )
    
    damping: bpy.props.FloatProperty(
        name="Damping",
        description="Air resistance (0=none, 1=immediate stop)",
        default=0.0,
        min=0.0,
        max=1.0,
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
    
    # Particle Type
    particle_type: bpy.props.EnumProperty(
        name="Particle Type",
        description="How each particle is rendered",
        items=[
            ('BILLBOARD', "Billboard", "Auto-created plane that always faces the active camera"),
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
            "When OFF: simple Object Color material only — no transparency issues. "
            "When ON: full UV + Image Texture node graph is generated on Initialize. "
            "You must assign an image to the Image Texture node, "
            "otherwise the billboard will appear transparent."
        ),
        default=False,
    )

    billboard_texture: bpy.props.PointerProperty(
        name="Texture",
        type=bpy.types.Image,
        description="Image to apply to the billboard material",
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
        description="How much particles bounce (0.0 = no bounce, 1.0 = full bounce)",
        default=0.5,
        min=0.0,
        max=1.0,
        update=update_game_prop
    )
    
    # Rotation Property (XYZ like velocity)
    rotation: bpy.props.FloatVectorProperty(
        name="Rotation",
        description="Rotation in degrees per lifetime (X, Y, Z axes)",
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
        description="Lifetime ratio (0-10) when color transition begins. Lower = starts earlier",
        default=0.0,
        min=0.0, max=10.0,
        update=update_game_prop
    )

    color_end_time: bpy.props.FloatProperty(
        name="End Time",
        description="Lifetime ratio (0-10) when color transition ends. Higher = ends later",
        default=10.0,
        min=0.0, max=10.0,
        update=update_game_prop
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
        description="Opacity at birth (1.0 = fully opaque, 0.0 = invisible). Fades to 0 accelerating near death",
        default=1.0,
        min=0.0, max=1.0,
        update=update_game_prop
    )

    # LOD Properties
    enable_lod: bpy.props.BoolProperty(
        name="Enable LOD",
        description="Enable Level of Detail — reduces simulation cost at distance",
        default=False,
        update=update_game_prop
    )

    lod_start_distance: bpy.props.FloatProperty(
        name="Start LOD",
        description="Distance from the active camera at which LOD begins. Below this = full simulation",
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
        description="Maximum active particles at LOD 1 (uses a portion of the main pool)",
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
        description="Maximum active particles at LOD 2 (uses a portion of the main pool)",
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
        description="Maximum active particles at LOD 3 (uses a portion of the main pool)",
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
        
        # Play Preview Toggle Button
        ps = obj.particle_system_props
        if ps.preview_active:
            row.operator("particle.preview_toggle", text="Stop Preview", icon='PAUSE', depress=True)
        else:
            row.operator("particle.preview_toggle", text="Play Preview", icon='PLAY')
        
        layout.separator()
        ps = obj.particle_system_props
        
        layout.prop(ps, "enabled", text="Particle Emitter")
        
        if ps.enabled:
            box = layout.box()
            box.label(text="Emission:")
            
            box.prop(ps, "emission_mode", text="Mode")
            box.prop(ps, "emission_shape", text="Shape")
            
            # Show shape-specific size controls
            if ps.emission_shape == 'BOX':
                box.prop(ps, "emission_box_size")
            elif ps.emission_shape == 'SPHERE':
                box.prop(ps, "emission_sphere_radius")
            
            # MOVED DOWN: Trigger is now below Mode
            layout.prop(ps, "trigger_enabled", text="Emission Trigger")
            
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
            box.label(text="Appearance:")

            # Particle type selector
            box.prop(ps, "particle_type", text="Particle Type")
            
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

            box.prop(ps, "start_size")
            box.prop(ps, "end_size")

            # Material settings
            box.separator()
            box.label(text="Material:", icon='MATERIAL')

            # Texture
            box.prop(ps, "enable_texture", text="Enable Texture")
            if ps.enable_texture:
                box.prop(ps, "billboard_texture", text="Image")
                if not ps.billboard_texture:
                    box.label(text="No image selected — texture slot will be empty", icon='ERROR')

            # Color over Lifetime
            box.prop(ps, "enable_color", text="Color over Lifetime")
            if ps.enable_color:
                row2 = box.row()
                row2.prop(ps, "color_start", text="Start")
                row2.prop(ps, "color_end", text="End")
                row3 = box.row(align=True)
                row3.prop(ps, "color_start_time", text="From")
                row3.prop(ps, "color_end_time", text="To")

            # Alpha over Lifetime
            box.prop(ps, "enable_alpha", text="Alpha over Lifetime")
            if ps.enable_alpha:
                box.prop(ps, "start_alpha", text="Start Alpha", slider=True)

            # Apply Material button
            box.separator()
            box.operator("particle.apply_material", text="Apply Material", icon='NODE_MATERIAL')


            # Physics
            box = layout.box()
            box.label(text="Physics:")

            box.prop(ps, "simulation_space", text="Space")
            box.prop(ps, "movement_type", text="Movement")
            
            # Conditional UI based on movement type
            if ps.movement_type == 'SIMPLE':
                # Simple mode (current behavior)
                box.prop(ps, "start_velocity")
                box.prop(ps, "rotation")
                box.prop(ps, "velocity_random")
                box.prop(ps, "gravity")
            else:
                # Force-based mode
                box.prop(ps, "start_velocity", text="Initial Velocity")
                box.prop(ps, "force")
                box.prop(ps, "torque")
                box.prop(ps, "damping", slider=True)
                box.prop(ps, "velocity_random")
                box.prop(ps, "gravity")
            
            # Collision section
            box.separator()
            box.prop(ps, "enable_collision", text="Enable Collision")
            if ps.enable_collision:
                box.prop(ps, "bounce_strength", slider=True)

            # Render / LOD box
            box = layout.box()
            box.label(text="Render:")
            box.prop(ps, "enable_lod", text="Enable LOD")

            if ps.enable_lod:
                # LOD 0 — Full simulation, distance controlled by start slider
                lod0_box = box.box()
                lod0_box.label(text="LOD 0 — Full Simulation")
                lod0_box.prop(ps, "lod_start_distance", text="Start LOD")

                # LOD 1
                lod1_box = box.box()
                lod1_box.label(text="LOD 1")
                lod1_box.prop(ps, "lod1_distance", text="Distance")
                lod1_box.prop(ps, "lod1_max_particles", text="Max Particles")
                if ps.emission_mode == 'BURST':
                    lod1_box.prop(ps, "lod1_burst_count", text="Burst Count")
                else:
                    lod1_box.prop(ps, "lod1_emission_rate", text="Emission Rate")
                lod1_box.prop(ps, "lod1_disable_collision", text="Disable Collision")
                lod1_box.prop(ps, "lod1_disable_emitting",  text="Disable Emitting")
                if ps.lod1_disable_emitting:
                    lod1_box.prop(ps, "lod1_destroy_particles", text="Destroy Particles")

                # LOD 2
                lod2_box = box.box()
                lod2_box.label(text="LOD 2")
                lod2_box.prop(ps, "lod2_distance", text="Distance")
                lod2_box.prop(ps, "lod2_max_particles", text="Max Particles")
                if ps.emission_mode == 'BURST':
                    lod2_box.prop(ps, "lod2_burst_count", text="Burst Count")
                else:
                    lod2_box.prop(ps, "lod2_emission_rate", text="Emission Rate")
                lod2_box.prop(ps, "lod2_disable_collision", text="Disable Collision")
                lod2_box.prop(ps, "lod2_disable_emitting",  text="Disable Emitting")
                if ps.lod2_disable_emitting:
                    lod2_box.prop(ps, "lod2_destroy_particles", text="Destroy Particles")

                # LOD 3
                lod3_box = box.box()
                lod3_box.label(text="LOD 3")
                lod3_box.prop(ps, "lod3_distance", text="Distance")
                lod3_box.prop(ps, "lod3_max_particles", text="Max Particles")
                if ps.emission_mode == 'BURST':
                    lod3_box.prop(ps, "lod3_burst_count", text="Burst Count")
                else:
                    lod3_box.prop(ps, "lod3_emission_rate", text="Emission Rate")
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
            import time
            current_time = time.time()
            if self._last_time == 0:
                dt = 0.016
            else:
                dt = current_time - self._last_time
            self._last_time = current_time
            dt = min(dt, 0.1)
            
            # Update existing particles
            if self._particles is None:
                self._particles = []

            import math

            # Hoist per-frame constants out of the particle loop
            gravity       = Vector(ps.gravity)
            enable_coll   = ps.enable_collision
            bounce        = ps.bounce_strength
            movement_type = ps.movement_type
            is_force      = (movement_type == 'FORCE')

            # FORCE mode constants
            if is_force:
                force_vec    = Vector(ps.force)
                damping      = ps.damping
                acc          = (force_vec + gravity) * dt
                damp_factor  = 1.0 - damping * dt
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

            to_remove = []
            for i, particle_data in enumerate(self._particles):
                particle_obj, age, lifetime, start_size, end_size, velocity, angular_velocity, rotation, is_billboard, col_start, col_end, col_t0, col_t1, p_start_alpha = particle_data
                age += dt

                if age >= lifetime:
                    to_remove.append(i)
                    bpy.data.objects.remove(particle_obj, do_unlink=True)
                    continue

                # Physics
                if is_force:
                    # Apply combined force + gravity acceleration then damping
                    velocity += acc
                    velocity *= damp_factor
                else:
                    # SIMPLE: gravity only
                    velocity += grav_dt

                # Position integration + collision (ground plane Z=0 for preview)
                if enable_coll:
                    next_pos = particle_obj.location + velocity * dt
                    if next_pos.z < 0:
                        velocity.z = -velocity.z * bounce
                        next_pos.z = 0.01
                    particle_obj.location = next_pos
                else:
                    particle_obj.location += velocity * dt

                # Size interpolation
                life_ratio = age / lifetime
                size = start_size + (end_size - start_size) * life_ratio
                particle_obj.scale = Vector((size, size, size))

                # Color over lifetime
                if ps.enable_color or ps.enable_alpha:
                    if ps.enable_color:
                        t = (life_ratio - col_t0) / max(col_t1 - col_t0, 0.0001)
                        t = max(0.0, min(1.0, t))
                        cr = col_start[0] + (col_end[0] - col_start[0]) * t
                        cg = col_start[1] + (col_end[1] - col_start[1]) * t
                        cb = col_start[2] + (col_end[2] - col_start[2]) * t
                    else:
                        cr, cg, cb = 1.0, 1.0, 1.0

                    if ps.enable_alpha and p_start_alpha > 0.0:
                        ca = p_start_alpha * ((1.0 - life_ratio) ** (1.0 / p_start_alpha))
                    else:
                        ca = 1.0

                    particle_obj.color = (cr, cg, cb, ca)

                # Billboard: per-particle look-at toward the viewport eye.
                # position, build a full orthonormal XYZ basis, apply as matrix.
                if is_billboard:
                    for area in context.screen.areas:
                        if area.type == 'VIEW_3D':
                            rv3d = area.spaces.active.region_3d
                            if rv3d:
                                from mathutils import Matrix as _Mat
                                eye     = rv3d.view_matrix.inverted().translation
                                to_cam  = (eye - particle_obj.location).normalized()
                                world_z = Vector((0.0, 0.0, 1.0))
                                # Gimbal guard: if to_cam nearly parallel to Z use Y as up ref
                                world_up = Vector((0.0, 1.0, 0.0)) if abs(to_cam.dot(world_z)) > 0.999 else world_z
                                # right = up_ref × to_cam  (X axis of billboard)
                                right   = world_up.cross(to_cam).normalized()
                                # up = to_cam × right  (Z axis of billboard, true up)
                                up      = to_cam.cross(right).normalized()
                                # Build column-major rotation matrix:
                                # col0=right(X), col1=to_cam(Y, faces camera), col2=up(Z)
                                rot_mat = _Mat((
                                    (right.x,  to_cam.x,  up.x),
                                    (right.y,  to_cam.y,  up.y),
                                    (right.z,  to_cam.z,  up.z),
                                ))
                                particle_obj.rotation_euler = rot_mat.to_euler()
                            break

                # Rotation (only for MESH type — billboard handles its own orientation)
                if not is_billboard:
                    if is_force and has_torque:
                        # Torque accumulates angular velocity, damping applied
                        angular_velocity += torque_rad
                        angular_velocity *= damp_factor
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
                                      col_start, col_end, col_t0, col_t1, p_start_alpha)

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
        import math
        obj = context.object
        ps = obj.particle_system_props

        # Limit max particles
        if len(self._particles) >= ps.max_particles:
            old_particle = self._particles.pop(0)
            bpy.data.objects.remove(old_particle[0], do_unlink=True)

        # Calculate spawn position based on emission shape
        emission_shape = ps.emission_shape
        mat = obj.matrix_world

        if emission_shape == 'BOX':
            box_size = ps.emission_box_size
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
            r     = radius * (random.random() ** (1.0 / 3.0))
            local_offset = Vector((
                r * math.sin(phi) * math.cos(theta),
                r * math.sin(phi) * math.sin(theta),
                r * math.cos(phi)
            ))
            spawn_pos = mat @ local_offset

        else:  # POINT
            spawn_pos = mat.translation.copy()

        is_billboard = (ps.particle_type == 'BILLBOARD')

        if is_billboard:
            # Auto-create a plane (shared mesh, instanced objects)
            if self._billboard_mesh is None:
                import bmesh as _bmesh
                bm_data = bpy.data.meshes.new("PS_BillboardMesh")
                bm = _bmesh.new()
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
        velocity = base_vel + random_offset

        # Calculate lifetime
        lifetime = ps.lifetime * (1.0 + (random.random() - 0.5) * ps.lifetime_random)

        # Capture color/alpha settings at spawn time so they stay consistent
        # even if the user changes panel values mid-preview
        p_col_start   = tuple(ps.color_start) if ps.enable_color else (1.0, 1.0, 1.0)
        p_col_end     = tuple(ps.color_end)   if ps.enable_color else (1.0, 1.0, 1.0)
        p_col_t0      = (ps.color_start_time / 10.0) if ps.enable_color else 0.0
        p_col_t1      = max(ps.color_end_time / 10.0, p_col_t0 + 0.0001) if ps.enable_color else 1.0
        p_start_alpha = ps.start_alpha if ps.enable_alpha else 0.0

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
                                p_col_start, p_col_end, p_col_t0, p_col_t1, p_start_alpha))
    
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
            for particle_obj, *_ in self._particles:
                bpy.data.objects.remove(particle_obj, do_unlink=True)
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
        import bmesh as _bm

        # Unique name per emitter so multiple emitters don't share the same template
        plane_name = f'PS_BP_{init_obj.name}'

        # If this emitter already has its own template, nothing to do
        if plane_name in bpy.data.objects:
            return plane_name

        mesh = bpy.data.meshes.new(plane_name)
        bm = _bm.new()
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

        # Controller - add only if missing, or if the script text was deleted
        existing_ctrl = next((c for c in init_obj.game.controllers if c.name == "ParticleController"), None)
        script_missing = existing_ctrl and (not existing_ctrl.text or existing_ctrl.text.name not in bpy.data.texts)
        if not existing_ctrl:
            bpy.ops.logic.controller_add(type='PYTHON', name="ParticleController", object=init_obj.name)
            existing_ctrl = init_obj.game.controllers[-1]
            existing_ctrl.name = "ParticleController"
            existing_ctrl.mode = 'SCRIPT'
            added.append("Controller")
        controller = existing_ctrl
        
        # Runtime Script with OBJECT POOLING for performance
        script_text = """# UPBGE Particle System Runtime v0.7.1

import bge
from bge import logic
from mathutils import Vector, Matrix
import random
import math

# Module-level math cache: avoid repeated attribute lookups inside the hot loop
_random = random.random
_pi     = math.pi
_acos   = math.acos
_sin    = math.sin
_cos    = math.cos
_radians = math.radians

class Particle:
    __slots__ = ('position', 'velocity', 'age', 'lifetime', 'size',
                 'obj', 'rotation', 'angular_velocity', 'local_offset', 'is_active')
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
        self.is_active       = False
class ParticleSystem:
    def __init__(self, emitter_obj):
        self.emitter          = emitter_obj
        self.particle_pool    = []
        self.inactive_stack   = []   # FAST O(1) pool: stack of inactive indices
        self.time_since_emit  = 0.0
        self.particle_template = None
        self.burst_triggered  = False
        self.props            = {}
        # Cached per-frame scalars hoisted out of the particle loop
        self._grav            = Vector((0.0, 0.0, -9.8))
        self._is_local        = False
        self._is_force        = False
        self._size_start      = 0.1
        self._size_delta      = 0.0   # end_size - start_size, pre-subtracted
        self._damping_factor  = 1.0   # (1 - damping * dt), pre-multiplied
        self._enable_collision = False
        self._bounce          = 0.5
        self._prev_mesh       = ''
        self._props_raw       = ()   # Dirty-flag cache: last known raw prop tuple
        self._is_billboard    = False
        self._lod_level       = 0    # Current active LOD level (0 = full sim)
        self.load_properties()
        self.create_particle_template()
        self.initialize_pool()

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
            g('ps_max_particles',       100),    # 8
            g('ps_emission_rate',       10.0),   # 9
            g('ps_emission_delay',      1.0),    # 10
            g('ps_burst_count',         30),     # 11
            g('ps_is_one_shot',         False),  # 12
            g('ps_lifetime',            3.0),    # 13
            g('ps_lifetime_random',     0.5),    # 14
            g('ps_start_size',          0.1),    # 15
            g('ps_end_size',            0.05),   # 16
            g('ps_start_velocity_x',    0.0),    # 17
            g('ps_start_velocity_y',    0.0),    # 18
            g('ps_start_velocity_z',    2.0),    # 19
            g('ps_velocity_random',     0.5),    # 20
            g('ps_gravity_x',           0.0),    # 21
            g('ps_gravity_y',           0.0),    # 22
            g('ps_gravity_z',           -9.8),   # 23
            g('ps_particle_mesh',       'ParticleSphere'),  # 24
            g('ps_simulation_space',    'WORLD'),           # 25
            g('ps_movement_type',       'SIMPLE'),          # 26
            g('ps_force_x',             0.0),    # 27
            g('ps_force_y',             0.0),    # 28
            g('ps_force_z',             0.0),    # 29
            g('ps_torque_x',            0.0),    # 30
            g('ps_torque_y',            0.0),    # 31
            g('ps_torque_z',            0.0),    # 32
            g('ps_damping',             0.0),    # 33
            g('ps_enable_collision',    False),  # 34
            g('ps_bounce_strength',     0.5),    # 35
            g('ps_rotation_x',          0.0),    # 36
            g('ps_rotation_y',          0.0),    # 37
            g('ps_rotation_z',          0.0),    # 38
            g('ps_particle_type',       'MESH'), # 39
            g('ps_billboard_template',  ''),     # 40
            g('ps_color_start_r',       1.0),    # 41
            g('ps_color_start_g',       1.0),    # 42
            g('ps_color_start_b',       1.0),    # 43
            g('ps_color_end_r',         1.0),    # 44
            g('ps_color_end_g',         0.0),    # 45
            g('ps_color_end_b',         0.0),    # 46
            g('ps_color_start_time',    0.0),    # 47
            g('ps_color_end_time',      10.0),   # 48
            g('ps_start_alpha',         1.0),    # 49
            g('ps_enable_color',        False),  # 50
            g('ps_enable_alpha',        False),  # 51
            g('ps_enable_lod',          False),  # 52
            g('ps_lod_start',           20.0),   # 53
            g('ps_lod1_dist',           40.0),   # 54
            g('ps_lod1_max',            50),     # 55
            g('ps_lod1_rate',           10.0),   # 56
            g('ps_lod1_burst',          15),     # 57
            g('ps_lod1_no_coll',        False),  # 58
            g('ps_lod1_no_emit',        False),  # 59
            g('ps_lod1_destroy',        False),  # 60
            g('ps_lod2_dist',           80.0),   # 61
            g('ps_lod2_max',            20),     # 62
            g('ps_lod2_rate',           5.0),    # 63
            g('ps_lod2_burst',          8),      # 64
            g('ps_lod2_no_coll',        True),   # 65
            g('ps_lod2_no_emit',        False),  # 66
            g('ps_lod2_destroy',        False),  # 67
            g('ps_lod3_dist',           150.0),  # 68
            g('ps_lod3_max',            5),      # 69
            g('ps_lod3_rate',           1.0),    # 70
            g('ps_lod3_burst',          3),      # 71
            g('ps_lod3_no_coll',        True),   # 72
            g('ps_lod3_no_emit',        True),   # 73
            g('ps_lod3_destroy',        True),   # 74
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
            'max_particles':          r[8],
            'emission_rate':          r[9],
            'emission_delay':         r[10],
            'burst_count':            r[11],
            'is_one_shot':            r[12],
            'lifetime':               r[13],
            'lifetime_random':        r[14],
            'start_size':             r[15],
            'end_size':               r[16],
            'start_velocity':        (r[17], r[18], r[19]),
            'velocity_random':        r[20],
            'gravity':               (r[21], r[22], r[23]),
            'particle_mesh':          r[24],
            'simulation_space':       r[25],
            'movement_type':          r[26],
            'force':                 (r[27], r[28], r[29]),
            'torque':                (r[30], r[31], r[32]),
            'damping':                r[33],
            'enable_collision':       r[34],
            'bounce_strength':        r[35],
            'rotation':              (r[36], r[37], r[38]),
            'particle_type':          r[39],
            'billboard_template':     r[40],
            'color_start':           (r[41], r[42], r[43]),
            'color_end':             (r[44], r[45], r[46]),
            'color_start_time':       r[47],
            'color_end_time':         r[48],
            'start_alpha':            r[49],
            'enable_color':           r[50],
            'enable_alpha':           r[51],
            'enable_lod':             r[52],
            'lod_start':              r[53],
            'lod1_dist':              r[54],
            'lod1_max':               r[55],
            'lod1_rate':              r[56],
            'lod1_burst':             r[57],
            'lod1_no_coll':           r[58],
            'lod1_no_emit':           r[59],
            'lod1_destroy':           r[60],
            'lod2_dist':              r[61],
            'lod2_max':               r[62],
            'lod2_rate':              r[63],
            'lod2_burst':             r[64],
            'lod2_no_coll':           r[65],
            'lod2_no_emit':           r[66],
            'lod2_destroy':           r[67],
            'lod3_dist':              r[68],
            'lod3_max':               r[69],
            'lod3_rate':              r[70],
            'lod3_burst':             r[71],
            'lod3_no_coll':           r[72],
            'lod3_no_emit':           r[73],
            'lod3_destroy':           r[74],
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
        self._is_local   = (p['simulation_space'] == 'LOCAL')
        self._is_force   = (p['movement_type']    == 'FORCE')
        self._size_start = p['start_size']
        self._size_delta = p['end_size'] - p['start_size']
        self._enable_collision = p['enable_collision']
        self._bounce     = p['bounce_strength']

        grav_t = p['gravity']
        grav_w = Vector(grav_t)

        if self._is_force:
            force_t = p['force']
            force_w = Vector(force_t)
            damping  = p['damping']
            self._damping_factor = 1.0 - damping * dt
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
            self._damping_factor = 1.0
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
        # Normalise the 0-10 timing values to 0-1 ratios
        self._color_t_start    = p['color_start_time'] / 10.0
        self._color_t_end      = max(p['color_end_time'] / 10.0, self._color_t_start + 0.0001)

        # Alpha over lifetime
        self._enable_alpha     = p['enable_alpha']
        self._start_alpha      = p['start_alpha']

        # LOD settings — cache the full table once per props change
        self._lod_enabled  = p['enable_lod']
        self._lod_start    = p['lod_start']
        self._lod_table    = (
            # (dist, max_p, rate, burst, no_coll, no_emit, destroy)
            (p['lod1_dist'], p['lod1_max'], p['lod1_rate'], p['lod1_burst'],
             p['lod1_no_coll'], p['lod1_no_emit'], p['lod1_destroy']),
            (p['lod2_dist'], p['lod2_max'], p['lod2_rate'], p['lod2_burst'],
             p['lod2_no_coll'], p['lod2_no_emit'], p['lod2_destroy']),
            (p['lod3_dist'], p['lod3_max'], p['lod3_rate'], p['lod3_burst'],
             p['lod3_no_coll'], p['lod3_no_emit'], p['lod3_destroy']),
        )

    # ------------------------------------------------------------------
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
            self.particle_pool.append(p)
            self.inactive_stack.append(i)   # All start inactive
        print(f"✓ Pool ready: {len(self.particle_pool)} particles")

    def get_inactive_particle(self):
        '''O(1) pop from inactive stack instead of O(n) linear scan'''
        if self.inactive_stack:
            return self.particle_pool[self.inactive_stack.pop()]
        return None

    def deactivate_particle(self, p):
        '''Hide and push index back onto inactive stack'''
        p.is_active = False
        if p.obj:
            p.obj.worldScale = [0.0, 0.0, 0.0]
            p.obj.visible = False
        # Recover index by identity search (only on deactivation, not hot path)
        idx = self.particle_pool.index(p)
        self.inactive_stack.append(idx)

    # ------------------------------------------------------------------
    # Emission
    # ------------------------------------------------------------------
    def emit_particle(self):
        p = self.get_inactive_particle()
        if not p:
            return

        emission_shape  = self.props['emission_shape']
        emitter_pos     = self.emitter.worldPosition
        emitter_ori     = self.emitter.worldOrientation
        spawn_local_offset = Vector((0.0, 0.0, 0.0))

        if emission_shape == 'BOX':
            bx, by, bz = self.props['emission_box_size']
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
            r      = radius * (_random() ** (1.0 / 3.0))
            sin_phi = _sin(phi)
            spawn_local_offset = Vector((
                r * sin_phi * _cos(theta),
                r * sin_phi * _sin(theta),
                r * _cos(phi),
            ))
            if self._is_local:
                spawn_pos = emitter_pos + (emitter_ori @ spawn_local_offset)
            else:
                spawn_pos = emitter_pos + spawn_local_offset

        else:  # POINT
            spawn_pos = emitter_pos.copy()

        # Velocity
        vr = self.props['velocity_random']
        sv = self.props['start_velocity']
        local_vel = Vector((
            sv[0] + (_random() - 0.5) * 2.0 * vr,
            sv[1] + (_random() - 0.5) * 2.0 * vr,
            sv[2] + (_random() - 0.5) * 2.0 * vr,
        ))
        world_vel = (emitter_ori @ local_vel) if self._is_local else local_vel

        lifetime = self.props['lifetime'] * (1.0 + (_random() - 0.5) * self.props['lifetime_random'])

        # Reset particle state
        p.position.x = spawn_pos.x; p.position.y = spawn_pos.y; p.position.z = spawn_pos.z
        p.velocity.x = world_vel.x; p.velocity.y = world_vel.y; p.velocity.z = world_vel.z
        p.local_offset.x = spawn_local_offset.x
        p.local_offset.y = spawn_local_offset.y
        p.local_offset.z = spawn_local_offset.z
        p.age      = 0.0
        p.lifetime = lifetime
        p.size     = self._size_start
        p.rotation.x = 0.0; p.rotation.y = 0.0; p.rotation.z = 0.0
        p.angular_velocity.x = 0.0; p.angular_velocity.y = 0.0; p.angular_velocity.z = 0.0
        p.is_active = True

        if p.obj:
            p.obj.worldPosition = spawn_pos
            s = self._size_start
            p.obj.worldScale = [s, s, s]
            p.obj.visible = True

    def emit_burst(self):
        for _ in range(self.props['burst_count']):
            self.emit_particle()

    def _emit_burst_lod(self, burst_count, max_particles):
        active_count = len(self.particle_pool) - len(self.inactive_stack)
        slots_free   = max(0, max_particles - active_count)
        count        = min(burst_count, slots_free)
        for _ in range(count):
            self.emit_particle()

    # ------------------------------------------------------------------
    # Main update
    # ------------------------------------------------------------------
    def update(self, dt):
        prev_mesh = self.props.get('particle_mesh')

        # Sync properties only if a game property actually changed this frame.
        # On stable frames this costs one tuple comparison and nothing else.
        props_changed = self.sync_properties()

        # Mesh change: deactivate pool and refresh template
        if self.props.get('particle_mesh') != prev_mesh:
            for p in self.particle_pool:
                if p.is_active:
                    self.deactivate_particle(p)
            self.create_particle_template()

        # Recache frame constants only when props changed OR first frame
        if props_changed or not hasattr(self, '_acc'):
            self._cache_frame_constants(dt)
        else:
            # Props stable: only rebuild the dt-dependent parts (acc scales with dt)
            self._acc = self._acc_per_sec * dt
            if self._is_force:
                self._damping_factor = 1.0 - self.props['damping'] * dt
                self._torque_rad = self._torque_per_sec * dt

        props = self.props

        # ── LOD evaluation ─────────────────────────────────────────
        # Runs once per update() — O(1) distance check against active camera.
        lod_max_particles = props['max_particles']   # default: main setting
        lod_emission_rate = props['emission_rate']
        lod_burst_count   = props['burst_count']
        lod_no_coll       = False
        lod_no_emit       = False
        lod_destroy       = False
        prev_lod_level    = self._lod_level

        if self._lod_enabled:
            scene = logic.getCurrentScene()
            cam   = scene.active_camera
            if cam:
                dist = (self.emitter.worldPosition - cam.worldPosition).length
                if dist <= self._lod_start:
                    self._lod_level = 0
                else:
                    self._lod_level = 0
                    for lvl_idx, (lvl_dist, lvl_max, lvl_rate, lvl_burst,
                                  lvl_ncoll, lvl_ne, lvl_destroy) in enumerate(self._lod_table):
                        if dist >= lvl_dist:
                            self._lod_level   = lvl_idx + 1
                            lod_max_particles = lvl_max
                            lod_emission_rate = lvl_rate
                            lod_burst_count   = lvl_burst
                            lod_no_coll       = lvl_ncoll
                            lod_no_emit       = lvl_ne
                            lod_destroy       = lvl_destroy

            # Destroy particles when entering a new LOD level that requests it
            if lod_destroy and self._lod_level != prev_lod_level:
                for p in self.particle_pool:
                    if p.is_active:
                        self.deactivate_particle(p)
        # ── end LOD ────────────────────────────────────────────────

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
        damping_factor   = self._damping_factor
        enable_collision = self._enable_collision and not lod_no_coll
        bounce           = self._bounce
        size_start       = self._size_start
        size_delta       = self._size_delta
        rot_has_value    = self._rot_has_value
        is_billboard     = self._is_billboard
        emitter_ori      = self.emitter.worldOrientation

        if is_force:
            torque_rad   = self._torque_rad
            damping_fac  = self._damping_factor

        has_torque   = self._has_torque
        if not is_force and rot_has_value:
            rot_rad = self._rot_rad

        # Hoist billboard camera lookup outside the loop — same camera for all particles this frame
        bb_cam = None
        if is_billboard:
            _scene = logic.getCurrentScene()
            bb_cam = _scene.active_camera

        # Color & alpha locals — LOD overrides applied on top
        enable_color  = self._enable_color
        enable_alpha  = self._enable_alpha
        color_start   = self._color_start
        color_end     = self._color_end
        color_t_start = self._color_t_start
        color_t_end   = self._color_t_end
        start_alpha   = self._start_alpha

        for p in self.particle_pool:
            if not p.is_active:
                continue

            p.age += dt
            if p.age >= p.lifetime:
                self.deactivate_particle(p)
                continue

            # Apply acceleration (gravity + optional force) — pre-built above
            p.velocity += acc

            if is_force:
                p.velocity *= damping_fac

            # Capture position BEFORE integration so the ray spans exactly
            # the segment the particle travels this frame (fixes one-frame-late
            # detection and the tunneling it caused at high velocities).
            prev_pos = p.position.copy()

            # Position integration
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
                        dot = p.velocity.dot(hit_normal)
                        p.velocity -= 2.0 * dot * hit_normal
                        p.velocity *= bounce
                        # Push off surface to prevent sinking
                        p.position = hit_pos + hit_normal * 0.02

            # Write to game object
            obj = p.obj
            if obj:
                obj.worldPosition = p.position
                life_ratio = p.age / p.lifetime
                s = size_start + size_delta * life_ratio
                p.size = s
                obj.worldScale = [s, s, s]

                # Color & alpha — only write obj.color if at least one feature is on,
                # avoiding an unnecessary per-particle dict write when both are disabled.
                if enable_color or enable_alpha:
                    if enable_color:
                        t = (life_ratio - color_t_start) / (color_t_end - color_t_start)
                        t = max(0.0, min(1.0, t))
                        cr = color_start[0] + (color_end[0] - color_start[0]) * t
                        cg = color_start[1] + (color_end[1] - color_start[1]) * t
                        cb = color_start[2] + (color_end[2] - color_start[2]) * t
                    else:
                        cr = cg = cb = 1.0

                    if enable_alpha:
                        alpha = start_alpha * ((1.0 - life_ratio) ** (1.0 / start_alpha))
                    else:
                        alpha = 1.0

                    obj.color = [cr, cg, cb, alpha]

                # Billboard: face the active camera every frame
                if is_billboard:
                    if bb_cam:
                        cam_pos = bb_cam.worldPosition
                        to_cam  = (cam_pos - p.position).normalized()
                        # Gimbal-lock guard: if to_cam is nearly parallel to Z,
                        # fall back to Y as the reference axis
                        world_z = Vector((0.0, 0.0, 1.0))
                        ref     = Vector((0.0, 1.0, 0.0)) if abs(to_cam.dot(world_z)) > 0.999 else world_z
                        right   = ref.cross(to_cam).normalized()
                        up      = to_cam.cross(right).normalized()
                        # UPBGE worldOrientation expects column-major:
                        # col0=right(X), col1=to_cam(Y/normal), col2=up(Z)
                        rot_mat = Matrix((
                            (right.x, to_cam.x, up.x),
                            (right.y, to_cam.y, up.y),
                            (right.z, to_cam.z, up.z),
                        ))
                        obj.worldOrientation = rot_mat

                # Rotation — only for MESH type, and only when there is actual rotation.
                # worldOrientation triggers an internal matrix decomposition in UPBGE
                # so skipping it when unused saves meaningful cost per particle per frame.
                elif is_force and has_torque:
                    av = p.angular_velocity
                    av += torque_rad
                    av *= damping_fac
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
        print("PARTICLE SYSTEM v0.7.1 - OBJECT POOLING")
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
        
        # Script - write only if controller has no script or the text block was deleted
        import time
        script_needs_write = (
            not controller.text or
            controller.text.name not in bpy.data.texts
        )
        if script_needs_write:
            for t in bpy.data.texts:
                if "ParticleSys_Runtime" in t.name: bpy.data.texts.remove(t)
            script_name = f"ParticleSys_Runtime_{int(time.time())}.py"
            text_block = bpy.data.texts.new(script_name)
            text_block.write(script_text)
            controller.text = text_block
            if "Script" not in added:
                added.append("Script")

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
        ensure_prop('ps_gravity_x', 'FLOAT', props.gravity[0])
        ensure_prop('ps_gravity_y', 'FLOAT', props.gravity[1])
        ensure_prop('ps_gravity_z', 'FLOAT', props.gravity[2])
        
        # Simulation space
        ensure_prop('ps_simulation_space', 'STRING', props.simulation_space)
        
        # Collision properties
        ensure_prop('ps_enable_collision', 'BOOL', props.enable_collision)
        ensure_prop('ps_bounce_strength', 'FLOAT', props.bounce_strength)
        
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
        ensure_prop('ps_damping', 'FLOAT', props.damping)
        
        # Rotation properties (XYZ)
        ensure_prop('ps_rotation_x', 'FLOAT', props.rotation[0])
        ensure_prop('ps_rotation_y', 'FLOAT', props.rotation[1])
        ensure_prop('ps_rotation_z', 'FLOAT', props.rotation[2])
        
        mesh_name = props.particle_mesh.name if props.particle_mesh else 'ParticleSphere'
        ensure_prop('ps_particle_mesh', 'STRING', mesh_name)
        ensure_prop('ps_particle_type', 'STRING', props.particle_type)

        # Color over lifetime
        ensure_prop('ps_enable_color',     'BOOL',  props.enable_color)
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
        ensure_prop('ps_start_alpha', 'FLOAT', props.start_alpha)

        # LOD
        ensure_prop('ps_enable_lod',      'BOOL',  props.enable_lod)
        ensure_prop('ps_lod_start',       'FLOAT', props.lod_start_distance)
        ensure_prop('ps_lod1_dist',       'FLOAT', props.lod1_distance)
        ensure_prop('ps_lod1_max',        'INT',   props.lod1_max_particles)
        ensure_prop('ps_lod1_rate',       'FLOAT', props.lod1_emission_rate)
        ensure_prop('ps_lod1_burst',      'INT',   props.lod1_burst_count)
        ensure_prop('ps_lod1_no_coll',    'BOOL',  props.lod1_disable_collision)
        ensure_prop('ps_lod1_no_emit',    'BOOL',  props.lod1_disable_emitting)
        ensure_prop('ps_lod1_destroy',    'BOOL',  props.lod1_destroy_particles)
        ensure_prop('ps_lod2_dist',       'FLOAT', props.lod2_distance)
        ensure_prop('ps_lod2_max',        'INT',   props.lod2_max_particles)
        ensure_prop('ps_lod2_rate',       'FLOAT', props.lod2_emission_rate)
        ensure_prop('ps_lod2_burst',      'INT',   props.lod2_burst_count)
        ensure_prop('ps_lod2_no_coll',    'BOOL',  props.lod2_disable_collision)
        ensure_prop('ps_lod2_no_emit',    'BOOL',  props.lod2_disable_emitting)
        ensure_prop('ps_lod2_destroy',    'BOOL',  props.lod2_destroy_particles)
        ensure_prop('ps_lod3_dist',       'FLOAT', props.lod3_distance)
        ensure_prop('ps_lod3_max',        'INT',   props.lod3_max_particles)
        ensure_prop('ps_lod3_rate',       'FLOAT', props.lod3_emission_rate)
        ensure_prop('ps_lod3_burst',      'INT',   props.lod3_burst_count)
        ensure_prop('ps_lod3_no_coll',    'BOOL',  props.lod3_disable_collision)
        ensure_prop('ps_lod3_no_emit',    'BOOL',  props.lod3_disable_emitting)
        ensure_prop('ps_lod3_destroy',    'BOOL',  props.lod3_destroy_particles)

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
                summary.append(f"{len(new_props)} game propertie(s)")
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
        mat.blend_method = 'BLEND'
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()

        use_tex   = ps.enable_texture
        use_color = ps.enable_color
        use_alpha = ps.enable_alpha

        # Always need BSDF + Output
        out  = nodes.new('ShaderNodeOutputMaterial'); out.location  = (600, 0)
        bsdf = nodes.new('ShaderNodeBsdfPrincipled'); bsdf.location = (300, 0)
        links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])

        # Object Info — needed for color and/or alpha
        obj_inf = None
        if use_color or use_alpha or use_tex:
            obj_inf = nodes.new('ShaderNodeObjectInfo'); obj_inf.location = (-250, -150)

        if use_tex:
            # Full texture chain: UV → Image Texture × Object Info → BSDF
            tex_co  = nodes.new('ShaderNodeTexCoord'); tex_co.location  = (-500, 150)
            img_tex = nodes.new('ShaderNodeTexImage'); img_tex.location = (-250, 150)
            links.new(tex_co.outputs['UV'], img_tex.inputs['Vector'])

            if ps.billboard_texture:
                img_tex.image = ps.billboard_texture

            if use_color:
                # Multiply texture color × object color
                mix_col = nodes.new('ShaderNodeMixRGB'); mix_col.location = (50, 150)
                mix_col.blend_type = 'MULTIPLY'
                mix_col.inputs['Fac'].default_value = 1.0
                links.new(img_tex.outputs['Color'],  mix_col.inputs['Color1'])
                links.new(obj_inf.outputs['Color'],  mix_col.inputs['Color2'])
                links.new(mix_col.outputs['Color'],  bsdf.inputs['Base Color'])
            else:
                links.new(img_tex.outputs['Color'], bsdf.inputs['Base Color'])

            if use_alpha:
                # Multiply texture alpha × object alpha
                math_a = nodes.new('ShaderNodeMath'); math_a.location = (50, -50)
                math_a.operation = 'MULTIPLY'
                links.new(img_tex.outputs['Alpha'],   math_a.inputs[0])
                links.new(obj_inf.outputs['Alpha'],   math_a.inputs[1])
                links.new(math_a.outputs['Value'],    bsdf.inputs['Alpha'])
            else:
                links.new(img_tex.outputs['Alpha'], bsdf.inputs['Alpha'])

        else:
            # Color-only path — no texture nodes, no transparency artifacts
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

        self.report({'INFO'}, f"Material '{mat_name}' applied to '{target.name}'")
        return {'FINISHED'}


classes = (
    ParticleSystemProperties,
    PARTICLE_PT_upbge_panel,
    PARTICLE_OT_preview_toggle,
    PARTICLE_OT_setup_logic,
    PARTICLE_OT_apply_material,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Object.particle_system_props = bpy.props.PointerProperty(type=ParticleSystemProperties)

def unregister():
    # NOTE: Wire shapes are NOT cleaned up - they persist by design
    # Users can manually delete them if needed (they're parented to emitter objects)
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Object.particle_system_props

if __name__ == "__main__":
    register()