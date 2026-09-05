from functools import partial
from glob import glob
from queue import Queue
from threading import Thread
from typing import List, Optional, Callable, Tuple
import os
import sys
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent

import OpenGL.GL as gl
# Removed GLUT import — GLFW will be used for window/context
# import OpenGL.GLUT as glut
import cv2
import numpy as np
from pillow_heif import register_heif_opener
from PIL import Image

import glfw  # new dependency

from engine.drawing import Drawing
from engine.renderer import Renderer
from engine.simplescanner import SimpleScanner
from background.drawingcreature import DrawingCreature, CREATURE_SHADER_CODE
from background.drawingstatic import DrawingStatic


# Register HEIF opener for HEIC support
register_heif_opener()


def create_back_layer(
        filename: str,
        z: float,
        shader: int = 0,
) -> DrawingStatic:
    drawing_back = DrawingStatic(Renderer.create_texture_from_file(filename), shader=shader)
    drawing_back.position = np.array([0, 0., z])
    drawing_back.scale = np.array([3.6, 2.0, 1.0])
    return drawing_back


def draw_simple_scene(drawings_list: List[Drawing], image_path: str) -> None:
    cleanup_and_exit.background_textures = []
    texture = Renderer.create_texture_from_file(image_path)
    cleanup_and_exit.background_textures.append(texture)
    drawings_list.append(create_back_layer(image_path, -0.8))


def update_scene(drawings_list: List[Drawing], scene_config: dict) -> None:
    creature_drawings = [d for d in drawings_list if isinstance(d, DrawingCreature)]
    drawings_list[:] = creature_drawings

    draw_simple_scene(drawings_list, scene_config['background'])


def scan_from_frame(
        frame: np.ndarray,
        scanner: SimpleScanner,
) -> Optional[np.ndarray]:
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    try:
        processed_frame = scanner.scan(frame)
    except ValueError as e:
        print(e)
        return None
    processed_frame = scanner.remove_background(processed_frame)
    return processed_frame


def load_creature_from_files(
        scanner: SimpleScanner,
        drawings_list: List[Drawing],
        creature_queue: Queue,
        creature_shader_program: int = 0,
) -> None:

    folders = [
        ('./photos/Ghosts/', True),
        ('./photos/Other/', False),
    ]

    for folder, wavy in folders:

        files = (
            glob(folder + '*.jpg') +
            glob(folder + '*.heic')
        )

        print(f"Found {len(files)} files in {folder}")

        for filename in files:
            try:
                print(f"Processing {filename}")

                if filename.lower().endswith('.heic'):
                    heif_file = Image.open(filename)
                    rgb_image = heif_file.convert('RGB')
                    frame = cv2.cvtColor(
                        np.array(rgb_image),
                        cv2.COLOR_RGB2BGR
                    )
                else:
                    frame = cv2.imread(filename)

                if frame is None:
                    print(f"ERROR: Could not read {filename}")
                    continue

                scanned_drawing = scan_from_frame(frame, scanner)

                if scanned_drawing is None:
                    print(f"ERROR: Scanner returned nothing for {filename}")
                    continue

                print(
                    f"Creating drawing: {filename}, "
                    f"wavy={wavy}"
                )

                drawing = DrawingCreature(
                    Renderer.create_texture(scanned_drawing),
                    shader=creature_shader_program,
                    wavy=wavy
                )

                drawings_list.append(drawing)
                creature_queue.put(drawing)

                print(f"Successfully loaded {filename}")

            except Exception as e:
                print(
                    f"ERROR processing {filename}: {str(e)}"
                )




