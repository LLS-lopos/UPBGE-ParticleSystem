bl_info = {
    "name": "UPBGE Particle System",
    "author": "Ghost DEV",
    "version": (0, 7, 0),
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
    
    # If disabled or POINT shape, hide all wires but DON'T delete
    if not ps.enabled or ps.emission_shape == 'POINT':
        if wire_box:
            wire_box.hide_viewport = True
            wire_box.hide_render = True
        if wire_sphere:
            wire_sphere.hide_viewport = True
            wire_sphere.hide_render = True
        update_game_prop(self, context)
        return
    
    # Create Box wire
    if not wire_box:
        wire_box = create_box_wire(obj, wire_box_name)
    
    # Create Sphere wire 
    if not wire_sphere:
        wire_sphere = create_sphere_wire(obj, wire_sphere_name)
    
    # Show/hide based on current shape
    if ps.emission_shape == 'BOX':
        # Parent to emitter with identity inverse so local origin = emitter origin
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
    
    # Create bmesh
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
    
    # Create bmesh (UNIT sphere)
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
    
    max_particles: bpy.props.IntProperty(name="Max Particles", default=100, min=1, max=1000, update=update_game_prop)
    emission_rate: bpy.props.FloatProperty(name="Emission Rate", default=10.0, min=0.0, max=100.0, update=update_game_prop)
    
    # NEW: Delay for Burst Mode
    emission_delay: bpy.props.FloatProperty(name="Burst Delay", description="Time between bursts (seconds)", default=1.0, min=0.1, max=100.0, update=update_game_prop)
    
    burst_count: bpy.props.IntProperty(name="Burst Count", default=30, min=1, max=500, update=update_game_prop)
    is_one_shot: bpy.props.BoolProperty(name="One Shot", description="Fire once when triggered, reset when trigger stops", default=False, update=update_game_prop)
    
    lifetime: bpy.props.FloatProperty(name="Lifetime", default=3.0, min=0.1, max=100.0, update=update_game_prop)
    lifetime_random: bpy.props.FloatProperty(name="Random Lifetime", default=0.5, min=0.0, max=1.0, update=update_game_prop)
    start_size: bpy.props.FloatProperty(name="Start Size", default=0.1, min=0.001, max=10.0, update=update_game_prop)
    end_size: bpy.props.FloatProperty(name="End Size", default=0.05, min=0.001, max=10.0, update=update_game_prop)
    
    start_velocity: bpy.props.FloatVectorProperty(name="Start Velocity", default=(0.0, 0.0, 2.0), size=3, update=update_game_prop)
    velocity_random: bpy.props.FloatProperty(name="Random Velocity", default=0.5, min=0.0, max=7.0, update=update_game_prop)
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
    
    def particle_mesh_poll(self, object):
        """Only allow MESH objects as particle mesh"""
        return object.type == 'MESH'
    
    particle_mesh: bpy.props.PointerProperty(
        name="Particle Mesh", 
        type=bpy.types.Object, 
        poll=particle_mesh_poll,
        update=update_game_prop
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
        
        # ALLOWED: Mesh, Light, Empty (all types)
        # REJECTED: Camera, Curve, Surface, Meta, Text, Armature, Lattice, Speaker, etc.
        allowed_types = {'MESH', 'LIGHT', 'EMPTY'}
        return obj.type in allowed_types
    
    def draw(self, context):
        layout = self.layout
        obj = context.object
        
        if obj is None: 
            return
        
        # Double-check object type (safety)
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
            box.prop(ps, "start_size")
            box.prop(ps, "end_size")
            
            # Lock particle mesh during preview to prevent crashes
            mesh_row = box.row()
            mesh_row.enabled = not ps.preview_active  # Disable if preview is running
            mesh_row.prop(ps, "particle_mesh")
            if ps.preview_active:
                box.label(text="(Mesh locked during preview)", icon='LOCKED')
            
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
            else:  # FORCE mode
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

class PARTICLE_OT_preview_toggle(bpy.types.Operator):
    """Toggle viewport particle preview"""
    bl_idname = "particle.preview_toggle"
    bl_label = "Toggle Particle Preview"
    
    _timer = None
    _particles = None       # Initialized per-instance in execute()
    _time_accumulator = 0.0
    _last_time = 0.0
    _burst_timer = 0.0
    _burst_triggered = False
    _original_object = None  # Track which object started the preview
    _default_sphere = None   # Initialized per-instance in execute()
    
    def modal(self, context, event):
        # Check if user pressed P (start game) - auto-stop preview
        if event.type == 'P' and event.value == 'PRESS':
            self.cancel(context)
            return {'CANCELLED'}
        
        if event.type == 'TIMER':
            # Check if active object changed - auto-stop preview
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
                acc          = (force_vec + gravity) * dt   # combined acceleration per frame
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
                particle_obj, age, lifetime, start_size, end_size, velocity, angular_velocity, rotation = particle_data
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

                # Rotation
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

                self._particles[i] = (particle_obj, age, lifetime, start_size, end_size, velocity, angular_velocity, rotation)

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

        else:  # POINT — use matrix translation to respect parent transforms
            spawn_pos = mat.translation.copy()
        
        # Create particle mesh INSTANCE (Alt+D - linked duplicate)
        if ps.particle_mesh:
            # Use copy() for object but SHARE mesh data (Alt+D method)
            particle_obj = ps.particle_mesh.copy()
            particle_obj.data = ps.particle_mesh.data  # Share mesh data (no .copy()!)
        else:
            # Create default sphere (only once per preview session, then reuse)
            if self._default_sphere is None or self._default_sphere.name not in bpy.data.objects:
                prev_active = context.view_layer.objects.active
                bpy.ops.mesh.primitive_uv_sphere_add(radius=0.05, location=(0, 0, 0))
                self._default_sphere = context.view_layer.objects.active
                # Restore original active object
                context.view_layer.objects.active = prev_active
            # Instance the default sphere
            particle_obj = self._default_sphere.copy()
            particle_obj.data = self._default_sphere.data  # Share mesh data
        
        # Link to scene
        context.collection.objects.link(particle_obj)
        
        # Set initial properties with calculated spawn position
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
        
        # Store particle data: (obj, age, lifetime, start_size, end_size, velocity, angular_velocity, rotation_xyz)
        self._particles.append((particle_obj, 0.0, lifetime, ps.start_size, ps.end_size, velocity, Vector((0.0, 0.0, 0.0)), (0.0, 0.0, 0.0)))
    
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
        script_text = """# UPBGE Particle System Runtime v0.9.0 - OPTIMIZED

import bge
from bge import logic
from mathutils import Vector
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

    # ------------------------------------------------------------------
    # Pool management
    # ------------------------------------------------------------------
    def create_particle_template(self):
        scene = logic.getCurrentScene()
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
            spawn_pos = emitter_pos + (emitter_ori @ spawn_local_offset)

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
            spawn_pos = emitter_pos + (emitter_ori @ spawn_local_offset)

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

        # Spawn logic
        if props['enabled']:
            mode    = props['emission_mode']
            trigger = props['trigger']

            if mode == 'CONTINUOUS':
                if trigger:
                    self.time_since_emit += dt
                    rate = props['emission_rate']
                    interval = 1.0 / rate if rate > 0 else float('inf')
                    while self.time_since_emit >= interval:
                        self.emit_particle()
                        self.time_since_emit -= interval

            elif mode == 'BURST':
                if props['is_one_shot']:
                    if trigger and not self.burst_triggered:
                        self.emit_burst()
                        self.burst_triggered = True
                    elif not trigger:
                        self.burst_triggered = False
                else:
                    if trigger:
                        self.time_since_emit += dt
                        if self.time_since_emit >= props['emission_delay']:
                            self.emit_burst()
                            self.time_since_emit = 0.0

        # --- Particle update loop (hot path) ---
        acc              = self._acc           # pre-built acceleration vector
        is_local         = self._is_local
        is_force         = self._is_force
        damping_factor   = self._damping_factor
        enable_collision = self._enable_collision
        bounce           = self._bounce
        size_start       = self._size_start
        size_delta       = self._size_delta
        rot_has_value    = self._rot_has_value
        emitter_pos      = self.emitter.worldPosition
        emitter_ori      = self.emitter.worldOrientation

        if is_force:
            torque_rad   = self._torque_rad
            damping_fac  = self._damping_factor

        has_torque   = self._has_torque
        if not is_force and rot_has_value:
            rot_rad = self._rot_rad

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

            # Position integration
            if is_local:
                p.local_offset += p.velocity * dt
                p.position.x = emitter_pos.x + emitter_ori[0][0]*p.local_offset.x + emitter_ori[0][1]*p.local_offset.y + emitter_ori[0][2]*p.local_offset.z
                p.position.y = emitter_pos.y + emitter_ori[1][0]*p.local_offset.x + emitter_ori[1][1]*p.local_offset.y + emitter_ori[1][2]*p.local_offset.z
                p.position.z = emitter_pos.z + emitter_ori[2][0]*p.local_offset.x + emitter_ori[2][1]*p.local_offset.y + emitter_ori[2][2]*p.local_offset.z
            else:
                p.position += p.velocity * dt

            # Collision
            if enable_collision and p.obj:
                # Cast forward from current position to next frame position.
                # rayCast(to, from, dist) — order matters.
                next_pos = p.position + p.velocity * dt
                distance = p.velocity.length * dt
                if distance > 0:
                    hit_obj, hit_pos, hit_normal = p.obj.rayCast(
                        next_pos,    # to   — where the particle is heading
                        p.position,  # from — where the particle is now
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

                # Rotation — only write worldOrientation when there is actual rotation.
                # worldOrientation triggers an internal matrix decomposition in UPBGE
                # so skipping it when unused saves meaningful cost per particle per frame.
                if is_force and has_torque:
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
        print("PARTICLE SYSTEM v0.8.0 - OBJECT POOLING")
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
        
        # Property Creation - only adds missing props, never overwrites existing ones
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
classes = (
    ParticleSystemProperties,
    PARTICLE_PT_upbge_panel,
    PARTICLE_OT_preview_toggle,
    PARTICLE_OT_setup_logic,
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