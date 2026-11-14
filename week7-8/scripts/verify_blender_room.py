"""Run with Blender --background room_301.blend --python this.py -- --out DIR."""
import bpy
import json
import math
import os
import sys
from mathutils import Vector

args=sys.argv[sys.argv.index('--')+1:]
out=os.path.abspath(args[args.index('--out')+1])
os.makedirs(out,exist_ok=True)
scene=bpy.context.scene
door=bpy.data.objects['Door_Leaf']
assert abs(door.dimensions.z-2.1)<1e-5
assert abs(door.rotation_euler.z-math.pi/2)<1e-5
assert abs(bpy.data.objects['Room_Floor'].dimensions.x-12)<1e-5
assert abs(bpy.data.objects['Room_Floor'].dimensions.y-7)<1e-5
walls=[]
for obj in bpy.data.objects:
    if obj.name.startswith('Room_Wall_Right') or obj.name=='Door_Lintel':
        vertices=[obj.matrix_world@Vector(v) for v in obj.bound_box]
        bounds={axis:[min(v[i] for v in vertices),max(v[i] for v in vertices)] for i,axis in enumerate('xyz')}
        # No wall box can overlap the interior of the opening.
        overlaps_y=bounds['y'][0]<-1.65-1e-5 and bounds['y'][1]>-2.7+1e-5
        overlaps_z=bounds['z'][0]<2.1-1e-5 and bounds['z'][1]>1e-5
        assert not (overlaps_y and overlaps_z),obj.name
        walls.append({'name':obj.name,'bounds':bounds})
people=[o for o in bpy.data.objects if o.name.startswith('Person_')]
lamps=[o for o in bpy.data.objects if o.name.startswith('CeilingLight_')]
cameras=[o for o in bpy.data.objects if o.type=='CAMERA']
assert len(people)==8 and len(lamps)==3 and len(cameras)==3
assert all(o.get('state_key')=='people_count' for o in people)
result={'blender_version':bpy.app.version_string,'blend_file':os.path.basename(bpy.data.filepath),
        'checks_passed':['12x7m floor','2.1m hinged door','wall opening has no blocking box','8 people anchors','3 lamp anchors','3 authored cameras'],
        'door_opening':{'axis':'Blender Y','min':-2.7,'max':-1.65,'height':2.1},'walls':walls,
        'object_count':len(bpy.data.objects),'render':'blender-native.png'}
with open(os.path.join(out,'blender-verification.json'),'w',encoding='utf-8') as f: json.dump(result,f,ensure_ascii=False,indent=2)
scene.render.engine='BLENDER_WORKBENCH'
scene.display.shading.light='STUDIO'
scene.display.shading.color_type='MATERIAL'
scene.display.shading.show_shadows=True
scene.render.resolution_x=1280;scene.render.resolution_y=800;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.render.filepath=os.path.join(out,'blender-native.png')
bpy.ops.render.render(write_still=True)
print(json.dumps(result,ensure_ascii=False))
