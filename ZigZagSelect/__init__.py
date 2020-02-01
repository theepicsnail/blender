bl_info = {
    "name": "Zig Zag Select",
    "category": "Object",
    'blender': (2, 80, 0),
}
print("B")
import bpy
import bmesh


class ZigZagSelect(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "edge.zigzag"
    bl_label = "Zig Zag Select"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return context.mode == 'EDIT_MESH'

    def execute(self, context):
        obj = context.active_object

        me = obj.data
        bm = bmesh.from_edit_mesh(me)

        zigzag = []  # type: list[bmesh.types.BMEdge]
        for e in bm.edges:
            if e.select:
                zigzag.append(e)
        assert len(zigzag) == 2, "Expected exactly 2 edges selected"
        assert len(set(zigzag[0].verts) | set(zigzag[1].verts)) == 3, "Expected edges to be connected."
        faces = list(set(zigzag[0].link_faces) & set(zigzag[1].link_faces))
        assert len(faces) == 1, "Expected edges to share a face."
        def selectZigZag(prevEdge, face, edge):
            for i in range(1000):
                if len(edge.link_faces) != 2:
                    print("Stopping, edge does not have 2 faces.")
                    break
                nextFace = [f for f in edge.link_faces if f != face][0]
                nextEdge = [e for e in nextFace.edges if len(set(prevEdge.verts) & set(e.verts)) == 0][0]
                if nextEdge.select:
                    print("Hit selected edge")
                    nextFace.select = True
                    break
                nextFace.select = True
                nextEdge.select = True

                prevEdge = edge
                edge = nextEdge
                face = nextFace

        faces[0].select = True
        selectZigZag(zigzag[0], faces[0], zigzag[1])
        selectZigZag(zigzag[1], faces[0], zigzag[0])


        bmesh.update_edit_mesh(me)
        me.update()

        return {'FINISHED'}


def register():
    print("ZigZagSelect register")
    bpy.utils.register_class(ZigZagSelect)


def unregister():
    bpy.utils.unregister_class(ZigZagSelect)


if __name__ == "__main__":
    try:
        unregister()
    except:
        pass
    register()
