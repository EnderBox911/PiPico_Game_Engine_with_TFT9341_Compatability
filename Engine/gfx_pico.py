from Driver.tft_ili9341 import ILI9341
import framebuf

class PicoGFX:
    """
    Graphics wrapper for the ILI9341 display.
    Public API (what game code should use):
    - clear(colour=0x0000)
    - fill_rect(x, y, w, h, colour=0xFFFF)
    - safe_fill_rect(x, y, w, h, colour=0xFFFF)
    - draw_text(x, y, text, colour=0xFFFF, bg=None, scale=1)
    - get_text_size(text, scale=1) -> (w, h)
    - load_sprite_rgb565(path, w, h)
    - draw_sprite(sprite, x, y)
    - draw_image_rgb565(x, y, w, h, buf)
    - present()
    """

    def __init__(self):
        self.tft = ILI9341()
        self.width = self.tft.width
        self.height = self.tft.height

        # Cache for text sprites (for repeated labels like "PLAYER", "DEALER", etc.)
        # key: (text, colour, bg, scale) -> sprite dict
        self._text_cache = {}

    # -------------------------------------------------------------------------
    # Basic drawing
    # -------------------------------------------------------------------------

    def clear(self, colour=0x0000):
        """Fill the entire display with the given colour."""
        self.tft.clear(colour)

    def fill_rect(self, x, y, w, h, colour=0xFFFF):
        """Draw a filled rectangle of a given colour (no clipping)."""
        self.tft.fill_rect(x, y, w, h, colour)

    def safe_fill_rect(self, x, y, w, h, colour=0xFFFF):
        """
        Like fill_rect but clamps to the visible screen.
        This avoids weird behaviour from the driver if coordinates go off-screen.
        Use this when you're not 100% sure your rectangle is in bounds.
        """
        if w <= 0 or h <= 0:
            return

        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.width, x + w)
        y1 = min(self.height, y + h)

        cw = x1 - x0
        ch = y1 - y0

        if cw <= 0 or ch <= 0:
            return

        self.fill_rect(x0, y0, cw, ch, colour)

    def draw_image_rgb565(self, x, y, w, h, buf):
        """Draw raw RGB565 image buffer at (x, y)."""
        self.tft.blit_rgb565(x, y, w, h, buf)

    def present(self):
        """
        For compatibility with a potential buffered backend.
        Drawing is currently immediate so this does nothing.
        Call at the end of each frame anyway so games don't care if you later add double buffering.
        """
        pass

    def clear_caches(self):
        self._text_cache = {}
        import gc
        gc.collect()

    # -------------------------------------------------------------------------
    # Text drawing
    # -------------------------------------------------------------------------

    def get_text_size(self, text, scale=1):
        """
        Return (width, height) in pixels for the given text at a scale.
        Base font is 8x8 per character.
        scale=2 -> 16x16 per character, etc.
        """
        if scale < 1:
            scale = 1

        base_w = 8 * len(text)
        base_h = 8
        return base_w * scale, base_h * scale

    def draw_text(self, x, y, text, colour=0xFFFF, bg=None, scale=1):
        """
        Draw text at (x, y).
        - scale = 1 and bg is None: uses the driver's 8x8 text directly (fast)
        - otherwise: renders text into a sprite and blits it (bigger or with bg)
        Coordinates are clamped so the entire text box stays on-screen.
        """
        if not text:
            return

        if scale < 1:
            scale = 1

        # Compute final on-screen size
        w, h = self.get_text_size(text, scale)

        # Clamp position so entire text area is visible
        if x < 0:
            x = 0
        if y < 0:
            y = 0
        if x + w > self.width:
            x = self.width - w
        if y + h > self.height:
            y = self.height - h

        # Small text path: fastest, direct to driver if no bg requested
        if scale == 1 and bg is None:
            # IMPORTANT: correct argument order for your driver:
            # text(self, x, y, text, colour=0xFFFF, bg=0x0000)
            self.tft.text(x, y, text, colour)
            return

        # Otherwise: render into a sprite and draw that sprite
        sprite = self._get_text_sprite(text, colour, bg, scale)
        self.draw_sprite(sprite, x, y)

    # -------------------------------------------------------------------------
    # Sprite loading / drawing
    # -------------------------------------------------------------------------

    def load_sprite_rgb565(self, path, w, h):
        """
        Load a RGB565 .bin sprite from SD or flash and return a sprite dict:
        { "w": w, "h": h, "data": <bytes>, "path": <str or None> }
        Use draw_sprite() to draw it.
        """
        with open(path, "rb") as f:
            data = f.read()
        return {"w": w, "h": h, "data": data, "path": path}

    def draw_sprite(self, sprite, x, y):
        """Draw a previously loaded sprite (or text sprite)."""
        self.draw_image_rgb565(x, y, sprite["w"], sprite["h"], sprite["data"])

    # -------------------------------------------------------------------------
    # Internal helpers for text sprites
    # -------------------------------------------------------------------------

    def _get_text_sprite(self, text, colour, bg, scale):
        """
        Internal: get or build a text sprite for (text, colour, bg, scale).
        This is used by draw_text() when scale > 1 or bg is specified.
        """
        key = (text, colour, bg, scale)
        spr = self._text_cache.get(key)
        if spr is not None:
            return spr
        spr = self._render_text_sprite(text, colour, bg, scale)
        self._text_cache[key] = spr
        return spr

    def _render_text_sprite(self, text, colour, bg, scale):
        """
        Internal: render text into an RGB565 sprite dict, handling scaling.
        Returns a sprite dict: { "w", "h", "data", "path": None }.
        """
        if scale < 1:
            scale = 1

        base_w = 8 * len(text)
        base_h = 8

        # 1) render base text into small RGB565 buffer via framebuf
        small_buf = bytearray(base_w * base_h * 2)
        fb = framebuf.FrameBuffer(small_buf, base_w, base_h, framebuf.RGB565)

        # fill background if bg is None: use black for base
        if bg is None:
            hi_bg = 0
            lo_bg = 0
        else:
            hi_bg = (bg >> 8) & 0xFF
            lo_bg = bg & 0xFF

        for i in range(0, len(small_buf), 2):
            small_buf[i] = hi_bg
            small_buf[i + 1] = lo_bg

        fb.text(text, 0, 0, colour)

        # No scaling needed?
        if scale == 1:
            return {
                "w": base_w,
                "h": base_h,
                "data": small_buf,
                "path": None,
            }

        # 2) scale into larger buffer using nearest-neighbour
        out_w = base_w * scale
        out_h = base_h * scale
        out_buf = bytearray(out_w * out_h * 2)

        for sy in range(out_h):
            src_y = sy // scale
            for sx in range(out_w):
                src_x = sx // scale
                src_index = 2 * (src_y * base_w + src_x)
                dst_index = 2 * (sy * out_w + sx)
                out_buf[dst_index] = small_buf[src_index]
                out_buf[dst_index + 1] = small_buf[src_index + 1]

        return {
            "w": out_w,
            "h": out_h,
            "data": out_buf,
            "path": None,
        }

    # -------------------------------------------------------------------------
    # Backwards compatibility helpers (optional)
    # -------------------------------------------------------------------------

    def draw_text_scaled(self, x, y, text, color=0xFFFF, bg=0x0000, scale=2):
        """Wrapper around draw_text() for old code."""
        self.draw_text(x, y, text, colour=color, bg=bg, scale=scale)

    def make_text_sprite(self, text, color=0xFFFF, bg=0x0000, scale=1):
        """Wrapper around _render_text_sprite() for old code."""
        return self._render_text_sprite(text, color, bg, scale)
