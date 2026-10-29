"""A clean export must retain a usable no-TeX plotting preset."""
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import scienceplots  # noqa: F401: registers upstream styles

from scripts.build_plugin import public_files

ROOT = Path(__file__).resolve().parents[1]


def test_shared_style_is_exported_and_renders_without_tex(tmp_path):
    preset = ROOT / 'templates/praxis.mplstyle'
    assert preset in public_files(ROOT)
    with plt.style.context(['science', 'no-latex', preset]):
        figure, axis = plt.subplots(figsize=(6.5, 4))
        axis.plot([0, 1, 2], [0, 1, 4], label='Measured')
        axis.set(xlabel='Time (s)', ylabel=r'Area ($m^2$)', title='Observed growth')
        axis.legend()
        assert not matplotlib.rcParams['text.usetex']
        assert axis.xaxis.label.get_fontsize() >= 12
        target = tmp_path / 'figure.pdf'
        figure.savefig(target)
        plt.close(figure)
    assert target.read_bytes().startswith(b'%PDF')
