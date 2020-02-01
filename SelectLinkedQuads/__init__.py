bl_info = {
    "name": "Select linked quads",
    "category": "Object",
    'blender': (2, 80, 0),
}
import bpy
import bmesh


class SelectLinkedQuads(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "object.select_linked_quads"
    bl_label = "Select linked quads"

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    def execute(self, context):
        obj = context.active_object

        me = obj.data
        bm = bmesh.from_edit_mesh(me)

        to_explore = []

        def select_face(face):
            face.select = True
            for edge in face.edges:
                for f in edge.link_faces:
                    if f != face:
                        to_explore.append(f)

        for face in bm.faces:
            if face.select:
                select_face(face)

        while to_explore:
            print(len(to_explore))
            f = to_explore.pop(0)
            if f.select:
                continue
            if len(f.edges) == 4:
                select_face(f)

        bmesh.update_edit_mesh(me)
        me.update()

        return {'FINISHED'}


def register():
    bpy.utils.register_class(SelectLinkedQuads)


def unregister():
    bpy.utils.unregister_class(SelectLinkedQuads)


if __name__ == "__main__":
    try:
        unregister()
    except:
        pass
    register()
