"""Small CPU-only 3D compatibility proof, NOT a GTA game or FPS benchmark.
Optional dependency: pip install panda3d==1.10.16
Does not change Blender dependencies or dispatch cloud jobs.
"""
from pathlib import Path
import hashlib
import json
from panda3d.core import (
    loadPrcFileData, GraphicsPipeSelection, GeomVertexFormat,
    GeomVertexData, GeomVertexWriter, GeomTriangles, Geom, GeomNode,
    PNMImage, PandaSystem,
)

loadPrcFileData('', '''
load-display p3tinydisplay
window-type offscreen
win-size 640 360
audio-library-name null
sync-video false
notify-level-device fatal
''')
from direct.showbase.ShowBase import ShowBase

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs' / 'research-assets'


def box(parent, name, position, size, color):
    data = GeomVertexData(name, GeomVertexFormat.get_v3c4(), Geom.UH_static)
    vertices = GeomVertexWriter(data, 'vertex')
    colors = GeomVertexWriter(data, 'color')
    faces = [
        ([(-1,-1,-1),(-1,1,-1),(1,1,-1),(1,-1,-1)], .45),
        ([(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)], 1.0),
        ([(-1,-1,-1),(1,-1,-1),(1,-1,1),(-1,-1,1)], .85),
        ([(1,-1,-1),(1,1,-1),(1,1,1),(1,-1,1)], .65),
        ([(1,1,-1),(-1,1,-1),(-1,1,1),(1,1,1)], .55),
        ([(-1,1,-1),(-1,-1,-1),(-1,-1,1),(-1,1,1)], .75),
    ]
    triangles = GeomTriangles(Geom.UH_static)
    for face, (corners, shade) in enumerate(faces):
        for vertex in corners:
            vertices.add_data3(*vertex)
            colors.add_data4(color[0]*shade, color[1]*shade, color[2]*shade, 1)
        first = face * 4
        triangles.add_vertices(first, first+1, first+2)
        triangles.add_vertices(first, first+2, first+3)
    geometry = Geom(data)
    geometry.add_primitive(triangles)
    node = GeomNode(name)
    node.add_geom(geometry)
    instance = parent.attach_new_node(node)
    instance.set_pos(*position)
    instance.set_scale(*(dimension/2 for dimension in size))
    instance.set_light_off()
    return instance


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    app = ShowBase(windowType='none')
    try:
        selection = GraphicsPipeSelection.get_global_ptr()
        types = [selection.get_pipe_type(i) for i in range(selection.get_num_pipe_types())]
        pipe_type = next(t for t in types if t.get_name() == 'TinyOffscreenGraphicsPipe')
        pipe = selection.make_pipe(pipe_type)
        app.open_default_window(type='offscreen', pipe=pipe)
        if app.win is None:
            raise RuntimeError('No CPU off-screen buffer')
        renderer = app.win.get_gsg().get_type().get_name()
        if not renderer.startswith('Tiny'):
            raise RuntimeError('Expected a software renderer, not a hardware backend')
        app.set_background_color(.45, .65, .82, 1)
        box(app.render, 'ground', (0, 5, -.12), (32, 38, .2), (.25, .40, .23))
        box(app.render, 'street', (0, 5, .01), (5, 38, .06), (.18, .20, .23))
        box(app.render, 'cross-street', (0, 5, .03), (32, 5, .06), (.18, .20, .23))
        for side in (-1, 1):
            for row, y in enumerate((-7, -1, 11, 17)):
                height = 3 + row % 3
                x = side * 7
                box(app.render, f'building-{side}-{row}', (x,y,height/2), (4,4,height),
                    (.68 + row*.03, .60, .42 + row*.05))
                box(app.render, f'roof-{side}-{row}', (x,y,height+.08), (4.2,4.2,.2), (.30,.35,.42))
                for window in (-1, 1):
                    box(app.render, f'window-{side}-{row}-{window}',
                        (x + window*.9, y-2.02, height*.6), (.8,.04,.9), (.30,.58,.70))
        for y in range(-10, 22, 4):
            box(app.render, f'road-marking-{y}', (0,y,.08), (.12,1.8,.02), (.9,.86,.65))
        box(app.render, 'car-body', (1,-3,.6), (1.7,3.2,.7), (.80,.12,.08))
        box(app.render, 'car-cabin', (1,-2.8,1.15), (1.4,1.65,.55), (.20,.38,.48))
        for x in (.12,1.88):
            for y in (-4,-2):
                box(app.render, 'wheel', (x,y,.37), (.22,.65,.65), (.06,.07,.08))
        app.disable_mouse()
        app.camera.set_pos(21,-25,23)
        app.camera.look_at(0,5,0)
        app.camLens.set_fov(54)
        for _ in range(3):
            app.graphicsEngine.render_frame()
        image = PNMImage()
        if not app.win.get_screenshot(image):
            raise RuntimeError('Screenshot readback failed')
        path = OUT / 'cpu-only-3d-proof.png'
        if not image.write(str(path)):
            raise RuntimeError('Image write failed')
        if (image.get_x_size(), image.get_y_size()) != (640,360):
            raise RuntimeError('Unexpected image dimensions')
        samples = {tuple(image.get_xel(x,y)) for y in range(10,350,20) for x in range(10,630,20)}
        if len(samples) < 8:
            raise RuntimeError('Image appears empty')
        report = {
            'status': 'CPU_ONLY_3D_COMPATIBILITY_PROOF_PASS',
            'engine': 'Panda3D', 'version': PandaSystem.get_version_string(),
            'graphics_pipe': pipe.get_type().get_name(), 'renderer': renderer,
            'dimensions': [640,360], 'image_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'scope': 'Static primitive scene, software-rendered on this sandbox CPU.',
            'not_demonstrated': ['Playable game', 'GTA-scale world', 'laptop FPS',
                                 'physics/AI systems', 'photorealism'],
        }
        (OUT / 'cpu-only-3d-proof.json').write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps(report, indent=2))
    finally:
        app.destroy()


if __name__ == '__main__':
    main()
