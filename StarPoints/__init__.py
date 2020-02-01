import itertools
from collections import defaultdict

from typing import Set, Optional, List

bl_info = {
    "name": "Select star points",
    "category": "Object",
    'blender': (2, 80, 0),
}
import bpy
import bmesh
import random


def neighbor_faces(face: bmesh.types.BMFace):
    f: Set[bmesh.types.BMFace] = set()
    for e in face.edges:
        f.update(e.link_faces)
    f.remove(face)
    return f


def neighbor_verts(vert: bmesh.types.BMVert):
    f: Set[bmesh.types.BMVert] = set()
    for e in vert.link_edges:
        f.update(e.verts)
    f.remove(vert)
    return f


def triangle_opposite_edge(triangle: bmesh.types.BMFace, vert: bmesh.types.BMVert):
    if len(triangle.edges) != 3:
        triangle.select = True

        assert len(triangle.edges) == 3
    assert vert in triangle.verts
    for e in triangle.edges:
        if vert not in e.verts:
            return e
def triangle_opposite_vert(triangle: bmesh.types.BMFace, edge: bmesh.types.BMEdge):
    if len(triangle.edges) != 3:
        triangle.select = True
        assert len(triangle.edges) == 3
    assert edge in triangle.edges
    for v in triangle.verts:
        if v not in edge.verts:
            return v


def is_star_point(vert: bmesh.types.BMVert):
    n1 = neighbor_verts(vert)
    n2 = set()
    for n in n1:
        n2.update(neighbor_verts(n))
    n2.difference_update(n1)
    n2.remove(vert)
    return len(n2) == 2 * len(n1)

def edge_opposite_face(edge: bmesh.types.BMEdge, face:bmesh.types.BMFace):
    assert face in edge.link_faces
    if len(edge.link_faces) == 1:
        return None
    assert len(edge.link_faces) == 2

    if edge.link_faces[0] == face:
        return edge.link_faces[1]
    return edge.link_faces[0]

def neighbor_star_points_small(vert: bmesh.types.BMVert):
    faces = vert.link_faces
    res = []
    for f in faces:
        e = triangle_opposite_edge(f, vert)
        t2 = edge_opposite_face(e, f)
        if t2 == None:
            continue
        v = triangle_opposite_vert(t2, e)
        res.append(v)
    return res

def neighbor_star_points(vert: bmesh.types.BMVert):
    count = defaultdict(int)
    n0 = set([vert])
    count[vert.index] = 1

    n1 = set()
    for v in n0:
        for n in neighbor_verts(v) - n0:
            count[n.index] += count[v.index]
            n1.add(n)

    n2 = set()
    for v in n1 - n0:
        for n in neighbor_verts(v) - n1 - n0:
            count[n.index] += count[v.index]
            n2.add(n)

    n3 = set()
    for v in n2 - n1 - n0:
        for n in neighbor_verts(v) - n2 - n1 - n0:
            count[n.index] += count[v.index]
            n3.add(n)

    n4 = set()
    for v in n3 - n2 - n1 - n0:
        for n in neighbor_verts(v) - n3 - n2 - n1 - n0:
            count[n.index] += count[v.index]
            n4.add(n)

    m = max([count[n.index] for n in n4])
    return [n for n in n4 if count[n.index] == 6]


def select_contained_edges(verts: Set[bmesh.types.BMVert]):
    res = []
    for v in verts:
        for e in v.link_edges:
            if verts.issuperset(set(e.verts)):
                res.append(e)
    return res


def select_star_edges(center: bmesh.types.BMVert, outer=True):
    inner_verts = neighbor_verts(center)
    edges = select_contained_edges(inner_verts)

    if outer:
        outer_verts = set()
        for v in inner_verts:
            outer_verts.update(neighbor_verts(v))
        outer_verts -= inner_verts
        outer_verts.remove(center)
        edges += select_contained_edges(outer_verts)

    return edges


class SelectStarEdges(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "object.select_star_edges"
    bl_label = "Select star edges"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    def execute(self, context):
        self.main(context)
        return {'FINISHED'}

    def main(self, context: bpy.context):
        obj = bpy.context.active_object
        me = obj.data
        bm = bmesh.from_edit_mesh(me)

        stars: List[bmesh.types.BMVert] = [vert for vert in bm.verts if vert.select]
        bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='EDGE')

        for v in stars:
            for e in select_star_edges(v):
                e.select = True

        bmesh.update_edit_mesh(me)


