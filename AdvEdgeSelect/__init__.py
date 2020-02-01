bl_info = {
    "name": "Advanced Edge Select",
    "category": "Object",
    'blender': (2, 80, 0),
}
print("B")
import bpy
import bmesh

def ordered_edge_list(center:bmesh.types.BMVert, start:bmesh.types.BMEdge):
    out = [start]
    cur = start
    faces = list(center.link_faces)
    while len(faces):
        for f in faces:
            if cur in f.edges:
                other_edge = None
                for e in f.edges:
                    if e == cur:
                        continue
                    if center in e.verts:
                        other_edge = e
                        break
                if other_edge is None:
                    return faces
                cur = other_edge
                out.append(cur)
                faces.remove(f)
                break
    return out


class AdvancedEdgeSelect(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "object.adv_edge_select"
    bl_label = "Advanced Edge Select"
    bl_options = {'REGISTER', 'UNDO'}

    select_mesh_edge: bpy.props.BoolProperty(name="Select Mesh Edge", default=False)
    action3: bpy.props.EnumProperty(items=[
        ("0", "Stop", "Stop when a 3-way junction is hit"),
        ("1", "Both", "Continue selecting down both paths"),
    ], name="3-Way resolution", description="3-point star", default="1")

    action4: bpy.props.EnumProperty(items=[
        ("0", "Stop", "Stop when a 4-way junction is hit"),
        ("1", "Opposite", "Continue selecting down opposite edge"),
    ], name="4-Way resolution", description="Cross", default="1")

    action5: bpy.props.EnumProperty(items=[
        ("0", "Stop", "Stop when a 5-way junction is hit"),
        ("1", "All", "Continue selecting down all edges"),
    ], name="5-Way resolution", description="5-point star", default="1")

    actionEven: bpy.props.EnumProperty(items=[
        ("0", "Stop", "Stop when an even 6+way junction is hit"),
        ("1", "Opposite", "Continue selecting from the opposite edge"),
        ("2", "Every Other", "Continue selecting down every other edge"),
    ], name="6+ Even Way resolution", description="Large even", default="0")

    actionOdd: bpy.props.EnumProperty(items=[
        ("0", "Stop", "Stop when an odd 7+way junction is hit"),
        ("1", "All", "Continue selecting down all edges"),
    ], name="7+ Odd Way resolution", description="Large odd", default="0")

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return context.mode == 'EDIT_MESH'

    def execute(self, context):
        obj = context.active_object

        me = obj.data
        bm = bmesh.from_edit_mesh(me)

        to_explore = []

        def select_edge(edge: bmesh.types.BMEdge):
            if len(edge.link_faces) == 1:
                return
            edge.select = True
            for v in edge.verts:
                n = len(v.link_edges)
                other_edges = set(v.link_edges) - {edge}
                if n == 2:
                    to_explore.append(v.link_edges[0] if v.link_edges[0] != edge else v.link_edges[1])
                if n == 3 and self.action3 == "1":
                    to_explore.extend(other_edges)
                if n == 4 and self.action4 == "1":
                    e = ordered_edge_list(v, edge)
                    to_explore.append(e[2])
                if n == 5 and self.action5 == "1":
                    to_explore.extend(other_edges)

                if n >= 6 and n % 2 == 0:
                    if self.actionEven == "1":
                        to_explore.append(ordered_edge_list(v, edge)[n/2])
                    if self.actionEven == "2":
                        to_explore.append(ordered_edge_list(v, edge)[2::2])

                if n >= 7 and n % 2 == 1 and self.actionOdd == "1":
                    to_explore.extend(other_edges)


        for e in bm.edges:
            if e.select:
                select_edge(e)

        while to_explore:
            print(len(to_explore))
            f = to_explore.pop(0)
            if f.select:
                continue
            select_edge(f)

        bmesh.update_edit_mesh(me)
        me.update()

        return {'FINISHED'}


def register():
    bpy.utils.register_class(AdvancedEdgeSelect)


def unregister():
    bpy.utils.unregister_class(AdvancedEdgeSelect)


if __name__ == "__main__":
    try:
        unregister()
    except:
        pass
    register()