class PhotoHandler(FileSystemEventHandler):
    def __init__(
            self,
            scanner: SimpleScanner,
            scanned_creature_queue: Queue
    ):
        self.scanner = scanner
        self.scanned_creature_queue = scanned_creature_queue
        self.processed_files = set()

    def _get_animation_type(self, filename: str):
        """
        Determine animation based on which folder contains the photo.

        Ghosts = wavy
        Other = rigid
        """

        normalized_path = os.path.abspath(filename).replace('\\', '/')

        if '/Ghosts/' in normalized_path:
            return True

        if '/Other/' in normalized_path:
            return False

        return None

    def _process_file(self, filename: str):

        if filename in self.processed_files:
            return

        wavy = self._get_animation_type(filename)

        if wavy is None:
            return

        print(
            f"DEBUG: Processing new photo: {filename}, "
            f"wavy={wavy}",
            flush=True
        )

        # Wait until the file actually exists and has finished copying.
        previous_size = -1

        for _ in range(20):
            try:
                current_size = os.path.getsize(filename)

                if current_size > 0 and current_size == previous_size:
                    break

                previous_size = current_size
                time.sleep(0.25)

            except OSError:
                time.sleep(0.25)

        try:
            if filename.lower().endswith('.heic'):
                heif_file = Image.open(filename)
                rgb_image = heif_file.convert('RGB')

                frame = cv2.cvtColor(
                    np.array(rgb_image),
                    cv2.COLOR_RGB2BGR
                )
            else:
                frame = cv2.imread(filename)

            if frame is None:
                print(
                    f"ERROR: Could not read {filename}",
                    flush=True
                )
                return

            scanned_drawing = scan_from_frame(
                frame,
                self.scanner
            )

            if scanned_drawing is None:
                print(
                    f"ERROR: Scanner returned nothing for {filename}",
                    flush=True
                )
                return

            # Put the scanned image AND animation type into the queue.
            self.scanned_creature_queue.put(
                (scanned_drawing, wavy)
            )

            self.processed_files.add(filename)

            print(
                f"DEBUG: Successfully queued {filename}, "
                f"wavy={wavy}",
                flush=True
            )

        except Exception as e:
            print(
                f"ERROR processing {filename}: {str(e)}",
                flush=True
            )
    def on_moved(self, event):
        if event.is_directory:
            return

        filename = event.dest_path

        if not (
            filename.lower().endswith('.jpg')
            or filename.lower().endswith('.jpeg')
            or filename.lower().endswith('.heic')
        ):
            return

        print(
            f"DEBUG: FILE MOVED: {event.src_path} -> {filename}",
            flush=True
        )

        self._process_file(filename)


        def on_created(self, event):
            if event.is_directory:
                return

            filename = event.src_path

            if not (
                filename.lower().endswith('.jpg')
                or filename.lower().endswith('.jpeg')
                or filename.lower().endswith('.heic')
            ):
                return

            print(
                f"DEBUG: FILE CREATED: {filename}",
                flush=True
            )

            self._process_file(filename)

        def on_modified(self, event):
            if event.is_directory:
                return

            filename = event.src_path

            if not (
                filename.lower().endswith('.jpg')
                or filename.lower().endswith('.jpeg')
                or filename.lower().endswith('.heic')
            ):
                return

            if filename not in self.processed_files:
                print(
                    f"DEBUG: FILE MODIFIED: {filename}",
                    flush=True
                )

                self._process_file(filename)




def watch_photos_directory(
        scanner: SimpleScanner,
        scanned_creature_queue: Queue,
) -> None:
    event_handler = PhotoHandler(scanner, scanned_creature_queue)
    observer = Observer()
    observer.schedule(event_handler, path='./photos', recursive=True)
    observer.start()

    cleanup_and_exit.observer = observer

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


def cleanup_and_exit():
    """
    Cleanup function to be called before program exit
    """
    # Stop the observer thread
    if hasattr(cleanup_and_exit, 'observer') and cleanup_and_exit.observer is not None:
        try:
            cleanup_and_exit.observer.stop()
            cleanup_and_exit.observer.join()
        except Exception:
            pass

    # Clean up OpenGL resources
    try:
        if hasattr(cleanup_and_exit, 'creature_shader'):
            try:
                gl.glDeleteProgram(cleanup_and_exit.creature_shader)
            except Exception:
                pass
    except Exception:
        pass

    # Delete textures
    textures_to_delete = []
    if hasattr(cleanup_and_exit, 'background_textures'):
        textures_to_delete.extend(cleanup_and_exit.background_textures)

    try:
        if textures_to_delete:
            gl.glDeleteTextures(textures_to_delete)
    except Exception:
        pass

    # Clean up VBO buffers from drawings
    if hasattr(cleanup_and_exit, 'drawings_list'):
        for drawing in cleanup_and_exit.drawings_list:
            if hasattr(drawing, '_vbo_vertices'):
                try:
                    drawing._vbo_vertices.delete()
                except Exception:
                    pass
            if hasattr(drawing, '_vbo_texcoords'):
                try:
                    drawing._vbo_texcoords.delete()
                except Exception:
                    pass

    # Close GLFW window if present
    try:
        if hasattr(cleanup_and_exit, 'window') and cleanup_and_exit.window is not None:
            try:
                glfw.destroy_window(cleanup_and_exit.window)
            except Exception:
                pass
    except Exception:
        pass

    # Exit normally
    try:
        glfw.terminate()
    except Exception:
        pass

    os._exit(0)  # Use os._exit to avoid raising SystemExit exception


def create_key_processor(
        scanner: SimpleScanner,
        scanned_creature_queue: Queue,
        drawings_list: List[Drawing],
        background_scenes: List[dict],
        current_scene_index: List[int]
) -> Tuple[Callable, Callable]:
    # kept for compatibility but not used by GLFW main
    def process_key(key: bytes, *_):
        if key == b'\x1b':  # esc
            cleanup_and_exit()

    def process_special_key(key: int, *_):
        return

    return process_key, process_special_key


def create_animation_function(
        renderer: Renderer,
        drawings_list: List[Drawing],
        scanned_creature_queue: Queue,
        creature_queue: Queue,
        creature_limit: int,
        timer_msec: int,
        creature_shader_program: int = 0,
) -> Callable:
    def animate(value):
        renderer.animate(drawings_list)
        if scanned_creature_queue.qsize() > 0:
            scanned_creature = scanned_creature_queue.get()
            drawing = DrawingCreature(Renderer.create_texture(scanned_creature),
                                  shader=creature_shader_program)
            drawings_list.append(drawing)
            creature_queue.put(drawing)

        if creature_queue.qsize() > creature_limit:
            creature = creature_queue.get()
            creature.go_away()

        # Remove dead creatures from drawing list
        for drawing in drawings_list:
            if isinstance(drawing, DrawingCreature) and not drawing.is_alive:
                drawings_list.remove(drawing)
    return animate


