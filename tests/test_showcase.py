"""Published bilingual images must retain identical fixed English/data regions.

Check the shipped pixels, independently of the rendering code or host fonts.
"""
from pathlib import Path

from PIL import Image, ImageChops
import pytest

ROOT = Path(__file__).resolve().parents[1] / 'demos'


@pytest.mark.parametrize('case,zh,en,regions', [
    ('cumcm-1998-a', 'overview-zh.png', 'overview-en.png',
     [(1300, 472, 1670, 553), (1300, 699, 1670, 780)]),
    ('cumcm-1998-a', 'risk-return-zh.png', 'risk-return.png',
     [(1300, 472, 1670, 553), (1300, 699, 1670, 780)]),
    ('mcm-2016-a', 'overview-zh.png', 'overview-en.png',
     [(1229, 430 + 135*i, 1500, 487 + 135*i) for i in range(4)]),
    ('collatz-research', 'overview-zh.png', 'overview-en.png',
     [(1230, 443, 1500, 501), (1230, 661, 1500, 719)]),
    ('domino-research', 'overview-zh.png', 'overview-en.png',
     [(1230, 443, 1500, 501), (1230, 661, 1500, 719)]),
])
def test_bilingual_fixed_regions_are_pixel_identical(case, zh, en, regions):
    with Image.open(ROOT / case / 'assets' / zh) as first, Image.open(ROOT / case / 'assets' / en) as second:
        assert first.size == second.size == (1920, 1080)
        for region in [(125, 60, 340, 110), (1430, 60, 1805, 110), *regions]:
            crop = first.convert('RGB').crop(region)
            assert any(low != high for low, high in crop.getextrema()), ('Empty inspection region', case, region)
            assert ImageChops.difference(crop, second.convert('RGB').crop(region)).getbbox() is None, (case, region)
