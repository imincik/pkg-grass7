"""
Raster3d related functions to be used in Python scripts.

Usage:

::

    from grass.script import raster3d as grass
    grass.raster3d_info(map)


(C) 2008-2009 by the GRASS Development Team
This program is free software under the GNU General Public
License (>=v2). Read the file COPYING that comes with GRASS
for details.

.. sectionauthor:: Glynn Clements
.. sectionauthor:: Martin Landa <landa.martin gmail.com>
.. sectionauthor:: Soeren Gebbert <soeren.gebbert gmail.com>
"""

import string

from core import *
from utils import float_or_dms, parse_key_val
from grass.exceptions import CalledModuleError


def raster3d_info(map):
    """Return information about a raster3d map (interface to `r3.info`).
    Example:

    >>> mapcalc3d('volume = row() + col() + depth()')
    >>> raster3d_info('volume') # doctest: +ELLIPSIS
    {'vertical_units': '"units"', 'tbres': 1.0, ... 'south': 185000.0}
    >>> run_command('g.remove', flags='f', type='raster_3d', name='volume')
    0

    :param str map: map name

    :return: parsed raster3d info
    """

    def float_or_null(s):
        if s == 'NULL':
            return None
        else:
            return float(s)

    s = read_command('r3.info', flags='rg', map=map)
    kv = parse_key_val(s)
    for k in ['min', 'max']:
        kv[k] = float_or_null(kv[k])
    for k in ['north', 'south', 'east', 'west', 'top', 'bottom']:
        kv[k] = float(kv[k])
    for k in ['nsres', 'ewres', 'tbres']:
        kv[k] = float_or_dms(kv[k])
    for k in ['rows', 'cols', 'depths']:
        kv[k] = int(kv[k])
    for k in ['tilenumx', 'tilenumy', 'tilenumz']:
        kv[k] = int(kv[k])
    for k in ['tiledimx', 'tiledimy', 'tiledimz']:
        kv[k] = int(kv[k])
    return kv


def mapcalc3d(exp, quiet=False, verbose=False, overwrite=False, **kwargs):
    """Interface to r3.mapcalc.

    :param str exp: expression
    :param bool quiet: True to run quietly (<tt>--q</tt>)
    :param bool verbose: True to run verbosely (<tt>--v</tt>)
    :param bool overwrite: True to enable overwriting the output (<tt>--o</tt>)
    :param kwargs:
    """
    t = string.Template(exp)
    e = t.substitute(**kwargs)

    try:
        run_command('r3.mapcalc', expression=e,
                    quiet=quiet,
                    verbose=verbose,
                    overwrite=overwrite)
    except CalledModuleError:
        fatal(_("An error occurred while running r3.mapcalc"))
