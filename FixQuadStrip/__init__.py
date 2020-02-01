from typing import List

bl_info = {
    "name": "Fix quad strip",
    "category": "Object",
    'blender': (2, 80, 0),
}
import bpy
import bmesh


class FixQuadStrip(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "object.fix_quad_strip"
    bl_label = "Fix Quad Strip"

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    def execute(self, context):
        obj = context.active_object

        bm = bmesh.from_edit_mesh(obj.data)
        faces = [i for i in bm.faces if i.select]

        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='EDGE')

        # print(faces)
        count = 10000
        while count > 0:
            count -= 1

            for face in faces:
                # count neighboring selected faces.
                selected_neighbors = 0
                middle_edge = None
                other_face = None
                for edge in face.edges:
                    for neighbor in edge.link_faces:
                        if neighbor == face:
                            continue
                        if neighbor in faces:
                            selected_neighbors += 1
                            middle_edge = edge
                            other_face = neighbor

                if selected_neighbors == 1:
                    middle_edge.select = True
                    faces.remove(face)
                    faces.remove(other_face)
                    break
            else:
                print("Failed to find end to cleanup.")
                break
        print(count)
        bpy.ops.mesh.dissolve_edges()
        return {'FINISHED'}


def register():
    bpy.utils.register_class(FixQuadStrip)


def unregister():
    bpy.utils.unregister_class(FixQuadStrip)


if __name__ == "__main__":
    try:
        unregister()
    except:
        pass
    register()
    bpy.ops.object.fix_quad_strip()
