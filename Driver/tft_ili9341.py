from machine import Pin, SPI
import time
import framebuf


class ILI9341:
    def __init__(self,
                 spi_id=0,
                 baudrate=40_000_000,
                 sck=2, mosi=3, miso=4,
                 cs=5, dc=6, rst=7,
                 width=240, height=320):
        self.width = width
        self.height = height

        self.spi = SPI(spi_id,
                       baudrate=baudrate,
                       polarity=0,
                       phase=0,
                       sck=Pin(sck),
                       mosi=Pin(mosi),
                       miso=Pin(miso))

        self.cs = Pin(cs, Pin.OUT, value=1)
        self.dc = Pin(dc, Pin.OUT, value=0)
        self.rst = Pin(rst, Pin.OUT, value=1)

        # small line buffer for readback (240 pixels * 2 bytes)
        self._linebuf = bytearray(self.width * 2)

        self._init_display()

    # --- Low level helpers ---

    def _write_cmd(self, cmd):
        self.dc.value(0)
        self.cs.value(0)
        self.spi.write(bytes([cmd]))
        self.cs.value(1)

    def _write_data(self, data_bytes):
        self.dc.value(1)
        self.cs.value(0)
        self.spi.write(data_bytes)
        self.cs.value(1)

    def _reset(self):
        self.rst.value(0)
        time.sleep_ms(50)
        self.rst.value(1)
        time.sleep_ms(50)

    def _init_display(self):
        self._reset()

        # Basic ILI9341 init
        self._write_cmd(0x01)  # SWRESET
        time.sleep_ms(50)

        self._write_cmd(0xCF)
        self._write_data(b'\x00\xC1\x30')

        self._write_cmd(0xED)
        self._write_data(b'\x64\x03\x12\x81')

        self._write_cmd(0xE8)
        self._write_data(b'\x85\x00\x78')

        self._write_cmd(0xCB)
        self._write_data(b'\x39\x2C\x00\x34\x02')

        self._write_cmd(0xF7)
        self._write_data(b'\x20')

        self._write_cmd(0xEA)
        self._write_data(b'\x00\x00')

        # Power control
        self._write_cmd(0xC0)
        self._write_data(b'\x23')

        self._write_cmd(0xC1)
        self._write_data(b'\x10')

        # VCOM
        self._write_cmd(0xC5)
        self._write_data(b'\x3E\x28')

        # Memory access control (rotation + BGR)
        self._write_cmd(0x36)
        # 0x48 = MX, BGR for portrait 240x320
        self._write_data(b'\x48')

        # Pixel format 16-bit
        self._write_cmd(0x3A)
        self._write_data(b'\x55')

        # Frame rate
        self._write_cmd(0xB1)
        self._write_data(b'\x00\x18')

        # Display function control
        self._write_cmd(0xB6)
        self._write_data(b'\x08\x82\x27')

        # Gamma
        self._write_cmd(0xF2)
        self._write_data(b'\x00')
        self._write_cmd(0x26)
        self._write_data(b'\x01')

        # Positive gamma
        self._write_cmd(0xE1)
        self._write_data(
            b'\x00\x0E\x14\x03\x11\x07\x31\xC1'
            b'\x48\x08\x0F\x0C\x31\x36\x0F'
        )

        # Sleep out & display on
        self._write_cmd(0x11)
        time.sleep_ms(120)
        self._write_cmd(0x29)  # DISPON
        time.sleep_ms(20)

    def _set_window(self, x0, y0, x1, y1):
        # Column addr set
        self._write_cmd(0x2A)
        self._write_data(bytes([
            (x0 >> 8) & 0xFF, x0 & 0xFF,
            (x1 >> 8) & 0xFF, x1 & 0xFF,
        ]))

        # Row addr set
        self._write_cmd(0x2B)
        self._write_data(bytes([
            (y0 >> 8) & 0xFF, y0 & 0xFF,
            (y1 >> 8) & 0xFF, y1 & 0xFF,
        ]))

        # Write to RAM
        self._write_cmd(0x2C)

    # window setup for RAM READ (no 0x2C)
    def _set_window_for_read(self, x0, y0, x1, y1):
        # Column addr set
        self._write_cmd(0x2A)
        self._write_data(bytes([
            (x0 >> 8) & 0xFF, x0 & 0xFF,
            (x1 >> 8) & 0xFF, x1 & 0xFF,
        ]))

        # Row addr set
        self._write_cmd(0x2B)
        self._write_data(bytes([
            (y0 >> 8) & 0xFF, y0 & 0xFF,
            (y1 >> 8) & 0xFF, y1 & 0xFF,
        ]))

        # RAMRD command
        self._write_cmd(0x2E)

    # --- Drawing primitives ---

    def clear(self, colour=0x0000):
        self.fill_rect(0, 0, self.width, self.height, colour)

    def fill_rect(self, x, y, w, h, colour):
        if w <= 0 or h <= 0:
            return
        x1 = x + w - 1
        y1 = y + h - 1
        if x < 0 or y < 0 or x1 >= self.width or y1 >= self.height:
            return
        self._set_window(x, y, x1, y1)

        hi = (colour >> 8) & 0xFF
        lo = colour & 0xFF
        chunk = bytes([hi, lo]) * 64
        pixels = w * h
        self.dc.value(1)
        self.cs.value(0)
        while pixels > 0:
            n = pixels if pixels < 64 else 64
            self.spi.write(chunk[:n * 2])
            pixels -= n
        self.cs.value(1)

    def pixel(self, x, y, colour):
        if 0 <= x < self.width and 0 <= y < self.height:
            self._set_window(x, y, x, y)
            self._write_data(bytes([(colour >> 8) & 0xFF, colour & 0xFF]))

    def blit_rgb565(self, x, y, w, h, buf):
        self._set_window(x, y, x + w - 1, y + h - 1)
        self._write_data(buf)

    def text(self, x, y, text, colour=0xFFFF, bg=0x0000):
        if not text:
            return
        w = 8 * len(text)
        h = 8
        buf = bytearray(w * h * 2)
        fb = framebuf.FrameBuffer(buf, w, h, framebuf.RGB565)

        # fill bg
        hi_bg = (bg >> 8) & 0xFF
        lo_bg = bg & 0xFF
        for i in range(0, len(buf), 2):
            buf[i] = hi_bg
            buf[i + 1] = lo_bg

        fb.text(text, 0, 0, colour)
        self.blit_rgb565(x, y, w, h, buf)
