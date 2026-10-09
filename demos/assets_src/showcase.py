"""Exact local font roles and shared geometry checks for promotional images.

Fonts stay in the host: extracted, uniquely named faces are temporary, never bundled.
The Latin face precedes the Chinese face for glyph fallback in mixed text.
"""
from __future__ import annotations

import json
import os
import tempfile
import warnings
from pathlib import Path

from fontTools.ttLib import TTCollection, TTFont
from matplotlib import font_manager

STYLE = json.loads((Path(__file__).parent / "visual-style.json").read_text())
FACES = {}


class FontSession:
    def __enter__(self):
        root = Path(__file__).resolve().parents[2] / '.session'
        root.mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix='showcase-fonts-', dir=root)
        for role, spec in STYLE['fonts'].items():
            # An explicit licensed local file may replace platform discovery.
            override = os.environ.get('PRAXIS_FONT_' + role.upper())
            source = Path(override) if override else Path(font_manager.findfont(spec['family'], fallback_to_default=False))
            collection = TTCollection(source) if source.suffix.lower() in ('.ttc', '.otc') else None
            candidates = collection.fonts if collection else [TTFont(source)]
            matches = [font for font in candidates if spec['postscript'] in
                       {n.toUnicode() for n in font['name'].names if n.nameID == 6}]
            if len(matches) != 1:
                raise ValueError('Exact font face not found: ' + spec['postscript'])
            font = matches[0]
            family = 'PraxisShowcase_' + role
            for name in font['name'].names:
                if name.nameID in (1, 4, 6, 16):
                    name.string = family.encode(name.getEncoding())
            target = Path(self.temporary.name) / (role + '.ttf')
            font.save(target)
            if collection:
                collection.close()
            else:
                font.close()
            font_manager.fontManager.addfont(target)
            FACES[role] = family
        return self

    def __exit__(self, *args):
        self.temporary.cleanup()
        FACES.clear()


def properties(kind='sans'):
    if not FACES:
        raise RuntimeError('Render within FontSession; font fallback is not allowed.')
    return font_manager.FontProperties(family=[FACES['latin_' + kind], FACES['chinese_' + kind]])


def validate_and_record(canvas, path):
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter('always')
        canvas.fig.canvas.draw()
    missing = [str(w.message) for w in recorded if 'Glyph' in str(w.message) and 'missing' in str(w.message)]
    if missing:
        raise ValueError('Font coverage failure: ' + '; '.join(missing))
    renderer = canvas.fig.canvas.get_renderer()
    boxes = []
    for axes in canvas.fig.axes:
        texts = list(axes.texts) + (axes.get_xticklabels() + axes.get_yticklabels() if axes.axison else [])
        for text in texts:
            if not text.get_visible() or not text.get_text():
                continue
            box = text.get_window_extent(renderer)
            width, height = canvas.fig.canvas.get_width_height()
            if box.x0 < 0 or box.x1 > width or box.y0 < 0 or box.y1 > height:
                raise ValueError('Text outside canvas: ' + text.get_text())
            if axes is canvas.ax and hasattr(canvas, 'fact_bounds'):
                x0, x1, y0, y1 = canvas.fact_bounds
                x, y = text.get_position()
                if x >= x0 and y0 <= y <= y1 and (box.x0 < x0 - 2 or box.x1 > x1):
                    raise ValueError('Fact exceeds its column: ' + text.get_text())
            boxes.append((text, box))
    for index, (left, box) in enumerate(boxes):
        for right, other in boxes[index + 1:]:
            if min(box.x1, other.x1) > max(box.x0, other.x0) + 1 and min(box.y1, other.y1) > max(box.y0, other.y0) + 1:
                raise ValueError(f'Text overlap: {left.get_text()} / {right.get_text()}')
    metrics = os.environ.get('PRAXIS_SHOWCASE_METRICS')
    if metrics:
        target = Path(metrics)
        data = json.loads(target.read_text()) if target.exists() else {}
        data[str(path)] = [{'text': text.get_text(), 'bounds': list(box.bounds),
                            'families': text.get_fontfamily()} for text, box in boxes]
        target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
