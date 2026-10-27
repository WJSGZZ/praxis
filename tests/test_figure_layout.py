"""Rendered-ink checks, including deliberate bounding-box false positives."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pytest

from scripts.figure_layout import inspect


@pytest.fixture(autouse=True)
def close_figures():
    yield
    plt.close('all')


def scene():
    fig, ax = plt.subplots(figsize=(4, 3), dpi=100)
    ax.set(xlim=(0, 10), ylim=(0, 10), xlabel='normal axis label')
    return fig, ax


def hits(fig):
    report = inspect(fig, figure_id='Figure 7')
    assert report['diagnostic_only'] is True
    assert 'passed' not in report
    return report['warnings']


def test_real_crossing_and_required_locations():
    fig, ax = scene()
    line, = ax.plot([0, 10], [5, 5], gid='crossing')
    ax.text(4, 5, 'crossed', va='center')
    warning = hits(fig)[0]
    assert warning['figure'] == 'Figure 7'
    assert warning['text'] == 'crossed'
    assert warning['axis'] == 0
    assert warning['object_id'] == 'crossing'
    assert len(warning['bbox_display_px']) == 4
    assert warning['overlap_pixels'] > 0


def test_diagonal_bbox_overlap_is_not_an_ink_intersection():
    fig, ax = scene()
    ax.plot([0, 10], [0, 10])
    ax.text(1, 8, 'clear')
    assert hits(fig) == []


def test_sparse_markers_do_not_fill_their_bounding_box():
    fig, ax = scene()
    ax.plot([1, 9], [5, 5], linestyle='none', marker='o')
    ax.text(4, 5, 'clear', va='center')
    assert hits(fig) == []
    ax.text(1, 5, 'marker', va='center')
    assert any(w['text'] == 'marker' for w in hits(fig))


def test_fill_between_and_scatter():
    fig, ax = scene()
    ax.fill_between([1, 9], [4, 4], [6, 6], gid='band')
    ax.scatter([2], [8], s=160, gid='points')
    ax.text(4, 5, 'band', va='center')
    ax.text(2, 8, 'point', va='center')
    found = {(w['text'], w['object_id']) for w in hits(fig)}
    assert ('band', 'band') in found
    assert ('point', 'points') in found


def test_clean_legend_labels_not_compared_with_own_handles():
    fig, ax = scene()
    ax.plot([0, 10], [0, 1], label='clean')
    ax.legend(loc='upper left')
    assert hits(fig) == []


def test_legend_frame_covers_actual_data():
    fig, ax = scene()
    ax.plot([0, 10], [9, 9], label='data')
    ax.legend(loc='upper left')
    assert any(w['code'] == 'figure_legend_data_overlap' for w in hits(fig))


@pytest.mark.parametrize('values', [[5, np.nan, 5], np.ma.array([5,5,5], mask=[0,1,0])])
def test_missing_data_does_not_bridge_disconnected_paths(values):
    fig, ax = scene()
    ax.plot([1, 5, 9], values)
    ax.text(4, 5, 'clear', va='center')
    assert hits(fig) == []


def test_clip_invisible_alpha_and_reference_exclusion():
    fig, ax = scene()
    ax.plot([1,9], [5,5], alpha=0)
    ax.plot([1,9], [5,5], visible=False)
    reference = ax.axhline(5, gid='budget')
    ax.text(4,5,'reference', va='center')
    assert inspect(fig, exclude_artists=[reference])['warnings'] == []
    assert inspect(fig, exclude_artists=[reference])['exclusions']['artist_ids'] == ['budget']
    reference.remove()
    ax.plot([11, 12], [5,5])
    ax.text(11,5,'outside', va='center', clip_on=False)
    assert hits(fig) == []


def test_collection_clip_path_and_marker_shape():
    from matplotlib.patches import Circle
    fig, ax = scene()
    points = ax.scatter([5], [5], s=3000, marker='x')
    ax.text(5, 6, 'gap', ha='center', va='center', fontsize=5)
    # The x marker's outer box covers this label, its actual strokes do not.
    assert hits(fig) == []
    points.remove()
    band = ax.fill_between([0,10],[0,0],[10,10])
    band.set_clip_path(Circle((1,1), .5, transform=ax.transData))
    assert hits(fig) == []


def test_transparent_rgba_colors_and_collection_alpha_array():
    fig, ax = scene()
    ax.scatter([4, 5], [5, 5], alpha=np.array([0., 0.]))
    ax.plot([1,9], [5,5], color=(1,0,0,0))
    ax.text(4,5,'clear', va='center')
    assert hits(fig) == []


def test_disconnected_moveto_path_does_not_draw_a_bridge():
    from matplotlib.path import Path
    from matplotlib.patches import PathPatch
    fig, ax = scene()
    path = Path([(1,5),(2,5),(8,5),(9,5)],
                [Path.MOVETO, Path.LINETO, Path.MOVETO, Path.LINETO])
    ax.add_patch(PathPatch(path, fill=False))
    ax.text(4,5,'clear', va='center')
    assert hits(fig) == []


def test_transparent_label_is_not_a_collision_target():
    fig, ax = scene()
    ax.plot([1,9],[5,5])
    ax.text(4,5,'invisible label', va='center', color=(0,0,0,0))
    assert hits(fig) == []
