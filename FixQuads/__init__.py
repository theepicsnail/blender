import itertools
from collections import defaultdict

from typing import Set, Optional

bl_info = {
    "name": "Fix quads",
    "category": "Object",
    'blender': (2, 80, 0),
}
import bpy
import bmesh


def get_opposite_face(face, edge):
    faces = set(edge.link_faces)
    assert face in faces
    faces.remove(face)
    if len(faces) == 0:
        return None
    if len(faces) > 1:
        print("Edge with more than 2 faces.")
        return None
    return faces.pop()


def get_neighbors(face):
    neighbors = set()
    for edge in face.edges:
        f = get_opposite_face(face, edge)
        if f is not None:
            neighbors.add(f)
    return neighbors


def pop_triangle(face_set: Set[bmesh.types.BMFace]) -> Optional[bmesh.types.BMFace]:
    for face in face_set:
        if len(face.edges) == 3:
            face_set.remove(face)
            return face
    return None


def pop_quad(face_set: Set[bmesh.types.BMFace]) -> Optional[bmesh.types.BMFace]:
    for face in face_set:
        if len(face.edges) == 4:
            face_set.remove(face)
            return face
    return None


class FaceExplorer(object):
    def __init__(self, bm: bmesh.types.BMesh, correct_faces: Set[bmesh.types.BMFace]):
        self.bm = bm
        self.correct_faces = set()  # type:Set[bmesh.types.BMFace]
        self.correct_edges = set()  # type:Set[bmesh.types.BMEdge]
        self.to_explore = []  # type:List[bmesh.types.BMFace]

        for face in correct_faces:
            self.mark_correct(face)
        self.dirty = False

    def mark_correct(self, face):
        if face in self.correct_faces:
            return False

        self.dirty = True
        self.correct_faces.add(face)
        self.correct_edges.update(face.edges)
        for f in get_neighbors(face).difference(self.correct_faces):
            self.to_explore.append(f)
        return True

    def get_correct_faces(self, other: set):
        return self.correct_faces.intersection(other)

    def is_correct_edge(self, edge):
        return bool(self.get_correct_faces(set(edge.link_faces)))

    def get_correct_edges(self, other: set):
        return self.correct_edges.intersection(other)

    def dissolve_edge(self, edge):
        edge.select = True
        res = bmesh.ops.dissolve_edges(self.bm, edges=[edge])
        self.dirty = True
        return True


def handle_quad(exp: FaceExplorer, quad):
    valid_n = exp.get_correct_faces(get_neighbors(quad))

    if len(valid_n) < 2:
        # We don't know yet.
        return False
    elif len(valid_n) == 2:
        # A quad that's between 2 correct faces is only guaranteed correct if those two faces touch.
        a = set(valid_n.pop().verts)
        b = set(valid_n.pop().verts)
        if len(a.intersection(b)) == 0:
            return False
    # 3 or 4 valid neighbors means we're valid
    exp.mark_correct(quad)
    return True


def handle_triangle(explorer: FaceExplorer, tri):
    all_correct = True
    for e in tri.edges:
        if not explorer.is_correct_edge(e):
            all_correct = False
            if dissolvable_edge(explorer, e):
                return True
            if rotate_edge(explorer, e):
                return True
    if all_correct:
        print("All sides of a triangle are correct. Marking as corect.")
        explorer.mark_correct(tri)
    return False


def dissolvable_edge(exp: FaceExplorer, edge):
    faces = set(edge.link_faces)
    t1 = pop_triangle(faces)
    t2 = pop_triangle(faces)
    if len(faces) != 0 or t1 is None or t2 is None:
        return False
    c1 = exp.get_correct_edges(set(t1.edges))
    c2 = exp.get_correct_edges(set(t2.edges))
    if len(c1) == 2 or len(c2) == 2:
        return exp.dissolve_edge(edge)

    # Check for 2 adjacent edges that are both good.
    for e1 in c1:
        if e1 == edge:
            continue
        for e2 in c2:
            if e2 == edge:
                continue
            if len(common_verts(e1, e2)) != 1:
                continue
            if len(common_verts(get_opposite_face(t1, e1), get_opposite_face(t2, e2))) != 1:
                continue
            return exp.dissolve_edge(edge)
    return False