def main():
    # GLFW-based main (replaces GLUT usage)
    # Ensure GLFW is initialized
    if not glfw.init():
        print("Failed to initialize GLFW. Install with: pip install glfw")
        return

    # Request compatibility context
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 2)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 1)

    width, height = 800, 600
    window = glfw.create_window(width, height, "HalloweenScanner", None, None)
    if not window:
        print("Failed to create GLFW window")
        glfw.terminate()
        return

    glfw.make_context_current(window)
    glfw.swap_interval(1)  # vsync

    # Initialize OpenGL via Renderer after context is current
    renderer = Renderer()
    renderer.init_for_window(width, height)
  
    gl.glClearColor(0.1, 0.1, 0.2, 1.0)

    scanner = SimpleScanner()

    timer_msec = int(1000 / 60)  # 60 times per second
    drawings_list = []
    cleanup_and_exit.drawings_list = drawings_list  # Store for cleanup

    creature_queue = Queue()
    creature_limit = 10
    scanned_creature_queue = Queue()
    
    background_scenes = [
        {'type': 'simple', 'name': 'halloween1','background': 'background/images/halloween1.jpg'},
        {'type': 'simple', 'name': 'halloween2','background': 'background/images/halloween2.jpg'},
        {'type': 'simple', 'name': 'halloween3','background': 'background/images/halloween3.jpg'}]

    current_scene_index = [0]

    # Initialize the scene
    update_scene(drawings_list, background_scenes[current_scene_index[0]])

    creature_shader_program = Renderer.create_shader(gl.GL_VERTEX_SHADER, CREATURE_SHADER_CODE)

    load_creature_from_files(scanner, drawings_list, creature_queue, creature_shader_program)

    # --- Correct texture inspection: bind each texture before querying its level0 size ---
    for i, d in enumerate(drawings_list):
        texid = getattr(d, '_texid', None)
        if texid:
            try:
                gl.glBindTexture(gl.GL_TEXTURE_2D, int(texid))
                w = gl.glGetTexLevelParameteriv(gl.GL_TEXTURE_2D, 0, gl.GL_TEXTURE_WIDTH)
                h = gl.glGetTexLevelParameteriv(gl.GL_TEXTURE_2D, 0, gl.GL_TEXTURE_HEIGHT)
                print(f"DEBUG:  bound tex {texid} level0 size = {w}x{h}", flush=True)
                gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
            except Exception as e:
                print("DEBUG:  tex query exception:", e, flush=True)
    print("DEBUG: corrected texture inspection end", flush=True)

    
    cleanup_and_exit.creature_shader = creature_shader_program

    # Start file watcher thread
    watcher_thread = Thread(target=watch_photos_directory, args=(scanner, scanned_creature_queue))
    watcher_thread.daemon = True  # Thread will exit when main program exits
    watcher_thread.start()

    cleanup_and_exit.window = window

    # Key handler (GLFW)
    def on_key(window_arg, key, scancode, action, mods):
        if key == glfw.KEY_ESCAPE and action == glfw.PRESS:
            cleanup_and_exit()
        elif key == glfw.KEY_LEFT and action == glfw.PRESS:
            current_scene_index[0] = (current_scene_index[0] - 1) % len(background_scenes)
            update_scene(drawings_list, background_scenes[current_scene_index[0]])
        elif key == glfw.KEY_RIGHT and action == glfw.PRESS:
            current_scene_index[0] = (current_scene_index[0] + 1) % len(background_scenes)
            update_scene(drawings_list, background_scenes[current_scene_index[0]])

    glfw.set_key_callback(window, on_key)

    # Main loop
    target_fps = 60.0
    frame_time = 1.0 / target_fps
    try:
        while not glfw.window_should_close(window):
            start_time = time.time()

            glfw.poll_events()

            while not scanned_creature_queue.empty():
                scanned_drawing, wavy = scanned_creature_queue.get()

                drawing = DrawingCreature(
                    Renderer.create_texture(scanned_drawing),
                    shader=creature_shader_program,
                    wavy=wavy
                )

                drawings_list.append(drawing)
                creature_queue.put(drawing)


            # Trim creatures beyond limit
            if creature_queue.qsize() > creature_limit:
                creature = creature_queue.get()
                creature.go_away()

            # Animate and render
            renderer.animate(drawings_list)
            renderer.render(drawings_list)


           

            # Swap buffers
            glfw.swap_buffers(window)

            # Remove dead creatures
            for drawing in list(drawings_list):
                if isinstance(drawing, DrawingCreature) and not drawing.is_alive:
                    drawings_list.remove(drawing)

            elapsed = time.time() - start_time
            sleep = frame_time - elapsed
            if sleep > 0:
                time.sleep(sleep)
    except KeyboardInterrupt:
        pass
    finally:
        cleanup_and_exit()


if __name__ == '__main__':
    main()