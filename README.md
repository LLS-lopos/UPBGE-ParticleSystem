# UPBGE Particle System
It's an addon design for UPBGE 0.5+ to create particle effects for your game without doing it from scratch, and it creates with the help of AI
## Features
+ Integrated directly into **The physics properties** for easy access
+ Two emission modes **Continuous**, **Burst** and **Rate Over Time**
+ Customization settings to create wide style options
+ Billboard or mesh can be a particle allowing for total creative freedom
+ Controlling the system with an emission trigger for smart use by toggle **ps_tigger** bool property
+ Preview mode allows you to debug your particles in the viewport without starting the game
+ Emission shape opens more possibilities to create effects
+ The system support color over lifetime, alpha and textures and you can control them with a curve
+ Prepare your shader and apply it with one button

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
7. Check the "Play On Awake" checkbox 
8. Press P and enjoy!

> [!TIP]
You can control the particle spawning with *Logic Brick* or *Logic nodes* by using **ps_trigger** bool property

> [!WARNING]
The performance can be an issue since the Add-on uses CPU in complex effects, but to optimize and deliver the best performance, follow these steps:
1. Select the object you want to use as a particle
2. Go to **object properties** and enable ***UPBGE Dupli Base***
3. Change the physics properties to **No Collision** and uncheck **Sound Occluder**
4. If you want to use textures I highly recommend using the *DDS* format
5. If you use mesh as a particle try using simple object geometry, or reduce the **Emission Rate**
6. Use the LOD system
7. Enable System launcher

## Documentation 
Coming soon

## Contributing
Contributors are very welcome. If you decide to contribute, please follow these rules:
1. Fixing bugs, adding new features or anything that touches the code, given in the form of Pull Requests
2. You are allowed to use AI for coding, suggest a new feature or anything else, make sure you understand the concept and how it works in UPBGE in general
3. Reviewing Pull Requests takes at least 3 days or more, based on how big the changes are
4. Any implementations must come with reasons and how important they are for the particle system
5. Anything unrelated to the particle system will not be accepted

## Discord Server
Join the community in the Discord server https://discord.gg/842uWxchu7

## Report bugs
If you face any bugs, please report them in issues 

Enjoy!
