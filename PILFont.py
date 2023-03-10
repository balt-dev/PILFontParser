import struct
from os import PathLike
from struct import pack, unpack
from PIL import Image
from pathlib import Path
from typing import IO, Tuple, Iterable, Optional, Self
from dataclasses import dataclass


def _check_header(fp: IO, expected: bytes):
    seek = fp.tell()
    if (actual := fp.read(len(expected))) != expected:
        raise PILFontParsingError(
            f"Incorrect header at {hex(seek)}: expected {expected}, got {actual}"
        )


class PILFontParsingError(Exception):
    """Error while parsing a PIL font."""
    pass


@dataclass
class Glyph(object):
    """
    A dataclass for a glyph in a PILFont.
    @param character: The character this glyph represents.
    @param delta: The amount to move after pasting the glyph.
    @param src_bbox: The box to take from the atlas to get the glyph's bitmap.
    @param dst_bbox: The box to paste the glyph's bitmap to on an image, as offsets from the glyph's position.
    """

    character: bytes
    delta: Tuple[int, int]
    src_bbox: Tuple[int, int, int, int]
    dst_bbox: Tuple[int, int, int, int]

    def __iter__(self):
        return iter((*self.delta, *self.dst_bbox, *self.src_bbox))


@dataclass
class PILFont:
    """
    A class to interact with a PIL font.
    @param atlas_size: A tuple of the glyph atlas's size and mode.
    @param ysize: The height of the font's glyphs.
    @param glyphs: An iterable of the glyphs in the font.
        The index of a glyph corresponds to its ASCII table index.
    """

    atlas: Image
    ysize: int
    glyphs: Iterable[Glyph]

    def __getitem__(self, index: int):
        return self.glyphs[index]

    @classmethod
    def load(
        cls, 
        metrics_path: str | bytes | PathLike, 
        image_path: str | bytes | PathLike
    ) -> Self:
        """
        Loads a PIL font from a file to an object.
        @param metrics_path: A path to the .pil file.
        @param image_path: A path to the glyph atlas.
        """
        with Image.open(image_path) as glyph_atlas:
            with open(metrics_path, "rb") as f:
                _check_header(f, b"PILfont\n;;;;;;")
                ysize = int(f.read(2))
                _check_header(f, b";\nDATA\n")
                glyphs = []
                for i, raw_glyph in enumerate(iter(lambda: f.read(20), b"")):
                    if not len(raw_glyph):
                        break
                    (
                        dx, dy, 
                        dx0, dy0, dx1, dy1, 
                        sx0, sy0, sx1, sy1
                    ) = struct.unpack("!10h", raw_glyph)
                    glyphs.append(
                        Glyph(
                            i.to_bytes(1, "little"),
                            (dx, dy),
                            (sx0, sy0, sx1, sy1),
                            (dx0, dy0, dx1, dy1),
                        )
                    )
            return cls(glyph_atlas.copy(), ysize, glyphs)

    def save(
        self,
        metrics_path: str | bytes | PathLike,
        image_path: str | bytes | PathLike | None = None,
        **image_kwargs,
    ):
        """
        Saves a PIL font to an image and metric file.
        @param metrics_path: A path to the destination .pil file.
        @param image_path: A path to save the glyph atlas at.
        @param image_kwargs: Parameters to send to the image saving function.
        """
        if image_path is not None:
            self.atlas.save(image_path, **image_kwargs)
        with open(metrics_path, "wb+") as fp:
            fp.write(b"PILfont\n;;;;;;")
            fp.write(str(self.ysize).encode("utf-8"))
            fp.write(b";\nDATA\n")
            for i, glyph in enumerate(self.glyphs):
                fp.write(struct.pack("!10h", *glyph))



PILFont.load("10x20.pil", "10x20.pbm").save("10x20_same.pil", "10x20_same.pbm")