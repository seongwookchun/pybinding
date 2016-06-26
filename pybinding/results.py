"""Processing and presentation of computed data

Result objects hold computed data and offer postprocessing and plotting functions
which are specifically adapted to the nature of the stored data.
"""
from copy import copy, deepcopy

import numpy as np
import matplotlib.pyplot as plt

from . import pltutils
from .utils import with_defaults, x_pi
from .system import (Positions, plot_sites, plot_hoppings, plot_periodic_boundaries,
                     structure_plot_properties)
from .support.pickle import pickleable

__all__ = ['Bands', 'DOS', 'Eigenvalues', 'LDOS', 'NDSweep', 'SpatialMap', 'StructureMap',
           'Sweep', 'make_path']


class Path(np.ndarray):
    """An ndarray which represents a path connecting certain points

    Attributes
    ----------
    point_indices : List[int]
        Indices of the significant points along the path. Minimum 2: start and end.
    """
    def __new__(cls, array, point_indices):
        obj = np.asarray(array).view(cls)
        assert len(point_indices) >= 2
        obj.point_indices = point_indices
        return obj

    def __array_finalize__(self, obj):
        if obj is None:
            return
        default_indices = [0, obj.shape[0] - 1] if len(obj.shape) >= 1 else []
        self.point_indices = getattr(obj, 'point_indices', default_indices)

    @property
    def points(self):
        """Significant points along the path, including start and end"""
        return self[self.point_indices]

    @property
    def is_simple(self):
        """Is it just a simple path between two points?"""
        return len(self.point_indices) == 2

    def as_1d(self):
        """Return a 1D representation of the path -- useful for plotting

        For simple paths (2 points) the closest 1D path with real positions is returned.
        Otherwise, an `np.arange(size)` is returned, where `size` matches the path. This doesn't
        have any real meaning, but it's something that can be used as the x-axis in a line plot.

        Examples
        --------
        >>> np.allclose(make_path(-2, 1, step=1).as_1d().T, [-2, -1, 0, 1])
        True
        >>> np.allclose(make_path([0, -2], [0, 1], step=1).as_1d().T, [-2, -1, 0, 1])
        True
        >>> np.allclose(make_path(1, -1, 4, step=1).as_1d().T, [0, 1, 2, 3, 4, 5, 6, 7])
        True
        """
        if self.is_simple:
            if len(self.shape) == 1:
                return self
            else:  # return the first axis with non-zero length
                return self[:, np.flatnonzero(np.diff(self.points, axis=0))[0]]
        else:
            return np.arange(self.shape[0])

    def plot(self, point_labels=None, **kwargs):
        """Quiver plot of the path

        Parameters
        ----------
        point_labels : List[str]
            Labels for the :attr:`.Path.points`.
        **kwargs
            Forwarded to :func:`~matplotlib.pyplot.quiver`.
        """
        ax = plt.gca()
        ax.set_aspect('equal')

        default_color = pltutils.get_palette('Set1')[1]
        kwargs = with_defaults(kwargs, scale_units='xy', angles='xy', scale=1, zorder=2,
                               lw=1.5, color=default_color, edgecolor=default_color)

        x, y = map(np.array, zip(*self.points))
        plt.quiver(x[:-1], y[:-1], np.diff(x), np.diff(y), **kwargs)

        ax.autoscale_view()
        pltutils.add_margin(0.5)
        pltutils.despine(trim=True)

        if point_labels:
            for k_point, label in zip(self.points, point_labels):
                ha, va = pltutils.align(*(-k_point))
                pltutils.annotate_box(label, k_point * 1.05, fontsize='large',
                                      ha=ha, va=va, bbox=dict(lw=0))