def rotate_edge(exp: FaceExplorer, middle_edge: bmesh.types.BMEdge):
    print("Rotate edge")
    if exp.get_correct_edges({middle_edge}):
        print("Edge already correct?")
        return False

    faces = set(middle_edge.link_faces)
    t = pop_triangle(faces)
    q = pop_quad(faces)
    if len(faces) != 0 or t is None or q is None:
        print("Edge not between triangle and quad")
        return False

    tc = exp.get_correct_edges(set(t.edges))
    qc = exp.get_correct_edges(set(q.edges))
    if not tc:
        return False
    tc0 = list(tc)[0]
    tn = list(get_neighbors(t) - {q})

    def check_edge(cut_edge):
        edge = find_quad_edge_completing_triangle(q, cut_edge, middle_edge.verts)
        if not edge:
            return False

        opp = get_opposite_face(q, edge)
        if opp:
            # opp should share 0 verts with one of the triangles neighbors
            # and 1 with the other neighrbor
            c = set(len(common_verts(opp, n)) for n in tn)
            if c != {0, 1}:
                return False

        valid = False
        if len(tc) == 2:
            # triangle provides 2 touching correct faces.
            pass
        elif common_verts(tc0, edge) and (edge in qc):
            # Triangle's correct edge is touching the newly added edge
            # and the newly added edge is correct, then we have 2 correct edges
            pass
        else:
            return False

        bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='VERT')
        bpy.ops.mesh.select_all(action='DESELECT')
        cut_edge[0].select = True
        cut_edge[1].select = True
        bpy.ops.mesh.edge_face_add()
        q.select = True
        bpy.ops.mesh.face_split_by_edges()
        bpy.ops.mesh.select_all(action='DESELECT')
        middle_edge.select = True
        bpy.ops.mesh.dissolve_edges()
        for f in tc0.link_faces:
            exp.mark_correct(f)
        return True

    v = list(q.verts)
    return check_edge(v[0::2]) or check_edge(v[1::2])


def common_verts(f1, f2):
    return set(f1.verts).intersection(f2.verts)


def find_quad_edge_completing_triangle(quad, v1, v2):
    search_verts = set(v1).symmetric_difference(set(v2))
    for e in quad.edges:
        if set(e.verts) == search_verts:
            return e
    return None


class FixQuads(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "object.fix_quads"
    bl_label = "Fix Quads"

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    def execute(self, context):
        self.main(context)
        return {'FINISHED'}

    def step(self, context: bpy.context):
        obj = bpy.context.active_object
        me = obj.data
        bm = bmesh.from_edit_mesh(me)
        selected_faces = set(face for face in bm.faces if face.select)

        fe = FaceExplorer(bm, selected_faces)
        while fe.to_explore:
            face = fe.to_explore.pop(0)
            if not face.is_valid:
                continue
            if len(face.edges) > 4:
                print("Skipping >4-gon.")
                continue
            if len(face.edges) == 4:
                if face in fe.correct_faces:
                    continue
                handle_quad(fe, face)
            if len(face.edges) == 3:
                handle_triangle(fe, face)

        bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='FACE')
        bpy.ops.mesh.select_all(action='DESELECT')
        for face in fe.correct_faces:
            if face.is_valid:
                face.select = True

        bmesh.update_edit_mesh(me)
        me.update()

        return True

    def main(self, context):
        for i in range(10):
            print(i)
            if not self.step(context):
                return

    def mark_correct(self, face):
        self.correct_faces.add(face)
        self.changed(face)

    def changed(self, face):
        for f in get_neighbors(face):
            if f not in self.correct_faces:
                self.to_check.add(f)

    def is_correct_edge(self, edge):
        return bool(set(edge.link_faces).intersection(self.correct_faces))

    def handle_quad(self, quad):
        """Check if a quad is valid.
        A Face is valid if 2 adjacent edges are valid.
        """

        def valid_face(face):
            if self.is_correct_edge(face.edges[0]):
                if self.is_correct_edge(face.edges[1]):
                    return True
                return self.is_correct_edge(face.edges[3])
            elif self.is_correct_edge(face.edges[2]):
                if self.is_correct_edge(face.edges[1]):
                    return True
                return self.is_correct_edge(face.edges[3])
            return False

        if valid_face(quad):
            self.mark_correct(quad)

    def handle_triangle_1(self, tri, e1, e2, e3):
        # Handle fixing a triangle with 1 edge correct
        # e1 is correct

        # Check for two triangles making a quad
        def check_two_triangles(common):
            other = get_opposite_face(tri, common)
            if len(other.edges) != 3:
                return False
            # Find other's edge that is connected to e1
            # but is not `common`.
            other_edge = None
            for e in other.edges:
                if e == common:
                    continue
                if set(e1.verts).intersection(set(e.verts)):
                    other_edge = e
                    break

            otherQuad = (set(other_edge.link_faces) - {other}).intersection(self.correct_faces)
            if otherQuad:
                otherQuad = otherQuad.pop()
                myQuad = (set(e1.link_faces) - {tri}).pop()
                if len(set(myQuad.verts).intersection(otherQuad.verts)) != 1:
                    return False
                tri.select = True
                other.select = True
                bpy.ops.mesh.dissolve_faces()
                return True
            return False

        if check_two_triangles(e2):
            return True
        if check_two_triangles(e3):
            return True

        # Pivot is the vert that's not on the correct edge.
        pivot = (set(e2.verts) - set(e1.verts)).pop()

        def bad_vert(vert):
            return len(set(vert.link_faces).intersection(self.correct_faces)) == 3

        v1, v2 = e2.verts
        if v2 == pivot:
            v1, v2 = v2, v1
        # v1 == pivot
        if bad_vert(v2):
            edge = e2
        else:
            v1, v2 = e3.verts
            if v2 == pivot:
                v1, v2 = v2, v1
            if bad_vert(v2):
                edge = e3
            else:
                return False

        quad = (set(edge.link_faces) - {tri}).pop()
        if len(quad.edges) != 4:
            return False
        # The wrong vert on the edge to move will have 3 correct faces and 2 incorrect faces.

        self.swap_edge(tri, quad, pivot, edge)
        return True

    def handle_triangle_2(self, face, e1, e2, e3):
        # Handle fixing a triangle with 2 edges correct
        # e1 and e2 are correct
        print("Handle triangle")
        faces = (set(e3.link_faces) - {face})
        if len(faces) != 1:
            return False

        q = faces.pop()

        # Fix simple triangle-triangle to quad
        if len(q.edges) == 3:
            e3.select = True
            bpy.ops.mesh.dissolve_edges()
            new_face = (set(e1.link_faces) - self.correct_faces).pop()
            self.mark_correct(new_face)
            print("3")
            return True

        if len(q.edges) != 4:
            print("4")
            return False

        if len(e3.verts[0].link_faces) == 4:
            pivot = e3.verts[0]
        elif len(e3.verts[1].link_faces) == 4:
            pivot = e3.verts[1]
        elif len(set(e3.verts[0].link_faces).intersection(self.correct_faces)) == 3:
            pivot = e3.verts[1]
        elif len(set(e3.verts[1].link_faces).intersection(self.correct_faces)) == 3:
            pivot = e3.verts[0]
        else:
            return False

        print(face, q, pivot, e3)
        self.swap_edge(face, q, pivot, e3)
        return True

    def swap_edge(self, tri, quad, pivot, edge):
        bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='VERT')
        bpy.ops.mesh.select_all(action='DESELECT')
        if len(quad.verts) != 4:
            quad.select = True
            raise Exception("Quad doesn't have 4 edges")

        assert len(tri.verts) == 3
        assert len(edge.verts) == 2
        assert pivot in quad.verts
        assert pivot in tri.verts
        assert pivot in edge.verts

        verts = set(quad.verts)
        for e in quad.edges:
            if pivot in e.verts:
                verts -= set(e.verts)
        if not verts:
            bpy.ops.mesh.select_all(action='DESELECT')
            quad.select = True
            tri.select = True
            raise Exception("Failed to compute pivot destination")
        opposite = verts.pop()
        opposite.select = True
        pivot.select = True
        bpy.ops.mesh.edge_face_add()
        quad.select = True
        bpy.ops.mesh.face_split_by_edges()
        bpy.ops.mesh.select_all(action='DESELECT')
        edge.select = True
        bpy.ops.mesh.dissolve_edges()

        # self.changed(tri)
        # edge = (set(tri.edges) & set(quad.edges)).pop()
        # bpy.ops.mesh.delete(type='EDGE')
        pass


