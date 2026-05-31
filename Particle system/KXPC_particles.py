# KX PythonComponent
# Particles System

import bge, bpy, random
from collections import OrderedDict
from mathutils import Vector, Euler

class ParticleSystem(bge.types.KX_PythonComponent):
    args = OrderedDict([
        ("Activate particles", False),
        ("Mode", {"Countinuous", "Burst"}),
        ("Max Particles", 20),
        ("Emission Rate", 1.0),
        ("Lifetime", 1.0),
        ("Random Lifetime", 1.0),
        ("Emission Trigger", False),
        ("Emission Delay", 1.0),
        ("is one shot", False),
        ("Start Size", 1.0),
        ("End Size", 1.0),
        ("Object Particle", bpy.types.Object),
        ("Start Velocity", (0.0, 0.0, 1.0)),
        ("Random Velocity", 0.0),
        ("Start Rotation", (0.0, 0.0, 0.0)),
        ("Random Rotation", 0.0),
        ("Gravity", (0.0, 0.0, -9.80)),
    ])

    def start(self, args):
        self.activate = args["Activate particles"]
        self.mode = args["Mode"]
        self.particle_max = args["Max Particles"]
        self.emission_rate = args["Emission Rate"]
        self.lifetime = args["Lifetime"]
        self.random_lifetime = args["Random Lifetime"]
        self.emission_trigger = args["Emission Trigger"]
        self.emission_delay = args["Emission Delay"]
        self.one_shot = args["is one shot"]
        self.start_size = args["Start Size"]
        self.end_size = args["End Size"]
        self.object_particle = args["Object Particle"]
        self.start_velocity = args["Start Velocity"]
        self.random_velocity = args["Random Velocity"]
        self.start_rotation = args["Start Rotation"]
        self.random_rotation = args["Random Rotation"]
        self.gravity = Vector(args["Gravity"])

        self.particles = []
        self.time_since_emit = 0.0
        self.time_since_burst = 0.0
        self.burst_triggered = False
        self.last_time = bge.logic.getClockTime()
        self.scene = bge.logic.getCurrentScene()

    def check_mode(self, dt):
        if self.mode == "Countinuous":
            if self.emission_trigger:
                self.time_since_emit += dt
                interval = 1.0 / self.emission_rate if self.emission_rate > 0 else float('inf')
                while self.time_since_emit >= interval:
                    self.emit_particle()
                    self.time_since_emit -= interval

        elif self.mode == "Burst":
            if self.one_shot:
                if self.emission_trigger and not self.burst_triggered:
                    for _ in range(self.particle_max):
                        self.emit_particle()
                    self.burst_triggered = True
                elif not self.emission_trigger:
                    self.burst_triggered = False
            else:
                if self.emission_trigger:
                    self.time_since_burst += dt
                    if self.time_since_burst >= self.emission_delay:
                        for _ in range(self.particle_max):
                            self.emit_particle()
                        self.time_since_burst = 0.0
                else:
                    self.time_since_burst = 0.0

    def compute_lifetime(self):
        return self.lifetime * (1.0 + (random.random() - 0.5) * self.random_lifetime)

    def compute_velocity(self):
        base_vel = Vector(self.start_velocity)
        random_offset = Vector((
            (random.random() - 0.5) * 2 * self.random_velocity,
            (random.random() - 0.5) * 2 * self.random_velocity,
            (random.random() - 0.5) * 2 * self.random_velocity
        ))
        return base_vel + random_offset

    def compute_rotation(self):
        base_vel = Vector(self.start_rotation)
        random_offset = Vector((
            (random.random() - 0.5) * 2 * self.random_rotation,
            (random.random() - 0.5) * 2 * self.random_rotation,
            (random.random() - 0.5) * 2 * self.random_rotation
        ))
        return base_vel + random_offset

    def compute_size(self, age, lifetime):
        life_ratio = age / lifetime
        return self.start_size + (self.end_size - self.start_size) * life_ratio

    def emit_particle(self):
        if not self.object_particle:
            return
        if len(self.particles) >= self.particle_max:
            old_particle = self.particles.pop(0)
            if old_particle["obj"]:
                old_particle["obj"].endObject()

        particle = {
            "position": self.object.worldPosition.copy(),
            "velocity": self.compute_velocity(),
            "rotation": Euler(self.compute_rotation()),  # rotation initiale en Euler
            "angular_velocity": Euler(self.compute_rotation()),  # vitesse angulaire
            "age": 0.0,
            "lifetime": self.compute_lifetime(),
            "size": self.start_size,
            "obj": None
        }
        try:
            particle["obj"] = self.scene.addObject(self.object_particle.name, self.object, 0)
            particle["obj"].worldPosition = particle["position"]
            particle["obj"].worldOrientation = particle["rotation"].to_matrix()
            particle["obj"].worldScale = [particle["size"]] * 3
            self.particles.append(particle)
        except Exception as e:
            print("Erreur lors de la création de la particule :", e)

    def update_particles(self, dt):
        grav = self.gravity
        to_remove = []
        for i, p in enumerate(self.particles):
            p["age"] += dt
            if p["age"] >= p["lifetime"]:
                if p["obj"]:
                    p["obj"].endObject()
                to_remove.append(i)
                continue
            p["velocity"] += grav * dt
            p["position"] += p["velocity"] * dt
            p["rotation"] = Euler((
                p["rotation"].x + p["angular_velocity"].x * dt,
                p["rotation"].y + p["angular_velocity"].y * dt,
                p["rotation"].z + p["angular_velocity"].z * dt
            ))
            if p["obj"]:
                p["obj"].worldPosition = p["position"]
                p["obj"].worldOrientation = p["rotation"].to_matrix()
                p["size"] = self.compute_size(p["age"], p["lifetime"])
                p["obj"].worldScale = [p["size"]] * 3
        for i in reversed(to_remove):
            self.particles.pop(i)

    def update(self):
        current_time = bge.logic.getClockTime()
        dt = current_time - self.last_time
        self.last_time = current_time

        if not self.activate:
            return
        self.check_mode(dt)
        self.update_particles(dt)
