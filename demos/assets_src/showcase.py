"""Shared template for every promotional image: exact font faces, type roles, grid and checks.

Case scripts supply content and choose roles; sizes, colours, strokes and positions
come from visual-style.json. Fonts stay in the host: extracted, uniquely named faces
are temporary, never bundled. The Latin face precedes the Chinese face for glyph
fallback in mixed text.
"""
from __future__ import annotations

import json
import os
import tempfile
import warnings
from pathlib import Path

from fontTools.ttLib import TTCollection, TTFont
from matplotlib import font_manager

STYLE = json.loads((Path(__file__).parent / "visual-style.json").read_text(encoding='utf-8'))
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


# ------------------------------------------------------------------ template
COLOURS = STYLE['colors']
ROLES = STYLE['roles']
LAYOUT = STYLE['layout']
STROKES = STYLE['strokes']
W, H = STYLE['canvas']
BG, INK, GREY, RULE = (COLOURS[k] for k in ('background', 'ink', 'secondary', 'rule'))
ACCENT, COMPARISON = COLOURS['accent'], COLOURS['comparison']
L = LAYOUT['margin']
R = LAYOUT['panel_x'] - LAYOUT['margin']          # right edge of the paper field
PX = LAYOUT['panel_x'] + LAYOUT['panel_margin']   # left edge of panel text
PR = W - LAYOUT['panel_margin']                   # right edge of panel text


class Canvas:
    """A 1920x1080 page in pixel coordinates (y downwards); text sits on baselines.

    Left: the paper field with the question and its chart. Right: the evidence panel.
    """

    def __init__(self, lang):
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        self.plt, self.lang = plt, lang
        self.fig = plt.figure(figsize=(W / 100, H / 100), dpi=100, facecolor=BG)
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, W)
        self.ax.set_ylim(H, 0)
        self.ax.axis('off')
        self.ax.add_patch(plt.Rectangle((LAYOUT['panel_x'], 0), W - LAYOUT['panel_x'], H,
                                        color=COLOURS['panel'], lw=0, zorder=0))
        self.fact_bounds = (PX, PR, LAYOUT['facts_top'], LAYOUT['facts_bottom'])

    def text(self, x, y, s, role, color=None, ha='left', rotation=0, va='baseline'):
        spec = ROLES[role]
        key = color or spec['color']
        size = spec.get('size_latin', spec['size']) if self.lang == 'en' else spec['size']
        return self.ax.text(x, y, s, fontsize=size * 0.72, color=COLOURS.get(key, key),
                            fontproperties=properties(spec['face']), ha=ha, va=va, rotation=rotation)

    def frame(self, kicker, title, dek):
        """Kicker, title and dek on paper; the wordmark on the panel. Identical on every image."""
        self.text(L, LAYOUT['kicker_y'], kicker, 'kicker')
        self.text(L, LAYOUT['title_y'], title, 'title')
        self.text(L, LAYOUT['dek_y'], dek, 'dek')
        self.text(PX, LAYOUT['masthead_y'], 'P R A X I S', 'masthead')

    def facts(self, items, notes=()):
        """Up to four (label, value, note, tone) facts, spaced evenly down the panel.

        tone is 'lead' (cream), 'comparison' (light vermilion) or 'context' (muted).
        """
        if not 1 <= len(items) <= 4:
            raise ValueError('An image carries one to four evidence facts')
        role = 'value' if len(items) <= 2 else 'value_compact'
        size = ROLES[role]['size']
        drop = 30 + size * .95  # label baseline to value baseline, clear of the face's ascent
        heights = [drop + (46 if note else 0) for _, _, note, _ in items]
        top, bottom = LAYOUT['facts_top'], LAYOUT['facts_bottom'] - (110 if notes else 0)
        gap = (bottom - top - sum(heights)) / (len(items) + 1)
        tones = {'lead': 'panel_ink', 'comparison': 'panel_comparison', 'context': 'panel_secondary'}
        y = top + gap
        for (label, value, note, tone), height in zip(items, heights):
            self.text(PX, y + 22, label, 'label')
            self.text(PX, y + drop, value, role, tones[tone])
            if note:
                self.text(PX, y + height, note, 'note')
            y += height + gap
        for yy, line in zip(LAYOUT['panel_notes_y'], notes):
            self.text(PX, yy, line, 'panel_note')
        if notes:
            self.ax.plot([PX, PR], [LAYOUT['panel_notes_y'][0] - 50] * 2, color=COLOURS['panel_rule'], lw=STROKES['hairline'])

    def footer(self, claim, condition):
        self.text(L, LAYOUT['claim_y'], claim, 'claim')
        self.text(L, LAYOUT['condition_y'], condition, 'condition')

    def axes(self, left, right, top, bottom, grid=True):
        a = self.fig.add_axes([left / W, 1 - bottom / H, (right - left) / W, (bottom - top) / H], facecolor='none')
        for name, spine in a.spines.items():
            spine.set_visible(name == 'bottom')
            spine.set_color(INK)
            spine.set_linewidth(STROKES['hairline'])
        a.tick_params(colors=GREY, length=0, pad=12)
        a.tick_params(axis='x', length=6, width=STROKES['hairline'], color=INK)
        if grid:
            a.grid(axis='y', color=RULE, lw=STROKES['hairline'])
            a.set_axisbelow(True)
        a.minorticks_off()
        return a

    def ticks(self, a):
        for label in a.get_xticklabels() + a.get_yticklabels():
            label.set_fontproperties(properties(ROLES['axis']['face']))
            label.set_fontsize(ROLES['axis']['size'] * 0.72)
            label.set_color(GREY)

    def key(self, x, y, items, ha='left'):
        """Inline legend: (label, colour, style) on baseline y; ha='right' ends at x."""
        renderer = self.fig.canvas.get_renderer()
        widths = [self.text(0, -100, label, 'key').get_window_extent(renderer).width for label, _, _ in items]
        for t in self.ax.texts[-len(items):]:
            t.remove()
        total = sum(46 + w for w in widths) + 36 * (len(items) - 1)
        x = x - total if ha == 'right' else x
        for (label, colour, style), width in zip(items, widths):
            if style == 'band':
                self.ax.add_patch(self.plt.Rectangle((x, y - 15), 34, 14, color=colour, alpha=.16, lw=0))
            elif style == 'dot':
                self.ax.plot([x + 17], [y - 7], 'o', ms=STROKES['marker'], color=colour)
            else:
                self.ax.plot([x, x + 34], [y - 7, y - 7], color=colour, lw=STROKES['secondary'],
                             ls=(0, (4, 2.4)) if style == 'dashed' else '-')
            self.text(x + 46, y, label, 'key')
            x += 46 + width + 36

    def save(self, path):
        renderer = self.fig.canvas.get_renderer()
        for text in self.ax.texts:
            box = text.get_window_extent(renderer)
            if text.get_position()[0] < LAYOUT['panel_x'] and box.x1 > R + 8:
                raise ValueError('Text crosses into the evidence panel: ' + text.get_text())
            if text.get_position()[0] >= LAYOUT['panel_x'] and box.x1 > PR + 8:
                raise ValueError('Text leaves the panel margin: ' + text.get_text())
        validate_and_record(self, path)
        self.fig.savefig(path, dpi=100, facecolor=BG)
        self.plt.close(self.fig)