class TriStripToQuadStrip(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "object.tri_strip_to_quad_strip"
    bl_label = "Tri strip to quad strip"
    even = bpy.props.BoolProperty(name="Even edges")

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    def execute(self, context):
        me = bpy.context.active_object.data
        bm = bmesh.from_edit_mesh(me)

        ew = EdgeWalker()
        bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='FACE')
        sel_faces = [f for f in bm.faces if f.select]
        for face in sel_faces:
            es = []
            for e in face.edges:
                add_edge = True
                for n in e.link_faces:
                    if not n.select:
                        add_edge = False
                if add_edge:
                    es.append(e)

            for edge in es:
                ew.add_edge(face, edge)

        print("Start walking")
        bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='EDGE')
        bpy.ops.mesh.select_all(action='DESELECT')
        for edge in ew.walk_edges(self.even):
            edge.select = True

        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)


class EdgeWalker:
    def __init__(self):
        self.cur_edge = None  # type:Optional[bmesh.types.BMEdge]
        self.face_to_edges = defaultdict(list)
        self.edge_to_faces = defaultdict(list)

    def add_edge(self, face: bmesh.types.BMFace, edge: bmesh.types.BMEdge):
        if self.cur_edge is None or edge.index < self.cur_edge.index:
            self.cur_edge = edge

        self.face_to_edges[face].append(edge)
        self.edge_to_faces[edge].append(face)
        assert len(self.edge_to_faces[edge]) <= 2
        assert len(self.face_to_edges[face]) <= 2

    def walk_edges(self, skip_first):
        if skip_first:
            self.step()

        while self.cur_edge is not None:
            yield self.cur_edge
            self.step()
            self.step()

    def step(self):
        faces = self.edge_to_faces[self.cur_edge]
        neighbors = []
        for f in faces:
            e = self.face_to_edges[f]
            e.remove(self.cur_edge)
            neighbors.extend(e)

        if neighbors:
            self.cur_edge = neighbors[0]
        else:
            self.cur_edge = None


def register():
    bpy.utils.register_class(FixQuads)
    bpy.utils.register_class(TriStripToQuadStrip)


def unregister():
    bpy.utils.unregister_class(FixQuads)
    bpy.utils.register_class(TriStripToQuadStrip)


if __name__ == "__main__":
    try:
        unregister()
    except:
        pass
    register()
    bpy.ops.object.fix_quads()
