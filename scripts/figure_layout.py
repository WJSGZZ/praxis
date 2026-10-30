"""Advisory Matplotlib text/data intersections using rendered artist ink.

Call ``inspect(fig, figure_id='Figure 1')`` after final layout and before savefig.
Coordinates are display pixels at the figure's current DPI, origin bottom left.
A hit means data ink intersects a text bounding rectangle, not proof a glyph is
obscured: white space within text, intentional labels and z-order need review.
Tick labels, spines, grids, annotation arrows and legend sample handles are not
comparison targets. Reference lines are data unless explicitly excluded.
"""
from __future__ import annotations

import numpy as np
from matplotlib.backends.backend_agg import RendererAgg
from matplotlib.text import Text
from matplotlib.colors import to_rgba


def _identity(artist, axis, kind, index):
    return artist.get_gid() or f'axes[{axis}].{kind}[{index}]'


def inspect(figure, *, figure_id=None, exclude_artists=(), reference_lines=None, reference_context=None):
    """Return warning-only findings; never return a pass/fail certificate.

    Supports Line2D, axes collections (scatter, fill_between, etc.) and data
    patches. Individual artists are rasterized with their real transform,
    linewidth, markers and clip; no line/collection bounding-box proxy is used.
    NaN/masked/disconnected paths are handled by Matplotlib itself. Raster
    precision is limited to the figure's current DPI. Custom images, 3D artists,
    path effects and filters require visual review. No file is saved or changed.
    Exclude reference artists by object identity; exclusions remain in report.
    """
    figure.canvas.draw()  # finalize layout, annotation transforms and legend frame
    width, height = map(lambda n: max(1, int(n)), figure.bbox.size)
    renderer = RendererAgg(width, height, figure.dpi)
    # draw once with Agg too: text metrics must match the raster comparison
    figure.draw(renderer)
    excluded = {id(a) for a in exclude_artists}
    report = {
        'diagnostic_only': True,
        'figure': str(figure_id if figure_id is not None else getattr(figure, 'number', 'unnumbered')),
        'coordinate_system': 'display pixels; origin bottom-left; current figure dpi',
        'dpi': float(figure.dpi),
        'warnings': [],
        'exclusions': {'tick_labels': True, 'legend_handles': True,
                       'artist_ids': []},
        'limitations': ['text bbox includes glyph whitespace; hits require visual review',
                        'current-DPI raster ink intersection, not vector geometry proof',
                        'images, 3D, custom path effects and filters require visual review'],
    }

    def visible(artist):
        alpha = artist.get_alpha()
        if not artist.get_visible() or (alpha is not None and not np.any(np.asarray(alpha) > 0)):
            return False
        if isinstance(artist, Text) and to_rgba(artist.get_color(), alpha=alpha)[3] == 0:
            return False
        return True

    def intersect(mask, bbox):
        if not np.isfinite(bbox.extents).all():
            return 0
        x0, y0, x1, y1 = bbox.extents
        left, right = max(0, int(np.floor(x0))), min(width, int(np.ceil(x1)))
        top, bottom = max(0, height-int(np.ceil(y1))), min(height, height-int(np.floor(y0)))
        if right <= left or bottom <= top:
            return 0
        return int(np.count_nonzero(mask[top:bottom, left:right]))

    for ai, ax in enumerate(figure.axes):
        if not ax.get_visible():
            continue
        targets = []
        texts = list(ax.texts) + [ax.xaxis.label, ax.yaxis.label,
                                 ax.title, ax._left_title, ax._right_title]
        # Figure-level text may cross any axis; check once per axis's artists.
        texts += list(figure.texts)
        for text in texts:
            if visible(text) and text.get_text().strip():
                # Annotation.get_window_extent also includes its arrow. Only the
                # text rectangle is a target; the arrow is intentionally attached.
                bbox = Text.get_window_extent(text, renderer=renderer)
                targets.append(('figure_text_data_overlap', text.get_text(), bbox))
        legends = list(figure.legends)
        if ax.get_legend() is not None:
            legends.append(ax.get_legend())
        for legend in legends:
            if not visible(legend):
                continue
            label = ' | '.join(t.get_text() for t in legend.get_texts())
            # Even frameless legends reserve this whole rectangle for readability.
            targets.append(('figure_legend_data_overlap', label,
                            legend.get_window_extent(renderer)))
        for kind, artists in [('lines', ax.lines), ('collections', ax.collections),
                              ('patches', ax.patches)]:
            for index, artist in enumerate(artists):
                object_id = _identity(artist, ai, kind, index)
                if id(artist) in excluded:
                    report['exclusions']['artist_ids'].append(object_id)
                    continue
                if not visible(artist):
                    continue
                renderer.clear()
                artist.draw(renderer)
                ink = np.asarray(renderer.buffer_rgba())[:, :, 3] > 0
                for code, text, bbox in targets:
                    count = intersect(ink, bbox)
                    if count:
                        report['warnings'].append({
                            'code': code, 'figure': report['figure'], 'axis': ai,
                            'text': text,
                            'bbox_display_px': [float(v) for v in bbox.extents],
                            'object_id': object_id, 'object_type': type(artist).__name__,
                            'overlap_pixels': count,
                            'message': 'Rendered data ink intersects label/legend bbox; review visually.',
                        })
    if reference_lines is not None:
        def fully_rendered_text(text):
            if not figure.get_visible():
                return False
            for parent in figure.axes:
                if ((text is parent.xaxis.label and (not parent.axison or not parent.xaxis.get_visible()))
                        or (text is parent.yaxis.label and (not parent.axison or not parent.yaxis.get_visible()))):
                    return False
            bbox = Text.get_window_extent(text, renderer=renderer)
            if (not np.isfinite(bbox.extents).all() or bbox.width <= 0 or bbox.height <= 0
                    or bbox.x0 < 0 or bbox.y0 < 0 or bbox.x1 > width or bbox.y1 > height):
                return False
            renderer.clear()
            Text.draw(text, renderer)  # An annotation arrow cannot stand in for its text.
            ink = np.asarray(renderer.buffer_rgba())[:, :, 3] > 0
            if not np.any(ink):
                return False
            clipped = text.get_clip_on()
            if clipped:
                try:
                    text.set_clip_on(False)
                    renderer.clear()
                    Text.draw(text, renderer)
                    full = np.asarray(renderer.buffer_rgba())[:, :, 3] > 0
                finally:
                    text.set_clip_on(clipped)
                if np.any(full & ~ink):
                    return False
            return True

        context = reference_context or {}
        known_texts = list(figure.texts)
        for ax in figure.axes:
            known_texts += list(ax.texts) + [ax.xaxis.label, ax.yaxis.label,
                                           ax.title, ax._left_title, ax._right_title]
        report['reference_review'] = []
        for artist in reference_lines:
            axis = next((i for i, ax in enumerate(figure.axes)
                         if any(artist is a for a in ax.lines)), None)
            object_id = artist.get_gid() or f'reference[{len(report["reference_review"])}]'
            entry = {'object_id': object_id, 'status': 'unexplained'}
            explanation = context.get(artist)
            if axis is None or not figure.get_visible() or not visible(artist) or not figure.axes[axis].get_visible():
                entry['status'] = 'not_visible_in_figure'
            elif (isinstance(explanation, Text)
                  and any(explanation is t for t in known_texts)
                  and explanation.get_figure() is figure
                  and visible(explanation) and explanation.get_text().strip()
                  and (explanation.axes is None or explanation.axes.get_visible())):
                if fully_rendered_text(explanation):
                    entry.update(status='visible_text_bound', text=explanation.get_text())
            elif (isinstance(explanation, dict)
                  and isinstance(explanation.get('location'), str)
                  and explanation['location'].strip()
                  and isinstance(explanation.get('text'), str)
                  and explanation['text'].strip()):
                entry.update(status='caller_attested_context', text=explanation['text'], location=explanation['location'])
            if entry['status'] == 'unexplained':
                legends = list(figure.legends) + [a.get_legend() for a in figure.axes
                                                   if a.get_visible() and a.get_legend() is not None]
                if any(visible(lg) and any(visible(t) and t.get_text().strip()
                       and t.get_text() == artist.get_label() for t in lg.get_texts())
                       for lg in legends):
                    entry['status'] = 'legend_binding_unverified'
                    report['warnings'].append({
                        'code': 'figure_reference_binding_unverified', 'figure': report['figure'],
                        'axis': axis, 'object_id': object_id,
                        'message': 'Visible legend has a matching label; original handle binding requires reader or caller confirmation, not proof of a missing explanation.'})
            report['reference_review'].append(entry)
            if entry['status'] == 'unexplained':
                report['warnings'].append({
                    'code': 'figure_reference_unexplained', 'figure': report['figure'],
                    'axis': axis, 'object_id': object_id,
                    'message': 'Declared reference lacks a bound visible explanation; inspect nearby caption/prose before changing the figure.'})
        report['limitations'].append('reference roles and nearby prose are caller supplied; text binding does not verify scientific meaning; legend proxies alone do not establish original handle identity')
    return report
