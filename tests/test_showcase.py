"""Published bilingual images must retain identical fixed English/data regions.

Check the shipped pixels, independently of the rendering code or host fonts.
"""
from pathlib import Path

from PIL import Image, ImageChops
import pytest

ROOT = Path(__file__).resolve().parents[1] / 'demos'


def _values(count, notes=True, panel_notes=False):
    """Value-row regions of the evidence panel, mirroring Canvas.facts and visual-style.json."""
    size = 100 if count <= 2 else 66
    drop = 30 + size * .95
    heights = [drop + (46 if notes else 0)] * count
    top, bottom = 210, 968 - (110 if panel_notes else 0)
    gap = (bottom - top - sum(heights)) / (count + 1)
    regions, y = [], top + gap
    for height in heights:
        regions.append((1344, int(y + drop - size * .78), 1824, int(y + drop + 8)))
        y += height + gap
    return regions


@pytest.mark.parametrize('case,zh,en,regions', [
    ('cumcm-1998-a', 'overview-zh.png', 'overview-en.png', _values(2, panel_notes=True)),
    ('cumcm-1998-a', 'risk-return-zh.png', 'risk-return.png', _values(2, panel_notes=True)),
    ('mcm-2016-a', 'overview-zh.png', 'overview-en.png', _values(4, notes=False)),
    ('collatz-research', 'overview-zh.png', 'overview-en.png', _values(2)),
    ('domino-research', 'overview-zh.png', 'overview-en.png', _values(2)),
])
def test_bilingual_fixed_regions_are_pixel_identical(case, zh, en, regions):
    with Image.open(ROOT / case / 'assets' / zh) as first, Image.open(ROOT / case / 'assets' / en) as second:
        assert first.size == second.size == (1920, 1080)
        for region in [(108, 108, 700, 140), (1340, 108, 1600, 140), *regions]:
            crop = first.convert('RGB').crop(region)
            assert any(low != high for low, high in crop.getextrema()), ('Empty inspection region', case, region)
            assert ImageChops.difference(crop, second.convert('RGB').crop(region)).getbbox() is None, (case, region)
