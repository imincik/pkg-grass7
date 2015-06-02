# -*- coding: utf-8 -*-
"""
Created on Fri May 25 12:57:10 2012

@author: Pietro Zambelli
"""
from __future__ import (nested_scopes, generators, division, absolute_import,
                        with_statement, print_function, unicode_literals)
import ctypes
import grass.lib.gis as libgis
import grass.script as grass

from grass.pygrass.errors import GrassError
from grass.pygrass.shell.conversion import dict2html


class Region(object):
    """This class is design to easily access and modify GRASS computational
    region. ::

        >>> default = Region(default=True)
        >>> current_original = Region()
        >>> current = Region()
        >>> current.align('elevation')
        >>> default == current
        True
        >>> current.cols
        1500
        >>> current.ewres
        10.0
        >>> current.cols = 3000
        >>> current.ewres
        5.0
        >>> current.ewres = 20.0
        >>> current.cols
        750
        >>> current.set_current()
        >>> default == current
        False
        >>> current.get_default()
        >>> default = Region(default=True)
        >>> default == current
        True
        >>> current_original.set_current()

    ..
    """
    def __init__(self, default=False):
        self.c_region = ctypes.pointer(libgis.Cell_head())
        if default:
            self.get_default()
        else:
            self.get_current()

    def _set_param(self, key, value):
        grass.run_command('g.region', **{key: value})

    #----------LIMITS----------
    def _get_n(self):
        """Private function to obtain north value"""
        return self.c_region.contents.north

    def _set_n(self, value):
        """Private function to set north value"""
        self.c_region.contents.north = value

    north = property(fget=_get_n, fset=_set_n,
                     doc="Set and obtain north coordinate")

    def _get_s(self):
        """Private function to obtain south value"""
        return self.c_region.contents.south

    def _set_s(self, value):
        """Private function to set south value"""
        self.c_region.contents.south = value

    south = property(fget=_get_s, fset=_set_s,
                     doc="Set and obtain south coordinate")

    def _get_e(self):
        """Private function to obtain east value"""
        return self.c_region.contents.east

    def _set_e(self, value):
        """Private function to set east value"""
        self.c_region.contents.east = value

    east = property(fget=_get_e, fset=_set_e,
                    doc="Set and obtain east coordinate")

    def _get_w(self):
        """Private function to obtain west value"""
        return self.c_region.contents.west

    def _set_w(self, value):
        """Private function to set west value"""
        self.c_region.contents.west = value

    west = property(fget=_get_w, fset=_set_w,
                    doc="Set and obtain west coordinate")

    def _get_t(self):
        """Private function to obtain top value"""
        return self.c_region.contents.top

    def _set_t(self, value):
        """Private function to set top value"""
        self.c_region.contents.top = value

    top = property(fget=_get_t, fset=_set_t,
                   doc="Set and obtain top value")

    def _get_b(self):
        """Private function to obtain bottom value"""
        return self.c_region.contents.bottom

    def _set_b(self, value):
        """Private function to set bottom value"""
        self.c_region.contents.bottom = value

    bottom = property(fget=_get_b, fset=_set_b,
                      doc="Set and obtain bottom value")

    #----------RESOLUTION----------
    def _get_rows(self):
        """Private function to obtain rows value"""
        return self.c_region.contents.rows

    def _set_rows(self, value):
        """Private function to set rows value"""
        self.c_region.contents.rows = value
        self.adjust(rows=True)

    rows = property(fget=_get_rows, fset=_set_rows,
                    doc="Set and obtain number of rows")

    def _get_cols(self):
        """Private function to obtain columns value"""
        return self.c_region.contents.cols

    def _set_cols(self, value):
        """Private function to set columns value"""
        self.c_region.contents.cols = value
        self.adjust(cols=True)

    cols = property(fget=_get_cols, fset=_set_cols,
                    doc="Set and obtain number of columns")

    def _get_nsres(self):
        """Private function to obtain north-south value"""
        return self.c_region.contents.ns_res

    def _set_nsres(self, value):
        """Private function to obtain north-south value"""
        self.c_region.contents.ns_res = value
        self.adjust()

    nsres = property(fget=_get_nsres, fset=_set_nsres,
                     doc="Set and obtain north-south resolution value")

    def _get_ewres(self):
        """Private function to obtain east-west value"""
        return self.c_region.contents.ew_res

    def _set_ewres(self, value):
        """Private function to set east-west value"""
        self.c_region.contents.ew_res = value
        self.adjust()

    ewres = property(fget=_get_ewres, fset=_set_ewres,
                     doc="Set and obtain east-west resolution value")

    def _get_tbres(self):
        """Private function to obtain top-botton 3D value"""
        return self.c_region.contents.tb_res

    def _set_tbres(self, value):
        """Private function to set top-bottom 3D value"""
        self.c_region.contents.tb_res = value
        self.adjust()

    tbres = property(fget=_get_tbres, fset=_set_tbres,
                     doc="Set and obtain top-bottom 3D value")

    @property
    def zone(self):
        """Return the zone of projection

        >>> reg = Region()
        >>> reg.zone
        0
        """
        return self.c_region.contents.zone

    @property
    def proj(self):
        """Return a code for projection

        >>> reg = Region()
        >>> reg.proj
        99
        """
        return self.c_region.contents.proj

    @property
    def cells(self):
        """Return the number of cells"""
        return self.rows * self.cols

    #----------MAGIC METHODS----------
    def __repr__(self):
        rg = 'Region(north=%g, south=%g, east=%g, west=%g, nsres=%g, ewres=%g)'
        return rg % (self.north, self.south, self.east, self.west,
                     self.nsres, self.ewres)

    def _repr_html_(self):
        return dict2html(dict(self.items()), keys=self.keys(),
                         border='1', kdec='b')

    def __unicode__(self):
        return grass.pipe_command("g.region", flags="pu").communicate()[0]

    def __str__(self):
        return self.__unicode__()

    def __eq__(self, reg):
        """Compare two region.

        >>> r0 = Region()
        >>> r1 = Region()
        >>> r2 = Region()
        >>> r2.nsres = 5
        >>> r0 == r1
        True
        >>> r1 == r2
        False
        """
        attrs = ['north', 'south', 'west', 'east', 'top', 'bottom',
                 'nsres', 'ewres', 'tbres']
        for attr in attrs:
            if getattr(self, attr) != getattr(reg, attr):
                return False
        return True

    def __ne__(self, other):
        return not self == other

    # Restore Python 2 hashing beaviour on Python 3
    __hash__ = object.__hash__

    def keys(self):
        """Return a list of valid keys. ::

            >>> reg = Region()
            >>> reg.keys()                               # doctest: +ELLIPSIS
            [u'proj', u'zone', ..., u'cols', u'cells']

        ..
        """
        return ['proj', 'zone', 'north', 'south', 'west', 'east',
                'top', 'bottom', 'nsres', 'ewres', 'tbres', 'rows',
                'cols', 'cells']

    def items(self):
        """Return a list of tuple with key and value. ::

            >>> reg = Region()
            >>> reg.items()                              # doctest: +ELLIPSIS
            [(u'proj', 99), ..., (u'cells', 2025000)]

        ..
        """
        return [(k, self.__getattribute__(k)) for k in self.keys()]

    #----------METHODS----------
    def zoom(self, raster_name):
        """Shrink region until it meets non-NULL data from this raster map

        :param raster_name: the name of raster
        :type raster_name: str
        """
        self._set_param('zoom', str(raster_name))
        self.get_current()

    def align(self, raster_name):
        """Adjust region cells to cleanly align with this raster map

        :param raster_name: the name of raster
        :type raster_name: str
        """
        self._set_param('align', str(raster_name))
        self.get_current()

    def adjust(self, rows=False, cols=False):
        """Adjust rows and cols number according with the nsres and ewres
        resolutions. If rows or cols parameters are True, the adjust method
        update nsres and ewres according with the rows and cols numbers.
        """
        libgis.G_adjust_Cell_head(self.c_region, bool(rows), bool(cols))

    def vect(self, vector_name):
        """Adjust bounding box of region using a vector

        :param vector_name: the name of vector
        :type vector_name: str

        ::

            >>> reg = Region()
            >>> reg.vect('census')
            >>> reg.get_bbox()
            Bbox(230963.640878, 212125.562878, 645837.437393, 628769.374393)
            >>> reg.get_default()

        ..
        """
        from grass.pygrass.vector import VectorTopo
        with VectorTopo(vector_name, mode='r') as vect:
            bbox = vect.bbox()
            self.set_bbox(bbox)

    def get_current(self):
        """Set the current GRASS region to the Region object"""
        libgis.G_get_set_window(self.c_region)

    def set_current(self):
        """Set the Region object to the current GRASS region"""
        libgis.G_set_window(self.c_region)

    def get_default(self):
        """Set the default GRASS region to the Region object"""
        libgis.G_get_window(self.c_region)

    def set_default(self):
        """Set the Region object to the default GRASS region.
        It works only in PERMANENT mapset"""
        from grass.pygrass.gis import Mapset
        mapset = Mapset()
        if mapset.name != 'PERMANENT':
            raise GrassError("ERROR: Unable to change default region. The " \
                             "current mapset is not <PERMANENT>.")
        self.adjust()
        if libgis.G_put_window(self.c_region) < 0:
            raise GrassError("Cannot change region (DEFAUL_WIND file).")

    def get_bbox(self):
        """Return a Bbox object with the extension of the region. ::

            >>> reg = Region()
            >>> reg.get_bbox()
            Bbox(228500.0, 215000.0, 645000.0, 630000.0)

        ..
        """
        from grass.pygrass.vector.basic import Bbox
        return Bbox(north=self.north, south=self.south,
                    east=self.east, west=self.west,
                    top=self.top, bottom=self.bottom)

    def set_bbox(self, bbox):
        """Set region extent from Bbox

        :param bbox: a Bbox object to set the extent
        :type bbox: Bbox object

        ::

            >>> from grass.pygrass.vector.basic import Bbox
            >>> b = Bbox(230963.640878, 212125.562878, 645837.437393, 628769.374393)
            >>> reg = Region()
            >>> reg.set_bbox(b)
            >>> reg.get_bbox()
            Bbox(230963.640878, 212125.562878, 645837.437393, 628769.374393)
            >>> reg.get_current()

        ..
        """
        self.north = bbox.north
        self.south = bbox.south
        self.east = bbox.east
        self.west = bbox.west
