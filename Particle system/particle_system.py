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

# Wire shape visualization - OPTIMIZED
def update_wire_shape(self, context):
    """Update wire shape visualization - uses scale, not mesh regeneration"""
    obj = context.object
    if not obj:
        return
    
    wire_name = f"PS_Wire_{obj.name}"
    ps = obj.particle_system_props
    
    # Remove wire if disabled or POINT shape
    if not ps.enabled or ps.emission_shape == 'POINT':
        if wire_name in bpy.data.objects:
            wire_obj = bpy.data.objects[wire_name]
            bpy.data.objects.remove(wire_obj, do_unlink=True)
        update_game_prop(self, context)
        return
    
    # Check if wire already exists
    wire_obj = bpy.data.objects.get(wire_name)
    
    # Create wire if it doesn't exist or shape type changed
    needs_new_mesh = False
    if not wire_obj:
        needs_new_mesh = True
    elif wire_obj.get('ps_shape_type') != ps.emission_shape:
        # Shape type changed, remove old and create new
        bpy.data.objects.remove(wire_obj, do_unlink=True)
        needs_new_mesh = True
    
    if needs_new_mesh:
        import bmesh
        
        # Create base mesh (unit size)
        mesh = bpy.data.meshes.new(f"PS_WireMesh_{obj.name}")
        wire_obj = bpy.data.objects.new(wire_name, mesh)
        
        # Store shape type
        wire_obj['ps_shape_type'] = ps.emission_shape
        
        # Link to collection
        context.collection.objects.link(wire_obj)
        
        # Parent to emitter - reset local transform so wire sits exactly at emitter center.
        # Using matrix_world.inverted() here would bake the emitter's current world offset
        # into the parent inverse, causing the wire to drift when the emitter has been moved.
        # Instead we zero the local location and use an identity parent inverse so the wire
        # always stays perfectly centered on the emitter regardless of its world position.
        wire_obj.parent = obj
        wire_obj.matrix_parent_inverse.identity()
        wire_obj.location = (0.0, 0.0, 0.0)
        wire_obj.rotation_euler = (0.0, 0.0, 0.0)
        
        # Create bmesh
        bm = bmesh.new()
        
        if ps.emission_shape == 'BOX':
            # Create UNIT box (1x1x1) - we'll scale it later
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
            
            # Create edges
            edges = [
                (0,1), (1,2), (2,3), (3,0),  # Bottom
                (4,5), (5,6), (6,7), (7,4),  # Top
                (0,4), (1,5), (2,6), (3,7),  # Vertical
            ]
            for e in edges:
                bm.edges.new((verts[e[0]], verts[e[1]]))
                
        elif ps.emission_shape == 'SPHERE':
            # Create UNIT sphere (radius 1.0) - we'll scale it later
            segments = 32
            import math
            
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
        
        # Write bmesh to mesh
        bm.to_mesh(mesh)
        bm.free()
        
        # Set display properties
        wire_obj.display_type = 'WIRE'
        wire_obj.show_in_front = True
        wire_obj.hide_render = True
        wire_obj.hide_select = True
        wire_obj.color = (0, 1, 1, 1)  # Cyan
    
    # Update scale based on size (OPTIMIZED - no mesh regeneration!)
    if wire_obj:
        if ps.emission_shape == 'BOX':
            # Box: Scale XYZ independently
            wire_obj.scale = ps.emission_box_size
        elif ps.emission_shape == 'SPHERE':
            # Sphere: Uniform scale on all axes
            radius = ps.emission_sphere_radius
            wire_obj.scale = (radius, radius, radius)
    
    # Update game properties
    update_game_prop(self, context)

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
            box.prop(ps, "start_velocity")
            box.prop(ps, "rotation")
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
    _particles = []
    _time_accumulator = 0.0
    _last_time = 0.0
    _burst_timer = 0.0
    _burst_triggered = False
    _original_object = None  # Track which object started the preview
    
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
            to_remove = []
            for i, particle_data in enumerate(self._particles):
                particle_obj, age, lifetime, start_size, end_size, velocity, rotation = particle_data
                age += dt
                
                if age >= lifetime:
                    to_remove.append(i)
                    bpy.data.objects.remove(particle_obj, do_unlink=True)
                    continue
                
                # Physics
                gravity = Vector(ps.gravity)
                velocity += gravity * dt
                
                # Collision detection (simplified for preview - ground plane only)
                if ps.enable_collision:
                    next_pos = particle_obj.location + velocity * dt
                    
                    # Simple ground collision (Z = 0)
                    if next_pos.z < 0:
                        # Hit ground
                        velocity.z = -velocity.z * ps.bounce_strength
                        next_pos.z = 0.01  # Prevent going below ground
                        particle_obj.location = next_pos
                    else:
                        particle_obj.location += velocity * dt
                else:
                    particle_obj.location += velocity * dt
                
                # Size interpolation
                life_ratio = age / lifetime
                size = start_size + (end_size - start_size) * life_ratio
                particle_obj.scale = Vector((size, size, size))
                
                # Rotation (XYZ)
                if ps.rotation[0] != 0 or ps.rotation[1] != 0 or ps.rotation[2] != 0:
                    import math
                    # Calculate rotation speed for each axis
                    rotation_speed_x = math.radians(ps.rotation[0]) / lifetime
                    rotation_speed_y = math.radians(ps.rotation[1]) / lifetime
                    rotation_speed_z = math.radians(ps.rotation[2]) / lifetime
                    
                    # Update rotation (rotation is now Vector with x, y, z)
                    rotation_x = rotation[0] + rotation_speed_x * dt
                    rotation_y = rotation[1] + rotation_speed_y * dt
                    rotation_z = rotation[2] + rotation_speed_z * dt
                    
                    # Apply rotation to all axes
                    particle_obj.rotation_euler.x = rotation_x
                    particle_obj.rotation_euler.y = rotation_y
                    particle_obj.rotation_euler.z = rotation_z
                    
                    # Update rotation tuple
                    rotation = (rotation_x, rotation_y, rotation_z)
                
                # Update particle data (rotation is now a tuple of 3 floats)
                self._particles[i] = (particle_obj, age, lifetime, start_size, end_size, velocity, rotation)
            
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
            bpy.data.objects.remove(old_particle[0], do_unlink=True)
        
        # Create particle mesh INSTANCE (Alt+D - linked duplicate)
        if ps.particle_mesh:
            # Use copy() for object but SHARE mesh data (Alt+D method)
            particle_obj = ps.particle_mesh.copy()
            particle_obj.data = ps.particle_mesh.data  # Share mesh data (no .copy()!)
        else:
            # Create default sphere (only first time, then reuse)
            if not hasattr(self, '_default_sphere'):
                bpy.ops.mesh.primitive_uv_sphere_add(radius=0.05, location=(0, 0, 0))
                self._default_sphere = context.active_object
                context.view_layer.objects.active = obj
            # Instance the default sphere
            particle_obj = self._default_sphere.copy()
            particle_obj.data = self._default_sphere.data  # Share mesh data
        
        # Link to scene
        context.collection.objects.link(particle_obj)
        
        # Set initial properties
        particle_obj.location = obj.location.copy()
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
        
        # Store particle data: (object, age, lifetime, start_size, end_size, velocity, rotation_xyz)
        self._particles.append((particle_obj, 0.0, lifetime, ps.start_size, ps.end_size, velocity, (0.0, 0.0, 0.0)))
    
    def execute(self, context):
        obj = context.object
        ps = obj.particle_system_props
        
        if ps.preview_active:
            # Stop preview
            ps.preview_active = False
            self.cancel(context)
            return {'CANCELLED'}
        else:
            # Start preview
            ps.preview_active = True
            self._particles = []
            self._time_accumulator = 0.0
            self._last_time = 0.0
            self._burst_timer = 0.0
            self._burst_triggered = False
            self._original_object = obj  # Track which object started preview
            
            wm = context.window_manager
            self._timer = wm.event_timer_add(0.016, window=context.window)
            wm.modal_handler_add(self)
            return {'RUNNING_MODAL'}
    
    def cancel(self, context):
        wm = context.window_manager
        if self._timer:
            wm.event_timer_remove(self._timer)
        
        # Clean up all particles
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
        
        # Logic Bricks
        has_sensor = any(s.name == "ParticleInit" for s in init_obj.game.sensors)
        if not has_sensor:
            bpy.ops.logic.sensor_add(type='ALWAYS', name="ParticleInit", object=init_obj.name)
            init_obj.game.sensors[-1].name = "ParticleInit"
            init_obj.game.sensors[-1].use_pulse_true_level = False
            
        for ctrl in list(init_obj.game.controllers):
            if "Particle" in ctrl.name:
                init_obj.game.controllers.remove(ctrl)
        
        bpy.ops.logic.controller_add(type='PYTHON', name="ParticleController", object=init_obj.name)
        controller = init_obj.game.controllers[-1]
        controller.name = "ParticleController"
        controller.mode = 'SCRIPT'
        
        # Runtime Script with OBJECT POOLING for performance
        script_text = """# UPBGE Particle System Runtime v0.8.0 - OBJECT POOLING

import bge
from bge import logic
from mathutils import Vector
import random
class Particle:
    def __init__(self, pos, vel, lifetime, size, local_offset=None):
        self.position = Vector(pos)
        self.velocity = Vector(vel)
        self.age = 0.0
        self.lifetime = lifetime
        self.size = size
        self.obj = None
        self.rotation = Vector((0.0, 0.0, 0.0))
        self.local_offset = Vector(local_offset) if local_offset else Vector((0, 0, 0))
        self.is_active = False  # POOLING: Track if particle is in use

class ParticleSystem:
    def __init__(self, emitter_obj):
        self.emitter = emitter_obj
        self.particle_pool = []  # POOLING: Pre-allocated particle pool
        self.time_since_emit = 0.0
        self.particle_template = None
        self.burst_triggered = False
        self.props = {}
        self.load_properties()
        self.create_particle_template()
        self.initialize_pool()  # POOLING: Pre-create all particles
        
    def load_properties(self):
        obj = self.emitter
        self.props = {
            'enabled': obj.get('ps_enabled', True),
            'trigger': obj.get('ps_trigger', True),
            'emission_mode': obj.get('ps_emission_mode', 'CONTINUOUS'),
            'emission_shape': obj.get('ps_emission_shape', 'POINT'),
            'emission_box_size': (obj.get('ps_emission_box_size_x', 1.0), obj.get('ps_emission_box_size_y', 1.0), obj.get('ps_emission_box_size_z', 1.0)),
            'emission_sphere_radius': obj.get('ps_emission_sphere_radius', 1.0),
            'max_particles': obj.get('ps_max_particles', 100),
            'emission_rate': obj.get('ps_emission_rate', 10.0),
            'emission_delay': obj.get('ps_emission_delay', 1.0),
            'burst_count': obj.get('ps_burst_count', 30),
            'is_one_shot': obj.get('ps_is_one_shot', False),
            'lifetime': obj.get('ps_lifetime', 3.0),
            'lifetime_random': obj.get('ps_lifetime_random', 0.5),
            'start_size': obj.get('ps_start_size', 0.1),
            'end_size': obj.get('ps_end_size', 0.05),
            'start_velocity': (obj.get('ps_start_velocity_x', 0.0), obj.get('ps_start_velocity_y', 0.0), obj.get('ps_start_velocity_z', 2.0)),
            'velocity_random': obj.get('ps_velocity_random', 0.5),
            'gravity': (obj.get('ps_gravity_x', 0.0), obj.get('ps_gravity_y', 0.0), obj.get('ps_gravity_z', -9.8)),
            'particle_mesh': obj.get('ps_particle_mesh', 'ParticleSphere'),
            'simulation_space': obj.get('ps_simulation_space', 'WORLD'),
            'enable_collision': obj.get('ps_enable_collision', False),
            'bounce_strength': obj.get('ps_bounce_strength', 0.5),
            'rotation': (obj.get('ps_rotation_x', 0.0), obj.get('ps_rotation_y', 0.0), obj.get('ps_rotation_z', 0.0))
        }
        
    def create_particle_template(self):
        scene = logic.getCurrentScene()
        mesh_name = self.props.get('particle_mesh', 'ParticleSphere')
        if mesh_name in scene.objectsInactive:
            self.particle_template = scene.objectsInactive[mesh_name]
            print(f"✓ Template: {mesh_name}")
        else:
            print(f"✗ ERROR: '{mesh_name}' not in objectsInactive!")
    
    def initialize_pool(self):
        '''POOLING: Pre-allocate all particles at startup'''
        if not self.particle_template:
            return
        
        scene = logic.getCurrentScene()
        max_particles = self.props['max_particles']
        
        print(f"Creating particle pool: {max_particles} particles...")
        
        for i in range(max_particles):
            # Create particle data
            p = Particle(Vector((0, 0, 0)), Vector((0, 0, 0)), 1.0, 0.1)
            p.is_active = False
            
            # Pre-instantiate mesh object
            try:
                p.obj = scene.addObject(self.particle_template, self.emitter, 0)
                p.obj.worldScale = [0.0, 0.0, 0.0]  # Hide it
                p.obj.visible = False  # Extra hiding
            except Exception as e:
                print(f"Pool creation error: {e}")
                continue
            
            self.particle_pool.append(p)
        
        print(f"✓ Pool ready: {len(self.particle_pool)} particles")
    
    def get_inactive_particle(self):
        '''POOLING: Find first inactive particle in pool'''
        for p in self.particle_pool:
            if not p.is_active:
                return p
        return None  # Pool exhausted
            
    def emit_particle(self):
        '''POOLING: Reuse particle from pool instead of creating new one'''
        # Get inactive particle from pool
        p = self.get_inactive_particle()
        if not p:
            return  # Pool is full, can't emit
        
        # Calculate spawn position based on emission shape
        emission_shape = self.props['emission_shape']
        
        if emission_shape == 'BOX':
            box_size = self.props['emission_box_size']
            local_offset = Vector((
                (random.random() - 0.5) * box_size[0],
                (random.random() - 0.5) * box_size[1],
                (random.random() - 0.5) * box_size[2]
            ))
            spawn_pos = self.emitter.worldPosition + (self.emitter.worldOrientation @ local_offset)
            
        elif emission_shape == 'SPHERE':
            radius = self.props['emission_sphere_radius']
            import math
            r = radius * (random.random() ** (1.0/3.0))
            theta = 2 * math.pi * random.random()
            phi = math.acos(2 * random.random() - 1)
            
            local_offset = Vector((
                r * math.sin(phi) * math.cos(theta),
                r * math.sin(phi) * math.sin(theta),
                r * math.cos(phi)
            ))
            spawn_pos = self.emitter.worldPosition + (self.emitter.worldOrientation @ local_offset)
            
        else:  # POINT
            spawn_pos = self.emitter.worldPosition.copy()
        
        # Calculate velocity
        base_vel = Vector(self.props['start_velocity'])
        random_offset = Vector(((random.random()-0.5)*2*self.props['velocity_random'], 
                                 (random.random()-0.5)*2*self.props['velocity_random'], 
                                 (random.random()-0.5)*2*self.props['velocity_random']))
        local_velocity = base_vel + random_offset
        
        if self.props['simulation_space'] == 'LOCAL':
            world_velocity = self.emitter.worldOrientation @ local_velocity
        else:
            world_velocity = local_velocity
        
        lifetime = self.props['lifetime'] * (1.0 + (random.random()-0.5) * self.props['lifetime_random'])
        
        # POOLING: Reset particle instead of creating new
        p.position = spawn_pos
        p.velocity = world_velocity
        p.age = 0.0
        p.lifetime = lifetime
        p.size = self.props['start_size']
        p.rotation = Vector((0.0, 0.0, 0.0))
        p.local_offset = Vector((0, 0, 0))
        p.is_active = True  # ACTIVATE
        
        # Show and position the mesh
        if p.obj:
            p.obj.worldPosition = p.position
            p.obj.worldScale = [p.size] * 3
            p.obj.visible = True
    
    def emit_burst(self):
        for _ in range(self.props['burst_count']):
            self.emit_particle()
        
    def update(self, dt):
        self.load_properties()
        
        # Spawn logic
        if self.props['enabled']:
            mode = self.props['emission_mode']
            trigger = self.props['trigger']
            
            if mode == 'CONTINUOUS':
                if trigger:
                    self.time_since_emit += dt
                    rate = self.props['emission_rate']
                    interval = 1.0 / rate if rate > 0 else float('inf')
                    while self.time_since_emit >= interval:
                        self.emit_particle()
                        self.time_since_emit -= interval
            
            elif mode == 'BURST':
                if self.props['is_one_shot']:
                    if trigger and not self.burst_triggered:
                        self.emit_burst()
                        self.burst_triggered = True
                    elif not trigger:
                        self.burst_triggered = False
                else:
                    if trigger:
                        self.time_since_emit += dt
                        if self.time_since_emit >= self.props['emission_delay']:
                            self.emit_burst()
                            self.time_since_emit = 0.0
        
        # POOLING: Only update ACTIVE particles
        grav = Vector(self.props['gravity'])
        enable_collision = self.props['enable_collision']
        bounce = self.props['bounce_strength']
        
        for p in self.particle_pool:
            if not p.is_active:  # POOLING: Skip inactive particles
                continue
            
            p.age += dt
            
            # POOLING: Deactivate instead of destroying
            if p.age >= p.lifetime:
                p.is_active = False
                if p.obj:
                    p.obj.worldScale = [0.0, 0.0, 0.0]  # Hide
                    p.obj.visible = False
                continue
            
            # Physics
            if self.props['simulation_space'] == 'LOCAL':
                local_grav = self.emitter.worldOrientation.transposed() @ grav
                p.velocity += local_grav * dt
            else:
                p.velocity += grav * dt
            
            # Collision
            if enable_collision and p.obj:
                next_pos = p.position + p.velocity * dt
                direction = next_pos - p.position
                distance = direction.length
                
                if distance > 0:
                    direction.normalize()
                    hit_obj, hit_pos, hit_normal = p.obj.rayCast(next_pos, p.position, distance)
                    
                    if hit_obj:
                        dot = p.velocity.dot(hit_normal)
                        p.velocity = p.velocity - 2 * dot * hit_normal
                        p.velocity *= bounce
                        p.position = hit_pos + hit_normal * 0.01
                    else:
                        if self.props['simulation_space'] == 'LOCAL':
                            p.local_offset += p.velocity * dt
                            p.position = self.emitter.worldPosition + (self.emitter.worldOrientation @ p.local_offset)
                        else:
                            p.position += p.velocity * dt
            else:
                if self.props['simulation_space'] == 'LOCAL':
                    p.local_offset += p.velocity * dt
                    p.position = self.emitter.worldPosition + (self.emitter.worldOrientation @ p.local_offset)
                else:
                    p.position += p.velocity * dt
            
            if p.obj:
                p.obj.worldPosition = p.position
                life_ratio = p.age / p.lifetime
                p.size = self.props['start_size'] + (self.props['end_size'] - self.props['start_size']) * life_ratio
                p.obj.worldScale = [p.size] * 3
                
                # Rotation
                rotation_xyz = self.props['rotation']
                if rotation_xyz[0] != 0 or rotation_xyz[1] != 0 or rotation_xyz[2] != 0:
                    import math
                    rotation_speed_x = math.radians(rotation_xyz[0]) / p.lifetime
                    rotation_speed_y = math.radians(rotation_xyz[1]) / p.lifetime
                    rotation_speed_z = math.radians(rotation_xyz[2]) / p.lifetime
                    
                    p.rotation.x += rotation_speed_x * dt
                    p.rotation.y += rotation_speed_y * dt
                    p.rotation.z += rotation_speed_z * dt
                    
                    p.obj.worldOrientation = [p.rotation.x, p.rotation.y, p.rotation.z]

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
        
        # Script Refresh Logic
        import time
        script_name = f"ParticleSys_Runtime_{int(time.time())}.py"
        for t in bpy.data.texts:
            if "ParticleSys_Runtime" in t.name: bpy.data.texts.remove(t)
            
        text_block = bpy.data.texts.new(script_name)
        text_block.write(script_text)
        controller.text = text_block
        
        sensor = next((s for s in init_obj.game.sensors if s.name == "ParticleInit"), None)
        if sensor: controller.link(sensor=sensor)
        
        # Property Creation
        def ensure_prop(name, type, value):
            if name not in init_obj.game.properties:
                bpy.ops.object.game_property_new(type=type, name=name)
            init_obj.game.properties[name].value = value

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
        
        # Rotation properties (XYZ)
        ensure_prop('ps_rotation_x', 'FLOAT', props.rotation[0])
        ensure_prop('ps_rotation_y', 'FLOAT', props.rotation[1])
        ensure_prop('ps_rotation_z', 'FLOAT', props.rotation[2])
        
        mesh_name = props.particle_mesh.name if props.particle_mesh else 'ParticleSphere'
        ensure_prop('ps_particle_mesh', 'STRING', mesh_name)
        
        self.report({'INFO'}, "System Initialized!")
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
    # Clean up all wire shapes
    wire_objects = [obj for obj in bpy.data.objects if obj.name.startswith("PS_Wire_")]
    for wire_obj in wire_objects:
        bpy.data.objects.remove(wire_obj, do_unlink=True)
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Object.particle_system_props

if __name__ == "__main__":
    register()