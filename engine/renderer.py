import sys
from queue import Queue
from typing import List

import cv2
import numpy as np

from engine.drawing import Drawing


class Renderer:
    """
    Core of the Engine
    """

    def __init__(self):
        """
        Initialize GL state later after a context is current.
        Do not call GL functions here that require a current context.
        Call init_for_window(width, height) after creating a window/context.
        """
        self._initialized = False

    def init_for_window(self, width: int, height: int) -> None:
        """
        Initialize OpenGL state once a context is current and known window size is available
        """
        from OpenGL import GL as gl

        self._gl = gl

        gl.glEnable(gl.GL_TEXTURE_2D)
        gl.glDisable(gl.GL_LIGHTING)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glEnableClientState(gl.GL_VERTEX_ARRAY)

        # Enable depth testing
        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glDepthFunc(gl.GL_LEQUAL)

        # Enable alpha testing to handle transparency better
        gl.glEnable(gl.GL_ALPHA_TEST)
        gl.glAlphaFunc(gl.GL_GREATER, 0.1)  # Only render pixels with alpha > 0.1

        # Setup viewport and projection
        gl.glViewport(0, 0, width, height)
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        aspect = width / height if height != 0 else 1.0
        gl.glOrtho(-aspect, aspect, 1, -1, -1, 1)

        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()

        self._initialized = True

    @staticmethod
    def render(drawings_list: List[Drawing]) -> None:
        """
        Draw all sprites. This function assumes a valid GL context is current.
        Note: swapping buffers should be done by the platform (GLFW) after this call.
        """
        from OpenGL import GL as gl

        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)

        # Sort drawings by z-position (back to front)
        sorted_drawings = sorted(drawings_list, key=lambda x: x.position[2], reverse=True)

        # First pass: render opaque objects
        gl.glDepthMask(gl.GL_TRUE)
        for drawing in sorted_drawings:
            if not hasattr(drawing, 'is_transparent') or not drawing.is_transparent:
                drawing.render()

        # Second pass: render transparent objects
        gl.glDepthMask(gl.GL_FALSE)  # Don't write to depth buffer for transparent objects
        for drawing in sorted_drawings:
            if hasattr(drawing, 'is_transparent') and drawing.is_transparent:
                drawing.render()

        gl.glDepthMask(gl.GL_TRUE)  # Reset depth mask
        gl.glFlush()

    def animate(
            self,
            drawings_list: List[Drawing],
    ) -> None:
        """
        Perform one step of animation
        :param drawings_list: List of sprites to animate
        :return:
        """
        renderer_queue = Queue()
        for drawing in drawings_list:
            drawing.animation()
            for child in drawing.get_child_sprites():
                renderer_queue.put(child)

        while renderer_queue.qsize() > 0:
            drawing = renderer_queue.get()
            drawing.animation()
            for child in drawing.get_child_sprites():
                renderer_queue.put(child)

        # No glut.glutPostRedisplay() here — main loop will call render each frame

   
    @staticmethod
    def create_texture(image: np.ndarray) -> int:
        """
        Create a texture from image represented by ndarray (expects RGBA or RGB)
        :param image: Image to build texture (numpy array)
        :return: Texture ID
        """
        from OpenGL import GL as gl

        img = np.ascontiguousarray(image)
        if img.dtype != np.uint8:
            img = img.astype(np.uint8)

        h, w = img.shape[:2]
        channels = img.shape[2] if img.ndim == 3 else 1

        # Choose OpenGL format based on channels
        if channels == 4:
            internal_format = gl.GL_RGBA
            data_format = gl.GL_RGBA
        elif channels == 3:
            internal_format = gl.GL_RGB
            data_format = gl.GL_RGB
        else:
            # single channel -> use RED/LUMINANCE depending on GL version
            internal_format = gl.GL_RED if hasattr(gl, 'GL_RED') else gl.GL_LUMINANCE
            data_format = internal_format

        texid = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, texid)
        gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 1)
        gl.glTexImage2D(gl.GL_TEXTURE_2D,
                        0,
                        internal_format,
                        w, h,
                        0,
                        data_format,
                        gl.GL_UNSIGNED_BYTE,
                        img)

        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
        gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST)
        gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)

        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
        return texid

    @staticmethod
    def create_texture_from_file(filename: str) -> int:
        """
        Create a texture from image loaded by the filename.
        Ensures correct channel ordering for JPG (BGR) and other formats.
        :param filename: Path to image with the texture
        :return: Texture ID
        """
        image = cv2.imread(filename, cv2.IMREAD_UNCHANGED)
        if image is None:
            raise FileNotFoundError(f"Failed to read image '{filename}'")

        # Convert loaded OpenCV image to RGBA for consistent upload
        if image.ndim == 2:
            # grayscale -> expand to RGBA
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGBA)
        elif image.shape[2] == 3:
            # BGR -> RGBA
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGBA)
        elif image.shape[2] == 4:
            # BGRA -> RGBA
            image = cv2.cvtColor(image, cv2.COLOR_BGRA2RGBA)
        else:
            # unexpected number of channels; try to make it RGBA
            try:
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGBA)
            except Exception:
                # fallback: create an empty RGBA placeholder
                h, w = image.shape[:2]
                image = np.zeros((h, w, 4), dtype=np.uint8)

        return Renderer.create_texture(image) 


    @staticmethod
    def create_shader(
            shader_type,
            source: str,
    ) -> int:
        """
        Compile a vertex shader from 'source' and attach a minimal fragment shader,
        then link into a program. Returns program id.

        Note: callers in the repo pass a vertex shader source (FISH_SHADER_CODE / SEAWEED_SHADER_CODE).
        We treat 'source' as the vertex shader source and provide a compatible fragment shader.
        """
        from OpenGL import GL as gl

        def _compile(stype, src):
            sh = gl.glCreateShader(stype)
            gl.glShaderSource(sh, src)
            gl.glCompileShader(sh)
            ok = gl.glGetShaderiv(sh, gl.GL_COMPILE_STATUS)
            if not ok:
                info = gl.glGetShaderInfoLog(sh)
                raise RuntimeError(f"Shader compile error ({stype}): {info!r}")
            return sh

        # Vertex shader: use provided source
        vertex_src = source

        # Minimal fragment shader compatible with legacy built-ins used by the vertex shader
        fragment_src = """
        #version 110
        uniform sampler2D tex;
        void main() {
            vec4 base = texture2D(tex, gl_TexCoord[0].xy);
            gl_FragColor = base * gl_Color;
        }
        """

        # Compile shaders
        vsh = _compile(gl.GL_VERTEX_SHADER, vertex_src)
        fsh = _compile(gl.GL_FRAGMENT_SHADER, fragment_src)

        # Link program
        prog = gl.glCreateProgram()
        gl.glAttachShader(prog, vsh)
        gl.glAttachShader(prog, fsh)
        gl.glLinkProgram(prog)

        linked = gl.glGetProgramiv(prog, gl.GL_LINK_STATUS)
        if not linked:
            info = gl.glGetProgramInfoLog(prog)
            raise RuntimeError(f"Shader link error: {info!r}")

        # Make sure the program's sampler 'tex' points to texture unit 0
        try:
            gl.glUseProgram(prog)
            loc = gl.glGetUniformLocation(prog, "tex")
            if loc != -1 and loc is not None:
                gl.glUniform1i(loc, 0)
        finally:
            gl.glUseProgram(0)

        return prog