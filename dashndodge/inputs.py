"""Action-based input over keyboard (QWERTY + AZERTY) and gamepads."""

import pygame

K = pygame
KEYS = {
    "up": (K.K_UP, K.K_w, K.K_z),
    "down": (K.K_DOWN, K.K_s),
    "left": (K.K_LEFT, K.K_a, K.K_q),
    "right": (K.K_RIGHT, K.K_d),
    "dash": (K.K_SPACE, K.K_k, K.K_c),
    "parry": (K.K_f, K.K_j, K.K_v),
    "spell": (K.K_x, K.K_l, K.K_e),
    "focus": (K.K_LSHIFT, K.K_RSHIFT),
    "confirm": (K.K_RETURN, K.K_KP_ENTER, K.K_SPACE),
    "back": (K.K_ESCAPE, K.K_BACKSPACE),
    "pause": (K.K_ESCAPE, K.K_p),
    "fullscreen": (K.K_F11,),
    "debug": (K.K_F3,),
}

# Standard SDL layout for XInput-style pads.
PAD_BUTTONS = {
    0: ("dash", "confirm"),
    1: ("parry", "back"),
    2: ("parry",),
    3: ("spell",),
    4: ("focus",),
    5: ("focus",),
    6: ("back",),
    7: ("pause",),
}

REPEAT_DELAY = 0.32
REPEAT_RATE = 0.075
DEADZONE = 0.35


class Input:
    def __init__(self):
        self.key_to_actions = {}
        for action, keys in KEYS.items():
            for k in keys:
                self.key_to_actions.setdefault(k, []).append(action)
        self.held_keys = set()
        self.held_pad = set()
        self.pressed = set()
        self.axis = [0.0, 0.0]
        self.hat = (0, 0)
        self.joysticks = {}
        self.repeat = {}
        self.repeated = set()
        self.text_events = []
        self.last_device = "keyboard"
        self._scan_pads()

    def _scan_pads(self):
        try:
            for i in range(pygame.joystick.get_count()):
                j = pygame.joystick.Joystick(i)
                self.joysticks[j.get_instance_id()] = j
        except pygame.error:
            pass

    # ------------------------------------------------------------------
    def handle_event(self, e):
        if e.type == pygame.KEYDOWN:
            self.last_device = "keyboard"
            for a in self.key_to_actions.get(e.key, ()):
                self.held_keys.add(a)
                self.pressed.add(a)
                self.repeat[a] = REPEAT_DELAY
        elif e.type == pygame.KEYUP:
            for a in self.key_to_actions.get(e.key, ()):
                if not self._key_still_held(a):
                    self.held_keys.discard(a)
        elif e.type == pygame.TEXTINPUT:
            self.text_events.append(e.text)
        elif e.type == pygame.JOYDEVICEADDED:
            self._scan_pads()
        elif e.type == pygame.JOYDEVICEREMOVED:
            self.joysticks.pop(getattr(e, "instance_id", None), None)
        elif e.type == pygame.JOYBUTTONDOWN:
            self.last_device = "pad"
            for a in PAD_BUTTONS.get(e.button, ()):
                self.held_pad.add(a)
                self.pressed.add(a)
                self.repeat[a] = REPEAT_DELAY
        elif e.type == pygame.JOYBUTTONUP:
            for a in PAD_BUTTONS.get(e.button, ()):
                self.held_pad.discard(a)
        elif e.type == pygame.JOYAXISMOTION:
            if e.axis in (0, 1):
                old = self._axis_dirs()
                self.axis[e.axis] = e.value
                self._edge_dirs(old)
        elif e.type == pygame.JOYHATMOTION:
            old = self._axis_dirs()
            self.hat = e.value
            self._edge_dirs(old)

    def _key_still_held(self, action):
        pressed = pygame.key.get_pressed()
        return any(pressed[k] for k in KEYS[action])

    def _axis_dirs(self):
        dirs = set()
        x = self.axis[0] if abs(self.axis[0]) > DEADZONE else self.hat[0]
        y = self.axis[1] if abs(self.axis[1]) > DEADZONE else -self.hat[1]
        if x < -0.5:
            dirs.add("left")
        if x > 0.5:
            dirs.add("right")
        if y < -0.5:
            dirs.add("up")
        if y > 0.5:
            dirs.add("down")
        return dirs

    def _edge_dirs(self, old):
        new = self._axis_dirs()
        for d in new - old:
            self.pressed.add(d)
            self.repeat[d] = REPEAT_DELAY
            self.last_device = "pad"

    # ------------------------------------------------------------------
    def held(self, action):
        return action in self.held_keys or action in self.held_pad or action in self._axis_dirs()

    def was_pressed(self, action):
        return action in self.pressed

    def menu(self, action):
        """Pressed, or auto-repeating while held (for menu navigation)."""
        return action in self.pressed or action in self.repeated

    def move_vector(self):
        x = (1 if self.held("right") else 0) - (1 if self.held("left") else 0)
        y = (1 if self.held("down") else 0) - (1 if self.held("up") else 0)
        ax, ay = self.axis
        if abs(ax) > DEADZONE or abs(ay) > DEADZONE:
            x, y = ax, ay
            mag = (x * x + y * y) ** 0.5
            if mag > 1:
                x, y = x / mag, y / mag
            return x, y
        if x and y:
            return x * 0.7071, y * 0.7071
        return float(x), float(y)

    def end_step(self, dt):
        """Called after each logic step: one-shot presses are consumed."""
        self.pressed.clear()
        self.repeated.clear()
        for a in list(self.repeat):
            if self.held(a):
                self.repeat[a] -= dt
                if self.repeat[a] <= 0:
                    self.repeated.add(a)
                    self.repeat[a] = REPEAT_RATE
            else:
                del self.repeat[a]

    def take_text(self):
        t = self.text_events
        self.text_events = []
        return t

    def reset(self):
        self.pressed.clear()
        self.repeated.clear()
        self.held_keys.clear()
        self.held_pad.clear()
        self.repeat.clear()
