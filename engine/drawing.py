from __future__ import annotations

from typing import List

import OpenGL.GL as gl
import OpenGL.arrays.vbo as glvbo
import numpy as np


class Drawing:
    """
    Draw and animate 3D sprite
    """

    def __init__(
            self,
            texid: int,
            grid_x: int = 5,
            grid_y: int = 5,
            shader: int = 0,
    ):
        """
        Setup default position for sprite. Initialize mesh of selected size.
        :param texid: ID of texture
        :param grid_x: Mesh elements along axis X
        :param grid_y: Mesh elements along axis Y
        :param shader: ID of shader. Select 0 if you need no shader
        """

        # Setup default positions of sprite
        self.position = np.array([0, 0., 0.])
        self.rotate = np.array([0., 0., 0.])
        self.scale = np.array([1.0, 1.0, 1.0])
        self.color = np.array([1.0, 1.0, 1.0])

        # Setup default animation settings
        self.max_animation_timer = 1
        self.step_animation_timer = 0.001

        # Setup default vectors for image transformation
        self.vector = np.array([0.0, 0.0, 0.0])
        self.rotation_vector = np.array([0.0, 0.0, 0.0])

        self._texid = texid
        self._shader = shader
        self._time_counter = 0.0

        # Create vertices array for the sprite
        # vertices is a flat list: [x,y,z, x,y,z, ...]
        vertices = self._mesh_create(grid_size_x=grid_x, grid_size_y=grid_y)
        # Convert to numpy array and reshape to (N,3)
        v = np.array(vertices, dtype='f').reshape(-1, 3)
        self._vertices_count = v.shape[0]

        # Build a 2-component texcoord array from the X,Y of the mesh
        # mesh X,Y range is [-0.5, 0.5), so map to [0,1] by adding 0.5
        texcoords = np.empty((self._vertices_count, 2), dtype='f')
        texcoords[:, 0] = v[:, 0] + 0.5  # u
        texcoords[:, 1] = v[:, 1] + 0.5  # v

        # Create VBOs (vertices: 3 floats per vertex, texcoords: 2 floats per vertex)
        self._vbo_vertices = glvbo.VBO(v.astype('f').ravel())
        self._vbo_texcoords = glvbo.VBO(texcoords.astype('f').ravel())

        # Enable client arrays and set pointers (do not bind texture here)
        gl.glEnableClientState(gl.GL_VERTEX_ARRAY)
        gl.glEnableClientState(gl.GL_TEXTURE_COORD_ARRAY)

        # Bind and set vertex pointer
        self._vbo_vertices.bind()
        gl.glVertexPointer(3, gl.GL_FLOAT, 0, None)

        # Bind and set texcoord pointer with size=2
        self._vbo_texcoords.bind()
        gl.glTexCoordPointer(2, gl.GL_FLOAT, 0, None)

    def _apply_transforms(self) -> None:
        """
        Apply translation, rotation and scaling to the sprite
        :return:
        """
        gl.glTranslatef(*self.position)
        gl.glRotatef(self.rotate[0], 1, 0, 0)
        gl.glRotatef(self.rotate[1], 0, 1, 0)
        gl.glRotatef(self.rotate[2], 0, 0, 1)
        gl.glScalef(*self.scale)

    def _draw_mesh(self) -> None:
        """
        Render sprite's mesh
        :return:
        """
        gl.glPushMatrix()
        self._apply_transforms()
        gl.glEnableClientState(gl.GL_VERTEX_ARRAY)
        gl.glEnableClientState(gl.GL_TEXTURE_COORD_ARRAY)

        # Bind vertices VBO and pointer (3 components)
        self._vbo_vertices.bind()
        gl.glVertexPointer(3, gl.GL_FLOAT, 0, None)

        # Bind texcoord VBO and pointer (2 components)
        self._vbo_texcoords.bind()
        gl.glTexCoordPointer(2, gl.GL_FLOAT, 0, None)

        gl.glDrawArrays(gl.GL_TRIANGLES, 0, self._vertices_count)

        gl.glDisableClientState(gl.GL_VERTEX_ARRAY)
        gl.glDisableClientState(gl.GL_TEXTURE_COORD_ARRAY)
        gl.glPopMatrix()

    def render(self) -> None:
        """
        Render sprite with attached texture and shader
        :return:
        """
        gl.glColor3f(*self.color)

        # Ensure texture unit 0 is active and bind the texture
        gl.glActiveTexture(gl.GL_TEXTURE0)
        gl.glBindTexture(gl.GL_TEXTURE_2D, int(self._texid))

        # Use shader program if set
        if self._shader != 0:
            gl.glUseProgram(self._shader)

            # Defensive: set sampler uniform to texture unit 0 if present
            try:
                loc_tex = gl.glGetUniformLocation(self._shader, "tex")
                if loc_tex != -1 and loc_tex is not None:
                    gl.glUniform1i(loc_tex, 0)
            except Exception:
                # ignore if driver doesn't like the query
                pass

            # Send timer value to the shader (existing behavior)
            location = gl.glGetUniformLocation(self._shader, "timer")
            if location != -1 and location is not None:
                gl.glUniform1f(location, self._time_counter)
            self._time_counter += self.step_animation_timer
            # If timer came to border - go back
            if self._time_counter >= self.max_animation_timer or self._time_counter <= 0:
                self.step_animation_timer = -self.step_animation_timer
        else:
            # If no shader, ensure fixed-function uses the bound texture (already bound)
            pass

        # Draw mesh
        self._draw_mesh()

        # Unbind program and texture
        if self._shader != 0:
            gl.glUseProgram(0)
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)

    def animation(self) -> None:
        """
        Override this method to apply animation
        :return:
        """
        pass

    def get_child_sprites(self) -> List[Drawing]:
        """
        Override this method to return all Drawings that child for the current one
        :return: List of child drawings
        """
        return []

    @staticmethod
    def _mesh_create(
            grid_size_x: int = 5,
            grid_size_y: int = 5,
    ) -> List[float]:
        """
        Create mesh of selected size
        :param grid_size_x: Mesh elements along axis X
        :param grid_size_y: Mesh elements along axis Y
        :return: List of vertices coordinates
        """
        vertices = []
        step_x = 1 / grid_size_x
        step_y = 1 / grid_size_y

        for y in np.arange(-0.5, 0.5, step_y):
            for x in np.arange(-0.5, 0.5, step_x):
                vertices += [x, y, 0.0,
                             x + step_x, y, 0.0,
                             x, y + step_y, 0.0,
                             x + step_x, y, 0.0,
                             x, y + step_y, 0.0,
                             x + step_x, y + step_y, 0.0,
                             ]
        return vertices