class SelectStarPoints(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "object.select_star_points"
    bl_label = "Select star points"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    def execute(self, context):
        self.main(context)
        return {'FINISHED'}

    def main(self, context: bpy.context):
        obj = bpy.context.active_object
        me = obj.data
        bm = bmesh.from_edit_mesh(me)


        again = True
        while again:
            again = False
            stars = [vert for vert in bm.verts if vert.select]
            for vert in stars:
                for v in neighbor_star_points(vert):
                    v.select = True
                    if v not in stars:
                        again = True

        bmesh.update_edit_mesh(me)


class SelectStarEdgesSmall(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "object.select_star_edges_small"
    bl_label = "Select star edges small"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    def execute(self, context):
        self.main(context)
        return {'FINISHED'}

    def main(self, context: bpy.context):
        obj = bpy.context.active_object
        me = obj.data
        bm = bmesh.from_edit_mesh(me)

        stars: List[bmesh.types.BMVert] = [vert for vert in bm.verts if vert.select]
        bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='EDGE')

        for v in stars:
            for e in select_star_edges(v, False):
                e.select = True

        bmesh.update_edit_mesh(me)

class SelectStarPointsSmall(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "object.select_star_points_small"
    bl_label = "Select star points small"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    def execute(self, context):
        self.main(context)
        return {'FINISHED'}

    def main(self, context: bpy.context):
        obj = bpy.context.active_object
        me = obj.data
        bm = bmesh.from_edit_mesh(me)

        again = True
        while again:
            again = False

            stars = [vert for vert in bm.verts if vert.select]
            for vert in stars:
                for v in neighbor_star_points_small(vert):
                    v.select = True
                    if v not in stars:
                        again = True

        bmesh.update_edit_mesh(me)


class FixStarMesh(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "object.fix_star_mesh"
    bl_label = "Fix star mesh"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    def execute(self, context):
        self.main(context)
        return {'FINISHED'}

    def main(self, context: bpy.context):
        obj = bpy.context.active_object
        me = obj.data
        bm = bmesh.from_edit_mesh(me)
        bpy.ops.object.select_star_points()
        bpy.ops.object.select_star_edges()
        bpy.ops.mesh.dissolve_edges()
        bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='VERT')
class FixStarMeshSmall(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "object.fix_star_mesh_small"
    bl_label = "Fix star mesh small"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    def execute(self, context):
        self.main(context)
        return {'FINISHED'}

    def main(self, context: bpy.context):
        obj = bpy.context.active_object
        me = obj.data
        bm = bmesh.from_edit_mesh(me)
        bpy.ops.object.select_star_points_small()
        bpy.ops.object.select_star_edges_small()
        bpy.ops.mesh.dissolve_edges()
        bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='VERT')

class SelectFaceEdge(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "object.select_face_edge"
    bl_label = "Select face edge"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    def execute(self, context):
        self.main(context)
        return {'FINISHED'}

    def main(self, context: bpy.context):
        obj = bpy.context.active_object
        me = obj.data
        bm = bmesh.from_edit_mesh(me)
        face = [vert for vert in bm.verts if vert.select]





def register():
    print("Starpoints register")
    bpy.utils.register_class(SelectStarPoints)
    bpy.utils.register_class(SelectStarPointsSmall)
    bpy.utils.register_class(SelectStarEdges)
    bpy.utils.register_class(SelectStarEdgesSmall)
    bpy.utils.register_class(FixStarMesh)
    bpy.utils.register_class(FixStarMeshSmall)


def unregister():
    bpy.utils.unregister_class(SelectStarPoints)
    bpy.utils.unregister_class(SelectStarPointsSmall)
    bpy.utils.unregister_class(SelectStarEdges)
    bpy.utils.unregister_class(SelectStarEdgesSmall)
    bpy.utils.unregister_class(FixStarMesh)
    bpy.utils.unregister_class(FixStarMeshSmall)



if __name__ == "__main__":
    try:
        unregister()
    except:
        pass
    register()
