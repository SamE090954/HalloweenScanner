from typing import List

import numpy as np

from engine.drawing import Drawing

CREATURE_SHADER_CODE = """
uniform float timer;

vec4 sine_wave(vec4 p) {
    float pi = 3.14159;
    float A_x = 0.001;
    float A_y = 0.01;
    float w = 10.0 * pi;
    float t = 30.0*pi/180.0;

    float y = sin(w*p.x + t) * A_y;
    float x = sin(w*p.x + t) * A_x;

    return vec4(p.x+x, p.y+y, p.z, p.w);
}

void main() {
    gl_Position = sine_wave(gl_ModelViewProjectionMatrix * gl_Vertex);
    gl_FrontColor = gl_Color;
    gl_TexCoord[0].xy = gl_MultiTexCoord0.xy;
}
"""


class DrawingCreature(Drawing):

    def __init__(
            self,
            texid: int,
            grid_x: int = 5,
            grid_y: int = 5,
            shader: int = 0,
            wavy: bool = True,
    ):
        """
        :param texid: ID of texture
        :param grid_x: Mesh elements along axis X
        :param grid_y: Mesh elements along axis Y
        :param shader: ID of shader
        :param wavy: True for fish/ghost-style deformation,
                     False for rigid drawings
        """

        # Disable the wave shader for rigid drawings.
        if not wavy:
            shader = 0

        super(DrawingCreature, self).__init__(
            texid,
            grid_x,
            grid_y,
            shader
        )

        self.is_transparent = True

        self.wavy = wavy

        self.scale = np.array([0.35, 0.9, 0.3])
        self.vector = np.array([0, 0.02, 0.0])
        self.is_alive = True

        self._left = -1.5
        self._right = 1.5
        self._top = -0.7
        self._bottom = 0.3

        # Randomly choose entry direction
        # 0 = left
        # 1 = right
        # 2 = top
        # 3 = bottom
        entry_direction = np.random.randint(4)

        if entry_direction == 0:
            self.position = np.array([
                -2.0,
                np.random.uniform(self._top, self._bottom),
                0.
            ])
            self.vector = np.array([0.02, 0.0, 0.0])

        elif entry_direction == 1:
            self.position = np.array([
                2.0,
                np.random.uniform(self._top, self._bottom),
                0.
            ])
            self.vector = np.array([-0.02, 0.0, 0.0])
            self.scale[0] = -abs(self.scale[0])

        elif entry_direction == 2:
            self.position = np.array([
                np.random.uniform(self._left, self._right),
                -1,
                0.
            ])
            self.vector = np.array([0.0, 0.02, 0.0])

        else:
            self.position = np.array([
                np.random.uniform(self._left, self._right),
                0.5,
                0.
            ])
            self.vector = np.array([0.0, -0.02, 0.0])

        # Randomly flip horizontal direction for vertical entry
        if (
            np.random.randint(2) == 0
            and entry_direction in [2, 3]
        ):
            self.scale[0] = -self.scale[0]
            self.vector[0] = np.random.uniform(-0.01, 0.01)

        # Parameters for animations
        self._animation_stage = 'init'
        self._init_animation_step = np.random.randint(60, 180)
        self._air_resistance = np.random.uniform(0.95, 0.98)


    def _init_creature_velocity(self) -> None:
        self.vector = np.array([
            np.random.uniform(0.002, 0.003),
            np.random.uniform(0.001, 0.002),
            0.0
        ])

        if self.scale[0] < 0:
            self.vector[0] = -self.vector[0]

        if np.random.randint(2) == 0:
            self.vector[1] = -self.vector[1]


    def animation(self) -> None:
        """
        Logic of movement of the drawing.
        """

        self.position += self.vector

        if self._animation_stage == 'init':
            self._init_animation_step -= 1
            self.vector[1] *= self._air_resistance

            if self._init_animation_step == 0:
                self._init_creature_velocity()
                self._animation_stage = 'fly'

        elif self._animation_stage == 'fly':

            # If near border, go the other direction
            if (
                self.position[0] > self._right
                or self.position[0] < self._left
            ):
                self.vector[0] = -self.vector[0]
                self.rotation_vector[1] = 5.0

            if (
                self.position[1] < self._top
                or self.position[1] > self._bottom
            ):
                self.vector[1] = -self.vector[1]

            self.rotate[1] = (
                self.rotate[1] + self.rotation_vector[1]
            ) % 360

            if self.rotate[1] % 180 == 0:
                self.rotation_vector[1] = 0.0

        elif self._animation_stage == 'finish':

            if (
                self.position[0] > self._right + 1.0
                or self.position[0] < self._left - 1.0
            ):
                self.is_alive = False


    def go_away(self) -> None:
        """
        Start animation of drawing leaving the aquarium.
        """

        self.vector[1] = 0.0
        self.vector[0] *= 2
        self._animation_stage = 'finish'

