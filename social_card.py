# ::ILANG [TYPE:python-module][ROLE:static-social-card]
# ::RULE{deterministic PNG generated locally, no API or paid service}
# ::BOUNDARY{never:load remote fonts or infer unverified discount amounts}
"""Generate an optional 1200×630 Open Graph preview PNG using stdlib only."""
import struct
import zlib

GLYPHS = {
    "A": ("01110","10001","10001","11111","10001","10001","10001"),
    "B": ("11110","10001","10001","11110","10001","10001","11110"),
    "C": ("01111","10000","10000","10000","10000","10000","01111"),
    "D": ("11110","10001","10001","10001","10001","10001","11110"),
    "E": ("11111","10000","10000","11110","10000","10000","11111"),
    "F": ("11111","10000","10000","11110","10000","10000","10000"),
    "G": ("01111","10000","10000","10111","10001","10001","01111"),
    "H": ("10001","10001","10001","11111","10001","10001","10001"),
    "I": ("11111","00100","00100","00100","00100","00100","11111"),
    "J": ("00111","00010","00010","00010","10010","10010","01100"),
    "K": ("10001","10010","10100","11000","10100","10010","10001"),
    "L": ("10000","10000","10000","10000","10000","10000","11111"),
    "M": ("10001","11011","10101","10101","10001","10001","10001"),
    "N": ("10001","11001","10101","10011","10001","10001","10001"),
    "O": ("01110","10001","10001","10001","10001","10001","01110"),
    "P": ("11110","10001","10001","11110","10000","10000","10000"),
    "Q": ("01110","10001","10001","10001","10101","10010","01101"),
    "R": ("11110","10001","10001","11110","10100","10010","10001"),
    "S": ("01111","10000","10000","01110","00001","00001","11110"),
    "T": ("11111","00100","00100","00100","00100","00100","00100"),
    "U": ("10001","10001","10001","10001","10001","10001","01110"),
    "V": ("10001","10001","10001","10001","10001","01010","00100"),
    "W": ("10001","10001","10001","10101","10101","11011","10001"),
    "X": ("10001","10001","01010","00100","01010","10001","10001"),
    "Y": ("10001","10001","01010","00100","00100","00100","00100"),
    "Z": ("11111","00001","00010","00100","01000","10000","11111"),
    " ": ("00000",)*7,
    "-": ("00000","00000","00000","11111","00000","00000","00000"),
}


def create_png(target, brand):
    width, height = 1200, 630
    pixels = bytearray(width * height * 3)
    for y in range(height):
        for x in range(width):
            i = (y * width + x) * 3
            pixels[i] = 13 + y // 75
            pixels[i+1] = 25 + x // 95
            pixels[i+2] = 47 + y // 36
    def rect(x, y, w, h, color):
        for row in range(max(0, y), min(height, y+h)):
            for col in range(max(0, x), min(width, x+w)):
                idx = (row*width+col)*3
                pixels[idx:idx+3] = bytes(color)
    rect(76, 118, 12, 390, (32, 174, 192))
    rect(89, 118, 2, 390, (97, 225, 216))
    rect(76, 535, 1038, 2, (50, 84, 116))
    rect(870, 110, 270, 18, (27, 63, 96))
    rect(910, 140, 230, 18, (28, 79, 112))
    rect(948, 170, 192, 18, (39, 116, 140))
    def write(string, x, y, scale, color):
        for char in string.upper():
            glyph = GLYPHS.get(char, GLYPHS[" "])
            for row, pattern in enumerate(glyph):
                for col, filled in enumerate(pattern):
                    if filled == "1":
                        rect(x+col*scale, y+row*scale, scale-1, scale-1, color)
            x += 6*scale
    write((brand or "VPS DEALS").replace("_", "-")[:21], 135, 205, 10, (235, 244, 251))
    write("VERIFIED OFFERS", 137, 360, 6, (90, 222, 217))
    def chunk(kind, data):
        return (struct.pack("!I",len(data)) + kind + data +
                struct.pack("!I",zlib.crc32(kind+data)&0xffffffff))
    uncompressed = b"".join(
        b"\x00" + bytes(pixels[y*width*3:(y+1)*width*3])
        for y in range(height)
    )
    png = (b"\x89PNG\r\n\x1a\n" +
           chunk(b"IHDR",struct.pack("!2I5B",width,height,8,2,0,0,0)) +
           chunk(b"IDAT",zlib.compress(uncompressed,6)) +
           chunk(b"IEND",b""))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(png)