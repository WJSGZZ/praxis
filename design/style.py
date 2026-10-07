"""Shared tokens, typography, layout checks and exports for showcase graphics."""
from contextlib import contextmanager
from pathlib import Path
import json
import os
import tempfile
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.text import Text

BUNDLE = Path(__file__).resolve().parents[1]
TOKENS = json.loads(Path(__file__).with_name('tokens.json').read_text())


class Style:
    def __init__(self, display, regular):
        self.c = TOKENS['palette']
        self.type = TOKENS['typography']
        self.display, self.regular = display, regular

    def font(self, lang='en', role='body'):
        display = role in {'display', 'section'}
        if lang == 'zh':
            return FontProperties(fname=str(self.display if display else self.regular))
        return FontProperties(family=self.type['latin_serif' if display else 'latin_sans'])

    def canvas(self):
        s = TOKENS['canvas']
        fig = plt.figure(figsize=(s['width_inches'], s['height_inches']), facecolor=self.c['paper'])
        ax = fig.add_axes([0, 0, 1, 1]); ax.axis('off')
        ax.set_xlim(0, 1); ax.set_ylim(0, 1)
        return fig, ax

    def text(self, ax, x, y, value, *, lang='en', role='body', color='ink', size=None, **kw):
        return ax.text(x, y, value, fontsize=size or self.type[role],
                       fontproperties=self.font(lang, role), color=self.c[color], va='top', **kw)

    def header(self, ax, right):
        l = TOKENS['layout']
        self.text(ax, l['left'], l['header'], 'P R A X I S', role='label', color='accent', weight='bold')
        self.text(ax, l['right'], l['header'], right, role='note', color='muted', ha='right')
        ax.plot([l['left'], l['right']], [l['header_rule']]*2, color=self.c['rule'], lw=.8)

    def save(self, fig, path):
        # Check exported text against the whole canvas; doesn't replace visual review.
        fig.canvas.draw(); renderer = fig.canvas.get_renderer()
        width, height = fig.canvas.get_width_height()
        for text in fig.findobj(Text):
            if text.get_visible() and text.get_text().strip():
                box = text.get_window_extent(renderer)
                if box.x0 < -1 or box.y0 < -1 or box.x1 > width+1 or box.y1 > height+1:
                    raise ValueError(f'Text exceeds canvas: {text.get_text()}')
        fig.savefig(path, dpi=TOKENS['canvas']['dpi'], facecolor=self.c['paper'])
        plt.close(fig)


@contextmanager
def showcase_style():
    """Use separately selected Chinese faces, never implicit collection fallbacks."""
    paths = sorted(Path('/System/Library/AssetsV2').glob('com_apple_MobileAsset_Font*/*.asset/AssetData/PingFang.ttc'))
    default = paths[0] if paths else Path('/System/Library/Fonts/PingFang.ttc')
    regular = Path(os.environ.get('PRAXIS_ZH_REGULAR', str(default)))
    display = Path(os.environ.get('PRAXIS_ZH_DISPLAY', '/System/Library/Fonts/Supplemental/Songti.ttc'))
    if not regular.is_file() or not display.is_file():
        raise FileNotFoundError('Set PRAXIS_ZH_REGULAR and PRAXIS_ZH_DISPLAY to locally installed Chinese font files.')
    scratch = BUNDLE / '.session/showcase-fonts'; scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=scratch) as temp:
        def face(source, name, target):
            if source.suffix.lower() != '.ttc':
                return source
            from fontTools.ttLib import TTCollection
            collection = TTCollection(source)
            try:
                chosen = next((f for f in collection.fonts if f['name'].getDebugName(6) == name), None)
                if chosen is None:
                    raise ValueError(f'Font face not present in collection: {name}')
                path = Path(temp) / target
                chosen.save(path)
                return path
            finally:
                collection.close()
        regular = face(regular, os.environ.get('PRAXIS_ZH_REGULAR_FACE', TOKENS['typography']['chinese_regular_face']), 'regular.ttf')
        display = face(display, os.environ.get('PRAXIS_ZH_DISPLAY_FACE', TOKENS['typography']['chinese_display_face']), 'display.ttf')
        yield Style(display, regular)
    scratch.rmdir()
