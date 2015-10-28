
import numpy
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
from pandas.core.frame import DataFrame
import pandas
from matplotlib.pyplot import colorbar, hist2d, sci
from scipy.stats.morestats import probplot
from itertools import cycle
from numpy.core.defchararray import decode
plt.style.use('ggplot')


def _get_mplot_axes(axes, fhand, figsize=None, plot_type=111):
    if axes is not None:
        return axes, None
    if fhand is None:
        fig = plt.figure(figsize=figsize)
    else:
        fig = Figure(figsize=figsize)

    canvas = FigureCanvas(fig)
    axes = fig.add_subplot(plot_type)
    return axes, canvas


def _print_figure(canvas, fhand, no_interactive_win):
    if fhand is None:
        if not no_interactive_win:
            plt.show()
        return
    canvas.print_figure(fhand)


def plot_histogram(mat, bins=20, range_=None, fhand=None, axes=None,
                   no_interactive_win=False, color=None, label=None,
                   canvas=None, mpl_params={}, figsize=None):
    print_figure = False
    if axes is None:
        print_figure = True
    axes, canvas = _get_mplot_axes(axes, fhand, figsize=figsize)
    result = axes.hist(mat, bins=bins, range=range_, color=color, label=label)
    if label is not None:
        axes.legend()
    for function_name, params in mpl_params.items():
        function = getattr(axes, function_name)
        function(*params['args'], **params['kwargs'])
    if print_figure:
        _print_figure(canvas, fhand, no_interactive_win=no_interactive_win)
    return result


def _calc_boxplot_stats(distribs, whis=1.5, show_fliers=False):
    cum_distribs = numpy.cumsum(distribs, axis=1)
    cum_distribs_norm = cum_distribs / cum_distribs[:, -1][:, None]
    series_stats = []
    for distrib, cum_distrib, cum_distrib_norm in zip(distribs, cum_distribs,
                                                      cum_distribs_norm):
        quartiles = [0.05, 0.25, 0.5, 0.75, 0.95]
        quartiles = [numpy.searchsorted(cum_distrib_norm, q) + 1 for q in quartiles]
        stats = {'q1': quartiles[1], 'med': quartiles[2], 'q3': quartiles[3]}
        stats['iqr'] = stats['q3'] - stats['q1']
        stats['mean'] = numpy.sum(numpy.array(range(0, distrib.shape[0])) * distrib)
        stats['mean'] = stats['mean'] / cum_distrib[-1]
        stats['whishi'] = quartiles[4]
        stats['whislo'] = quartiles[0]
        stats['cihi'] = stats['med']
        stats['cihi'] += 1.57 * stats['iqr'] / numpy.sqrt(cum_distrib[-1])
        stats['cilo'] = stats['med']
        stats['cilo'] -= 1.57 * stats['iqr'] / numpy.sqrt(cum_distrib[-1])
        stats['fliers'] = numpy.array([])
        if show_fliers:
            fliers_indices = list(range(0, int(stats['whislo'])))
            fliers_indices += list(range(int(stats['whishi']),
                                         distrib.shape[0]))
            stats['fliers'] = numpy.repeat(numpy.arange(len(fliers_indices)),
                                           fliers_indices)
        series_stats.append(stats)
    return series_stats


def plot_boxplot(mat, by_row=True, make_bins=False, fhand=None, axes=None,
                 no_interactive_win=False, figsize=None, show_fliers=False,
                 mpl_params={}):
    axes, canvas = _get_mplot_axes(axes, fhand, figsize=figsize)
    if make_bins:
        if by_row:
            mat = mat.transpose()
        result = axes.boxplot(mat)
    else:
        if not by_row:
            mat = mat.transpose()
        bxp_stats = _calc_boxplot_stats(mat)
        result = axes.bxp(bxp_stats)
    for function_name, params in mpl_params.items():
        function = getattr(axes, function_name)
        function(*params['args'], **params['kwargs'])
    _print_figure(canvas, fhand, no_interactive_win=no_interactive_win)
    return result


def plot_barplot(x, height, width=0.8, fhand=None, axes=None,
                 no_interactive_win=False, figsize=None,
                 mpl_params={}, **kwargs):
    print_figure = False
    if axes is None:
        print_figure = True
    axes, canvas = _get_mplot_axes(axes, fhand, figsize=figsize)
    result = axes.bar(x, height, width=width, **kwargs)
    for function_name, params in mpl_params.items():
        function = getattr(axes, function_name)
        function(*params['args'], **params['kwargs'])
    if print_figure:
        _print_figure(canvas, fhand, no_interactive_win=no_interactive_win)
    return result


def plot_pandas_barplot(matrix, columns, fpath=None, stacked=True,
                        mpl_params={}, axes=None, color=None):
    df = DataFrame(matrix, columns=columns)
    axes = df.plot(kind='bar', stacked=stacked, figsize=(70, 10),
                   axes=axes, color=color)
    for function_name, params in mpl_params.items():
        function = getattr(axes, function_name)
        function(*params['args'], **params['kwargs'])
    if fpath is not None:
        figure = axes.get_figure()
        figure.savefig(fpath)
    return axes


