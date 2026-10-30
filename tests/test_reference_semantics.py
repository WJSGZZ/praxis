import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.text import Text
import pytest

from scripts.figure_layout import inspect

@pytest.fixture
def scene():
    fig, ax=plt.subplots()
    line,=ax.plot([0,1],[0,1],ls='--',color='gray')
    yield fig,ax,line
    plt.close('all')

def semantic(report):
    return [w for w in report['warnings'] if w['code']=='figure_reference_unexplained']

def test_default_retains_old_report_shape(scene):
    fig,ax,line=scene
    assert 'reference_review' not in inspect(fig)
    assert inspect(fig)['diagnostic_only'] is True

def test_declared_unexplained_reference_warns(scene):
    fig,ax,line=scene
    assert len(semantic(inspect(fig,reference_lines=[line])))==1

def test_data_lines_are_not_forced_to_have_legends(scene):
    fig,ax,line=scene
    assert not semantic(inspect(fig,reference_lines=[]))

def test_visible_text_binding(scene):
    fig,ax,line=scene
    text=fig.text(.1,.01,'Dashed grey line: predicted = observed (y = x).')
    r=inspect(fig,reference_lines=[line],reference_context={line:text})
    assert not semantic(r)
    assert r['reference_review'][0]['status']=='visible_text_bound'

@pytest.mark.parametrize('kind',['hidden','empty','foreign','unattached','offcanvas','hidden_axis'])
def test_invalid_text_does_not_silence_warning(scene,kind):
    fig,ax,line=scene
    text=fig.text(.1,.01,'Identity line')
    if kind=='hidden': text.set_visible(False)
    if kind=='empty': text.set_text(' ')
    if kind=='foreign': text=plt.figure().text(.1,.1,'Identity')
    if kind=='unattached': text=Text(.1,.1,'Identity');text.set_figure(fig)
    if kind=='offcanvas': text.set_position((20,20))
    if kind=='hidden_axis':
        hidden=fig.add_axes([.5,.5,.2,.2]);text=hidden.text(.1,.1,'Identity');hidden.set_visible(False)
    assert semantic(inspect(fig,reference_lines=[line],reference_context={line:text}))

def test_body_explanation_is_attested_not_machine_certified(scene):
    fig,ax,line=scene
    r=inspect(fig,reference_lines=[line],reference_context={line:{'location':'Figure 4 caption','text':'Dashed grey line is y=x.'}})
    assert not semantic(r)
    assert r['reference_review'][0]['status']=='caller_attested_context'

@pytest.mark.parametrize('explanation',[{'text':'Identity'}, {'location':'p12'}, {'location':' ', 'text':'Identity'}, 'Identity'])
def test_unbound_body_text_warns(scene,explanation):
    fig,ax,line=scene
    assert semantic(inspect(fig,reference_lines=[line],reference_context={line:explanation}))

def test_same_name_proxy_legend_does_not_prove_handle_identity(scene):
    fig,ax,line=scene
    line.set_label('Identity line')
    ax.legend(handles=[Line2D([],[],label='Identity line')])
    r=inspect(fig,reference_lines=[line])
    assert not semantic(r)
    assert r['reference_review'][0]['status']=='legend_binding_unverified'
    assert any(w['code']=='figure_reference_binding_unverified' for w in r['warnings'])

def test_transparent_text_does_not_silence_warning(scene):
    fig,ax,line=scene
    text=fig.text(.1,.1,'Identity',alpha=0)
    assert semantic(inspect(fig,reference_lines=[line],reference_context={line:text}))

def test_geometry_remains_enabled(scene):
    fig,ax,line=scene
    text=ax.text(.5,.5,'crossing',va='center')
    r=inspect(fig,reference_lines=[line],reference_context={line:text})
    assert any(w['code']=='figure_text_data_overlap' for w in r['warnings'])


def test_axis_clipped_invisible_explanation_cannot_pass(scene):
    fig, ax, line = scene
    text = ax.text(.5, 1.12, 'Dashed line: y = x', clip_on=True)
    report = inspect(fig, reference_lines=[line], reference_context={line: text})
    assert semantic(report)
    assert text.get_clip_on() is True


def test_partially_clipped_explanation_requires_review(scene):
    fig, ax, line = scene
    text = ax.text(.99, .5, 'Dashed line: predicted equals observed', clip_on=True)
    assert semantic(inspect(fig, reference_lines=[line], reference_context={line: text}))
    assert text.get_clip_on() is True


def test_partly_off_canvas_explanation_requires_review(scene):
    fig, ax, line = scene
    text = fig.text(-.01, .05, 'Dashed line: predicted equals observed')
    assert semantic(inspect(fig, reference_lines=[line], reference_context={line: text}))


@pytest.mark.parametrize('axis_name', ['xaxis', 'yaxis'])
def test_hidden_parent_axis_cannot_make_its_label_an_explanation(scene, axis_name):
    fig, ax, line = scene
    parent = getattr(ax, axis_name)
    parent.label.set_text('Dashed line: predicted = observed')
    fig.canvas.draw()  # Keep the once-visible label's on-canvas position.
    parent.set_visible(False)
    assert semantic(inspect(fig, reference_lines=[line], reference_context={line: parent.label}))


def test_axis_off_cannot_make_hidden_axis_label_an_explanation(scene):
    fig, ax, line = scene
    ax.set_xlabel('Dashed line: predicted = observed')
    fig.canvas.draw()
    ax.set_axis_off()
    assert semantic(inspect(fig, reference_lines=[line], reference_context={line: ax.xaxis.label}))