def make_path(k0, k1, *ks, step=0.1):
    """Create a path which connects the given k points

    Parameters
    ----------
    k0, k1, *ks
        Points in k-space to connect.
    step : float
        Length in k-space between two samples. Smaller step -> finer detail.

    Examples
    --------
    >>> np.allclose(make_path(0, 3, -1, step=1).T, [0, 1, 2, 3, 2, 1, 0, -1])
    True
    >>> np.allclose(make_path([0, 0], [2, 3], [-1, 4], step=1.4),
    ...             [[0, 0], [1, 1.5], [2, 3], [0.5, 3.5], [-1, 4]])
    True
    """
    k_points = [np.atleast_1d(k) for k in (k0, k1) + ks]
    if not all(k.shape == k_points[0].shape for k in k_points[:1]):
        raise RuntimeError("All k-points must have the same shape")

    k_paths = []
    point_indices = [0]
    for k_start, k_end in zip(k_points[:-1], k_points[1:]):
        num_steps = int(np.linalg.norm(k_end - k_start) // step)
        # k_path.shape == num_steps, k_space_dimensions
        k_path = np.array([np.linspace(s, e, num_steps, endpoint=False)
                           for s, e in zip(k_start, k_end)]).T
        k_paths.append(k_path)
        point_indices.append(point_indices[-1] + num_steps)
    k_paths.append(k_points[-1])

    return Path(np.vstack(k_paths), point_indices)


@pickleable
class DOS:
    """Density of states as a function of energy

    Attributes
    ----------
    energy : array_like
    dos : array_like
    """
    def __init__(self, energy, dos):
        self.energy = np.atleast_1d(energy)
        self.dos = np.atleast_1d(dos)

    def plot(self, **kwargs):
        """Labeled line plot

        Parameters
        ----------
        **kwargs
            Forwarded to `plt.plot()`.
        """
        plt.plot(self.energy, self.dos, **kwargs)
        plt.xlim(self.energy.min(), self.energy.max())
        plt.ylabel('DOS')
        plt.xlabel('E (eV)')
        pltutils.despine()


@pickleable
class LDOS:
    """Local density of states as a function of energy

    Attributes
    ----------
    energy : array_like
    ldos : array_like
    """
    def __init__(self, energy, ldos):
        self.energy = np.atleast_1d(energy)
        self.ldos = np.atleast_1d(ldos)

    def plot(self, **kwargs):
        """Labeled line plot

        Parameters
        ----------
        **kwargs
            Forwarded to `plt.plot()`.
        """
        plt.plot(self.energy, self.ldos, **kwargs)
        plt.xlim(self.energy.min(), self.energy.max())
        plt.ylabel('LDOS')
        plt.xlabel('E (eV)')
        pltutils.despine()


@pickleable
class SpatialMap:
    """Represents some spatially dependent property: data mapped to site positions

    Attributes
    ----------
    data : array_like
        1D array of values which correspond to x, y, z coordinates.
    positions : Tuple[array_like, array_like, array_like]
        Lattice site positions. Named tuple with x, y, z fields, each a 1D array.
    sublattices : Optional[array_like]
        Sublattice ID for each position.
    """
    def __init__(self, data, positions, sublattices=None):
        self.data = np.atleast_1d(data)
        self.positions = Positions(*positions)  # maybe convert from tuple
        if sublattices is not None:
            self.sublattices = np.atleast_1d(sublattices)
        else:
            self.sublattices = np.zeros_like(self.data)

    @property
    def num_sites(self) -> int:
        """Total number of lattice sites"""
        return self.data.size

    @property
    def x(self) -> np.ndarray:
        """1D array of x coordinates"""
        return self.positions.x

    @property
    def y(self) -> np.ndarray:
        """1D array of y coordinates"""
        return self.positions.y

    @property
    def z(self) -> np.ndarray:
        """1D array of z coordinates"""
        return self.positions.z

    @classmethod
    def from_system(cls, data, system):
        """Alternate constructor which takes `pos` and `sub` from `system`

        Parameters
        ----------
        data : np.ndarray
        system : :class:`.System`
        """
        return cls(data, system.positions, system.sublattices)

    def save_txt(self, filename):
        with open(filename + '.dat', 'w') as file:
            file.write('# {:12}{:13}{:13}\n'.format('x(nm)', 'y(nm)', 'data'))
            for x, y, d in zip(self.x, self.y, self.data):
                file.write(("{:13.5e}" * 3 + '\n').format(x, y, d))

    def __getitem__(self, idx):
        """Same rules as numpy indexing"""
        return self.__class__(self.data[idx], (v[idx] for v in self.positions),
                              self.sublattices[idx])

    def cropped(self, **limits):
        """Return a copy which retains only the sites within the given limits

        Parameters
        ----------
        **limits
            Attribute names and corresponding limits. See example.

        Returns
        -------
        StructureMap

        Examples
        --------
        Leave only the data where -10 <= x < 10 and 2 <= y < 4::

            new = original.cropped(x=[-10, 10], y=[2, 4])
        """
        idx = np.ones(self.num_sites, dtype=np.bool)
        for name, limit in limits.items():
            v = getattr(self, name)
            idx = np.logical_and(idx, v >= limit[0])
            idx = np.logical_and(idx, v < limit[1])

        return self[idx]

    def clipped(self, v_min, v_max):
        """Clip (limit) the values in the `data` array, see :func:`~numpy.clip`"""
        return self.__class__(np.clip(self.data, v_min, v_max), self.positions, self.sublattices)

    def convolve(self, sigma=0.25):
        # TODO: slow and only works in the xy-plane
        x, y, _ = self.positions
        r = np.sqrt(x**2 + y**2)

        data = np.empty_like(self.data)
        for i in range(len(data)):
            idx = np.abs(r - r[i]) < sigma
            data[i] = np.sum(self.data[idx] * np.exp(-0.5 * ((r[i] - r[idx]) / sigma)**2))
            data[i] /= np.sum(np.exp(-0.5 * ((r[i] - r[idx]) / sigma)**2))

        self.data = data

    @staticmethod
    def _decorate_plot():
        ax = plt.gca()
        ax.set_aspect('equal')
        ax.set_xlabel('x (nm)')
        ax.set_ylabel('y (nm)')
        pltutils.despine(trim=True)

    def plot_pcolor(self, **kwargs):
        """Color plot of the xy plane

        Parameters
        ----------
        **kwargs
            Forwarded to :func:`~matplotlib.pyplot.tripcolor`.
        """
        x, y, _ = self.positions
        kwargs = with_defaults(kwargs, shading='gouraud', rasterized=True)
        pcolor = plt.tripcolor(x, y, self.data, **kwargs)
        self._decorate_plot()
        return pcolor

    def plot_contourf(self, num_levels=50, **kwargs):
        """Filled contour plot of the xy plane

        Parameters
        ----------
        num_levels : int
            Number of contour levels.
        **kwargs
            Forwarded to :func:`~matplotlib.pyplot.tricontourf`.
        """
        levels = np.linspace(self.data.min(), self.data.max(), num=num_levels)
        x, y, _ = self.positions
        kwargs = with_defaults(kwargs, levels=levels, rasterized=True)
        contourf = plt.tricontourf(x, y, self.data, **kwargs)
        self._decorate_plot()
        return contourf

    def plot_contour(self, **kwargs):
        """Contour plot of the xy plane

        Parameters
        ----------
        **kwargs
            Forwarded to :func:`~matplotlib.pyplot.tricontour`.
        """
        x, y, _ = self.positions
        contour = plt.tricontour(x, y, self.data, **kwargs)
        self._decorate_plot()
        return contour


@pickleable
class StructureMap(SpatialMap):
    """A subclass of :class:`.SpatialMap` that also includes hoppings between sites

    Attributes
    ----------
    hoppings : :class:`~scipy.sparse.csr_matrix`
        Sparse matrix of hopping IDs. See :attr:`.System.hoppings`.
    boundaries : List[:class:`~scipy.sparse.csr_matrix`]
        Boundary hoppings. See :attr:`.System.boundaries`.
    """
    def __init__(self, data, positions, sublattices, hoppings, boundaries=()):
        super().__init__(data, positions, sublattices)
        self.hoppings = hoppings
        self.boundaries = boundaries

    @classmethod
    def from_system(cls, data, system):
        return cls(data, system.positions, system.sublattices,
                   system.hoppings.tocsr(), system.boundaries)

    @property
    def spatial_map(self) -> SpatialMap:
        """Just the :class:`SpatialMap` subset without hoppings"""
        return SpatialMap(self.data, self.positions, self.sublattices)

    @staticmethod
    def _filter_csr_matrix(csr, idx):
        """Indexing must preserve all data, even zeros"""
        m = copy(csr)  # shallow copy
        m.data = m.data.copy()
        m.data += 1  # increment by 1 to preserve zeroes when slicing
        m = m[idx][:, idx]
        m.data -= 1
        return m

    @staticmethod
    def _filter_boundary(boundary, idx):
        b = copy(boundary)
        b.hoppings = StructureMap._filter_csr_matrix(b.hoppings, idx)
        return b

    def __getitem__(self, idx):
        """Same rules as numpy indexing"""
        return self.__class__(self.data[idx], (v[idx] for v in self.positions),
                              self.sublattices[idx], self._filter_csr_matrix(self.hoppings, idx),
                              [self._filter_boundary(b, idx) for b in self.boundaries])

    def plot_structure(self, cmap='YlGnBu', site_radius=(0.03, 0.05), num_periods=1, **kwargs):
        """Plot the spatial structure with a colormap of :attr:`data` at the lattice sites

        Both the site size and color are used to display the data.

        Parameters
        ----------
        cmap : str
            Matplotlib colormap to be used for the data.
        site_radius : Tuple[float, float]
            Min and max radius of lattice sites. This range will be used to visually
            represent the magnitude of the data.
        num_periods : int
            Number of times to repeat periodic boundaries.
        **kwargs
            Additional plot arguments as specified in :func:`.structure_plot_properties`.
        """
        ax = plt.gca()
        ax.set_aspect('equal', 'datalim')
        ax.set_xlabel('x (nm)')
        ax.set_ylabel('y (nm)')

        def to_radii(data):
            if not isinstance(site_radius, (tuple, list)):
                return site_radius

            positive_data = data - data.min()
            maximum = positive_data.max()
            if not np.allclose(maximum, 0):
                delta = site_radius[1] - site_radius[0]
                return site_radius[0] + delta * positive_data / maximum
            else:
                return site_radius[1]

        props = structure_plot_properties(**kwargs)
        props['site'] = with_defaults(props['site'], radius=to_radii(self.data), cmap=cmap)
        collection = plot_sites(self.positions, self.data, **props['site'])

        hop = self.hoppings.tocoo()
        props['hopping'] = with_defaults(props['hopping'], color='#bbbbbb')
        plot_hoppings(self.positions, hop, **props['hopping'])

        props['site']['alpha'] = props['hopping']['alpha'] = 0.5
        plot_periodic_boundaries(self.positions, hop, self.boundaries, self.data,
                                 num_periods, **props)

        pltutils.despine(trim=True)
        pltutils.add_margin()

        plt.sci(collection)
        return collection


@pickleable
class Eigenvalues:
    """Hamiltonian eigenvalues with optional probability map

    Attributes
    ----------
    values : np.ndarray
    probability : np.ndarray
    """
    def __init__(self, eigenvalues, probability=None):
        self.values = np.atleast_1d(eigenvalues)
        self.probability = np.atleast_1d(probability)

    @property
    def indices(self):
        return np.arange(0, self.values.size)

    def _decorate_plot(self, mark_degenerate, number_states):
        """Common elements for the two eigenvalue plots"""
        if mark_degenerate:
            # draw lines between degenerate states
            from .solver import Solver
            from matplotlib.collections import LineCollection
            pairs = ((s[0], s[-1]) for s in Solver.find_degenerate_states(self.values))
            lines = [[(i, self.values[i]) for i in pair] for pair in pairs]
            plt.gca().add_collection(LineCollection(lines, color='black', alpha=0.5))

        if number_states:
            # draw a number next to each state
            for index, energy in enumerate(self.values):
                pltutils.annotate_box(index, (index, energy), fontsize='x-small',
                                      xytext=(0, -10), textcoords='offset points')

        plt.xlabel('state')
        plt.ylabel('E (eV)')
        plt.xlim(-1, len(self.values))
        pltutils.despine(trim=True)

    def plot(self, mark_degenerate=True, show_indices=False, **kwargs):
        """Standard eigenvalues scatter plot

        Parameters
        ----------
        mark_degenerate : bool
            Plot a line which connects degenerate states.
        show_indices : bool
            Plot index number next to all states.
        **kwargs
            Forwarded to plt.scatter().
        """
        plt.scatter(self.indices, self.values, **with_defaults(kwargs, c='#377ec8', s=15, lw=0.1))
        self._decorate_plot(mark_degenerate, show_indices)

    def plot_heatmap(self, size=(7, 77), mark_degenerate=True, show_indices=False, **kwargs):
        """Eigenvalues scatter plot with a heatmap indicating probability density

        Parameters
        ----------
        size : Tuple[int, int]
            Min and max scatter dot size.
        mark_degenerate : bool
            Plot a line which connects degenerate states.
        show_indices : bool
            Plot index number next to all states.
        **kwargs
            Forwarded to plt.scatter().
        """
        if not np.any(self.probability):
            return self.plot(mark_degenerate, show_indices, **kwargs)

        # higher probability states should be drawn above lower ones
        idx = np.argsort(self.probability)
        indices, energy, probability = (v[idx] for v in
                                        (self.indices, self.values, self.probability))

        scatter_point_sizes = size[0] + size[1] * probability / probability.max()
        plt.scatter(indices, energy, **with_defaults(kwargs, cmap='YlOrRd', lw=0.2, alpha=0.85,
                                                     c=probability, s=scatter_point_sizes))

        self._decorate_plot(mark_degenerate, show_indices)
        return self.probability.max()


@pickleable
class Bands:
    """Band structure along a path in k-space

    Attributes
    ----------
    k_path : :class:`Path`
        The path in reciprocal space along which the bands were calculated.
        E.g. constructed using :func:`make_path`.
    energy : array_like
        Energy values for the bands along the path in k-space.
    """
    def __init__(self, k_path, energy):
        self.k_path = np.atleast_1d(k_path).view(Path)
        self.energy = energy

    @staticmethod
    def _point_names(k_points):
        names = []
        for k_point in k_points:
            k_point = np.atleast_1d(k_point)
            values = map(x_pi, k_point)
            fmt = "[{}]" if len(k_point) > 1 else "{}"
            names.append(fmt.format(', '.join(values)))
        return names

    def plot(self, point_labels=None, **kwargs):
        """Line plot of the band structure

        Parameters
        ----------
        point_labels : List[str]
            Labels for the `k_points`.
        **kwargs
            Forwarded to `plt.plot()`.
        """
        default_color = pltutils.get_palette('Set1')[1]
        k_space = self.k_path.as_1d()
        plt.plot(k_space, self.energy, **with_defaults(kwargs, color=default_color))

        plt.xlim(k_space.min(), k_space.max())
        plt.xlabel('k-space')
        plt.ylabel('E (eV)')
        pltutils.add_margin()
        pltutils.despine(trim=True)

        point_labels = point_labels or self._point_names(self.k_path.points)
        plt.xticks(k_space[self.k_path.point_indices], point_labels)

        # Draw vertical lines at significant points. Because of the `transLimits.transform`,
        # this must be the done last, after all other plot elements are positioned.
        for idx in self.k_path.point_indices:
            ymax = plt.gca().transLimits.transform([0, max(self.energy[idx])])[1]
            plt.axvline(k_space[idx], ymax=ymax, color='0.4', ls=':', zorder=-1)

    def plot_kpath(self, point_labels=None, **kwargs):
        """Quiver plot of the k-path along which the bands were computed

        Combine with :meth:`.Lattice.plot_brillouin_zone` to see the path in context.

        Parameters
        ----------
        point_labels : List[str]
            Labels for the k-points.
        **kwargs
            Forwarded to :func:`~matplotlib.pyplot.quiver`.
        """
        self.k_path.plot(point_labels, **kwargs)


@pickleable
class Sweep:
    """2D parameter sweep with `x` and `y` 1D array parameters and `data` 2D array result

    Attributes
    ----------
    x : array_like
        1D array with x-axis values -- usually the primary parameter being swept.
    y : array_like
        1D array with y-axis values -- usually the secondary parameter.
    data : array_like
        2D array with `shape == (x.size, y.size)` containing the main result data.
    labels : dict
        Plot labels: 'title', 'x', 'y' and 'data'.
    tags : dict
        Any additional user defined variables.
    """
    def __init__(self, x, y, data, labels=None, tags=None):
        self.x = np.atleast_1d(x)
        self.y = np.atleast_1d(y)
        self.data = np.atleast_2d(data)

        self.labels = with_defaults(labels, title="", x="x", y="y", data="data")
        self.tags = tags

    def copy(self) -> 'Sweep':
        return deepcopy(self)

    @property
    def plain_labels(self):
        """Labels dict with latex symbols stripped out."""
        trans = str.maketrans('', '', '$\\')
        return {k: v.translate(trans) for k, v in self.labels.items()}

    def xy_grids(self):
        """Expand x and y into 2D arrays matching data."""
        xgrid = np.column_stack([self.x] * self.y.size)
        ygrid = np.row_stack([self.y] * self.x.size)
        return xgrid, ygrid

    def save_txt(self, filename):
        """Save text file with 3 columns: x, y, data.

        Parameters
        ----------
        filename : str
        """
        with open(filename, 'w') as file:
            file.write("#{x:>11} {y:>12} {data:>12}\n".format(**self.plain_labels))

            xgrid, ygrid = self.xy_grids()
            for row in zip(xgrid.flat, ygrid.flat, self.data.flat):
                values = ("{:12.5e}".format(v) for v in row)
                file.write(" ".join(values) + "\n")

    def filter(self, idx_x=None, idx_y=None):
        idx_x = np.ones(self.x.size, dtype=bool) if idx_x is None else idx_x
        idx_y = np.ones(self.y.size, dtype=bool) if idx_y is None else idx_y

        self.x = self.x[idx_x]
        self.y = self.y[idx_y]
        self.data = self.data[np.ix_(idx_x, idx_y)]

    def crop(self, x=None, y=None):
        """Crop data to limits in the x and/or y axes.

        A call with x=(-1, 2) will leave data only where -1 < x < 2.

        Parameters
        ----------
        x, y : Tuple[float, float]
            Min and max data limit.
        """
        xlim, ylim = x, y
        idx_x = np.logical_and(self.x >= xlim[0], self.x <= xlim[1]) if xlim else None
        idx_y = np.logical_and(self.y >= ylim[0], self.y <= ylim[1]) if ylim else None
        self.filter(idx_x, idx_y)

    def mirror(self, axis='x'):
        """Mirror data in the specified axis. Only makes sense if the axis starts at 0.

        Parameters
        ----------
        axis : 'x' or 'y'
        """
        if axis == 'x':
            self.x = np.concatenate((-self.x[::-1], self.x[1:]))
            self.data = np.vstack((self.data[::-1], self.data[1:]))
        elif axis == 'y':
            self.y = np.concatenate((-self.y[::-1], self.y[1:]))
            self.data = np.hstack((self.data[:, ::-1], self.data[:, 1:]))

    def interpolate(self, multiply=None, size=None, kind='linear'):
        """Interpolate data using scipy's interp1d.

        Call with multiply=2 to double the size of the x-axis and interpolate data to match.
        To interpolate in both axes pass a tuple, e.g. multiply=(4, 2).

        Parameters
        ----------
        multiply : int or tuple of int
            Number of times the size of the axes should be multiplied.
        size : int or tuple of int
            New size of the axes. Zero will leave size unchanged.
        kind
            Passed to scipy.interpolate.interp1d.
        """
        from scipy.interpolate import interp1d
        if not multiply and not size:
            return

        if multiply:
            try:
                mul_x, mul_y = multiply
            except TypeError:
                mul_x, mul_y = multiply, 1
            size_x = self.x.size * mul_x
            size_y = self.y.size * mul_y
        else:
            try:
                size_x, size_y = size
            except TypeError:
                size_x, size_y = size, 0

        if size_x > 0 and size_x != self.x.size:
            interp_x = interp1d(self.x, self.data, axis=0, kind=kind)
            self.x = np.linspace(self.x.min(), self.x.max(), size_x, dtype=self.x.dtype)
            self.data = interp_x(self.x)

        if size_y > 0 and size_y != self.y.size:
            interp_y = interp1d(self.y, self.data, kind=kind)
            self.y = np.linspace(self.y.min(), self.y.max(), size_y, dtype=self.x.dtype)
            self.data = interp_y(self.y)

    def convolve_gaussian(self, sigma, axis='x'):
        """Convolve the data with a Gaussian function.

        Parameters
        ----------
        sigma : float
            Gaussian broadening.
        axis : 'x' or 'y'
        """
        def convolve(v, data0):
            v0 = v[v.size // 2]
            gaussian = np.exp(-0.5 * ((v - v0) / sigma)**2)
            gaussian /= gaussian.sum()

            extend = 10  # TODO: rethink this
            data = np.concatenate((data0[extend::-1], data0, data0[:-extend:-1]))
            data = np.convolve(data, gaussian, 'same')
            return data[extend:-extend]

        if 'x' in axis:
            for i in range(self.y.size):
                self.data[:, i] = convolve(self.x, self.data[:, i])

        if 'y' in axis:
            for i in range(self.x.size):
                self.data[i, :] = convolve(self.y, self.data[i, :])

    def slice_x(self, x):
        """Return a slice of data nearest to x and the found values of x.

        Parameters
        ----------
        x : float
        """
        idx = np.abs(self.x - x).argmin()
        return self.data[idx, :], self.x[idx]

    def slice_y(self, y):
        """Return a slice of data nearest to y and the found values of y.

        Parameters
        ----------
        y : float
        """
        idx = np.abs(self.y - y).argmin()
        return self.data[:, idx], self.y[idx]

    def plot(self, **kwargs):
        """Plot a 2D colormap of :attr:`Sweep.data`

        Parameters
        ----------
        **kwargs
            Forwarded to :func:`matplotlib.pyplot.pcolormesh`.
        """
        mesh = plt.pcolormesh(self.x, self.y, self.data.T,
                              **with_defaults(kwargs, cmap='RdYlBu_r', rasterized=True))
        plt.xlim(self.x.min(), self.x.max())
        plt.ylim(self.y.min(), self.y.max())

        plt.title(self.labels['title'])
        plt.xlabel(self.labels['x'])
        plt.ylabel(self.labels['y'])

        plt.gca().get_xaxis().tick_bottom()
        plt.gca().get_yaxis().tick_left()

        return mesh

    def colorbar(self, **kwargs):
        """Draw a colorbar with the label of :attr:`Sweep.data`"""
        return pltutils.colorbar(**with_defaults(kwargs, label=self.labels['data']))

    def _plot_slice(self, axis, x, y, value, **kwargs):
        plt.plot(x, y, **kwargs)

        split = self.labels[axis].split(' ', 1)
        label = split[0]
        unit = '' if len(split) == 1 else split[1].strip('()')
        plt.title('{}, {} = {:.2g} {}'.format(self.labels['title'], label, value, unit))

        plt.xlim(x.min(), x.max())
        plt.xlabel(self.labels['x' if axis == 'y' else 'y'])
        plt.ylabel(self.labels['data'])
        pltutils.despine()

    def plot_slice_x(self, x, **kwargs):
        z, value = self.slice_x(x)
        self._plot_slice('x', self.y, z, value, **kwargs)

    def plot_slice_y(self, y, **kwargs):
        z, value = self.slice_y(y)
        self._plot_slice('y', self.x, z, value, **kwargs)


@pickleable
class NDSweep:
    """ND parameter sweep.

    Attributes
    ----------
    variables : tuple of array_like
        The parameters being swept.
    data : np.ndarray
        Main result array with `shape == [len(v) for v in variables]`.
    labels : dict
        Plot labels: 'title', 'x', 'y' and 'data'.
    tags : dict
        Any additional user defined variables.
    """
    def __init__(self, variables, data, labels=None, tags=None):
        self.variables = variables
        self.data = np.reshape(data, [len(v) for v in variables])

        self.labels = with_defaults(labels, title="", axes=[], data="data")
        # alias the first 3 axes to x, y, z for compatibility with Sweep labels
        for axis, label in zip('xyz', self.labels['axes']):
            self.labels[axis] = label

        self.tags = tags

    def copy(self) -> 'NDSweep':
        return deepcopy(self)