def plot_hexabinplot(matrix, columns, fpath=None, axes=None,
                     mpl_params={}):
    y = []
    for i in range(matrix.shape[1]):
            y.extend([i]*matrix.shape[0])
    x = list(range(0, matrix.shape[0]))*matrix.shape[1]
    z = matrix.reshape((matrix.shape[0]*matrix.shape[1],))
    df = DataFrame(numpy.array([x, y, z]).transpose(), columns=['x', 'y', 'z'])
    numpy.set_printoptions(threshold=numpy.nan)
    axes = df.plot(kind='hexbin', x='x', y='y', C='z', axes=axes)
    for function_name, params in mpl_params.items():
        function = getattr(axes, function_name)
        function(*params['args'], **params['kwargs'])
    if fpath is not None:
        figure = axes.get_figure()
        figure.savefig(fpath)
    return axes


def plot_hist(hist, bins):
    width = 0.7 * (bins[1] - bins[0])
    center = (bins[:-1] + bins[1:]) / 2
    plt.bar(center, hist, align='center', width=width)
    plt.show()


class AxesMod():
    def __init__(self, axes):
        self.axes = axes

    def hist2d(self, matrix):
        y = numpy.arange(matrix.shape[1])
        x = numpy.arange(matrix.shape[0])
        pc = self.axes.pcolorfast(x, y, matrix)
        self.axes.set_xlim(x[0], x[-1])
        self.axes.set_ylim(y[0], y[-1])
        return matrix, x, y, pc


def plot_hist2d(matrix, fhand=None, axes=None, fig=None,
                no_interactive_win=False, figsize=None,
                mpl_params={}, colorbar_label='', **kwargs):
    print_figure = False
    if axes is None:
        print_figure = True
        fig = Figure(figsize=figsize)
        canvas = FigureCanvas(fig)
        axes = fig.add_subplot(111)
    axesmod = AxesMod(axes)
    result = axesmod.hist2d(matrix)
    fig.colorbar(result[3], ax=axes, label=colorbar_label)
    for function_name, params in mpl_params.items():
        function = getattr(axes, function_name)
        function(*params['args'], **params['kwargs'])
    if print_figure:
        _print_figure(canvas, fhand, no_interactive_win=no_interactive_win)
    return result


def qqplot(x, distrib, distrib_params, axes=None, mpl_params={},
           no_interactive_win=False, figsize=None, fhand=None):
    print_figure = False
    if axes is None:
        print_figure = True
        axes, canvas = _get_mplot_axes(axes, fhand, figsize=figsize)
    result = probplot(x, dist=distrib, sparams=distrib_params, plot=axes)
    for function_name, params in mpl_params.items():
        function = getattr(axes, function_name)
        function(*params['args'], **params['kwargs'])
    if print_figure:
        _print_figure(canvas, fhand, no_interactive_win=no_interactive_win)
    return result


def manhattan_plot(chrom, pos, values, axes=None, mpl_params={},
           no_interactive_win=False, figsize=None, fhand=None,
           colors='bk', yfunc=lambda x:x, ylim=0, yline=None,
           remove_nans=True, show_chroms=True):
    if remove_nans:
        mask = numpy.logical_not(numpy.isnan(values))
        chrom = chrom[mask]
        pos = pos[mask]
        values = values[mask]
    
    print_figure = False
    if axes is None:
        print_figure = True
        axes, canvas = _get_mplot_axes(axes, fhand, figsize=figsize)
    
    x = numpy.array([])
    y = numpy.array([])
    col = numpy.array([])
    chrom_names = numpy.unique(chrom)
    last_pos = 0
    colors = cycle(colors)
    xticks = []
    for chrom_name, color in zip(chrom_names, colors):
        mask = chrom == chrom_name
        chrom_pos = pos[mask]
        col = numpy.append(col, numpy.repeat(color, chrom_pos.shape[0]))
        xs = chrom_pos + last_pos
        x = numpy.append(x, xs)
        xticks.append((xs[0] + xs[-1]) / 2)
        y = numpy.append(y, yfunc(values[mask]))
        last_pos = xs[-1]
    result = axes.scatter(x, y, c=col, alpha=0.8, edgecolors='none')
    axes.set_xticks(xticks)
    if show_chroms:
        axes.set_xticklabels(decode(chrom_names), rotation=-90, size='small')
    else:
        axes.set_xticklabels([''])
    axes.set_xlim(0, x[-1])
    axes.set_ylim(ylim)
    if yline is not None:
        axes.axhline(y=yline, color='0.5', linewidth=2)
    for function_name, params in mpl_params.items():
        function = getattr(axes, function_name)
        function(*params['args'], **params['kwargs'])
    if print_figure:
        _print_figure(canvas, fhand, no_interactive_win=no_interactive_win)
    return result
