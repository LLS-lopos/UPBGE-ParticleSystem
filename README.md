# UPBGE Particle System
It's an addon design for UPBGE 0.5+ to create particle effects for your game without doing it from scratch, and it creates with the help of AI
## Features
+ Integrated directly into **The physics properties** for easy access
+ Two emission modes **continuous** and **burst**
+ Customization settings to create wide style options
+ Billboard or mesh can be a particle allowing for total creative freedom
+ Controlling the system with an emission trigger for smart use by toggle **ps_tigger** bool property
+ Preview mode allows you to debug your particles in the viewport without starting the game
+ Emission shape opens more possibilities to create effects
+ The system support color over lifetime, alpha and textures

## Installation guide
1. Download the addon 
2. Go to **Edit** -> **preferences** -> **Add-on** -> **Add-on settings** -> **Install from disk**
3. Locate the zip <sub>Particle system</sub> file and select it
4. Click on the checkbox to activate the Add-on

## Quick setup
1. Add empty
2. Go to physics properties 
3. Enable the option "Particle Emitter"
4. Choose a particle type *Billboard* or *Mesh*
5. Hide the object by selecting it and pressing H or clicking on the eye in the outliner
6. Click on "Initialize"
7. Check the "Emission trigger" checkbox 
8. Press P and enjoy!

> [!TIP]
You can control the particle spawning with *Logic Brick* or *Logic nodes* by using **ps_tigger** bool property

> [!WARNING]
The performance is not great since the Add-on uses CPU, but to deliver the best performance, follow these steps:
1. Select the object you want to use as a particle
2. Go to **object properties** and enable ***UPBGE Dupli Base***
3. Change the physics properties to **No Collision** and uncheck **Sound Occluder**
4. If you want to use textures i highly recommend to use *DDS* format
5. Try using simple object geometry if you choose mesh or reduce the **Emission Rate**
6. Use LOD system to improve the performance 

## Documentation 
Coming soon

## Discord Server
If you want to join the community, go to the Discord server https://discord.gg/842uWxchu7

## Report bugs
If you face any bug please report it on GitHub

Enjoy!
