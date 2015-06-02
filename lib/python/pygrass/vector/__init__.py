# -*- coding: utf-8 -*-
from os.path import join, exists
import grass.lib.gis as libgis
libgis.G_gisinit('')
import grass.lib.vector as libvect

#
# import pygrass modules
#
from grass.pygrass.vector.vector_type import VTYPE
from grass.pygrass.errors import GrassError, must_be_open
from grass.pygrass.gis import Location

from grass.pygrass.vector.geometry import GEOOBJ as _GEOOBJ
from grass.pygrass.vector.geometry import read_line, read_next_line
from grass.pygrass.vector.geometry import Area as _Area
from grass.pygrass.vector.abstract import Info
from grass.pygrass.vector.basic import Bbox, Cats, Ilist


_NUMOF = {"areas": libvect.Vect_get_num_areas,
          "dblinks": libvect.Vect_get_num_dblinks,
          "faces": libvect.Vect_get_num_faces,
          "holes": libvect.Vect_get_num_holes,
          "islands": libvect.Vect_get_num_islands,
          "kernels": libvect.Vect_get_num_kernels,
          "lines": libvect.Vect_get_num_lines,
          "nodes": libvect.Vect_get_num_nodes,
          "updated_lines": libvect.Vect_get_num_updated_lines,
          "updated_nodes": libvect.Vect_get_num_updated_nodes,
          "volumes": libvect.Vect_get_num_volumes}


#=============================================
# VECTOR
#=============================================

class Vector(Info):
    """Vector class is the grass vector format without topology

        >>> from grass.pygrass.vector import Vector
        >>> cens = Vector('census')
        >>> cens.is_open()
        False
        >>> cens.mapset
        ''
        >>> cens.exist()
        True
        >>> cens.mapset
        'PERMANENT'
        >>> cens.overwrite
        False

    """
    def __init__(self, name, mapset='', *args, **kwargs):
        # Set map name and mapset
        super(Vector, self).__init__(name, mapset, *args, **kwargs)
        self._topo_level = 1
        self._class_name = 'Vector'
        self.overwrite = False

    def __repr__(self):
        if self.exist():
            return "%s(%r, %r)" % (self._class_name, self.name, self.mapset)
        else:
            return "%s(%r)" % (self._class_name, self.name)

    def __iter__(self):
        """::

            >>> cens = Vector('census')
            >>> cens.open(mode='r')
            >>> features = [feature for feature in cens]
            >>> features[:3]
            [Boundary(v_id=None), Boundary(v_id=None), Boundary(v_id=None)]
            >>> cens.close()

        ..
        """
        #return (self.read(f_id) for f_id in xrange(self.num_of_features()))
        return self

    @must_be_open
    def next(self):
        """::

            >>> cens = Vector('census')
            >>> cens.open(mode='r')
            >>> cens.next()
            Boundary(v_id=None)
            >>> cens.next()
            Boundary(v_id=None)
            >>> cens.close()

        ..
        """
        return read_next_line(self.c_mapinfo, self.table, self.writable,
                              is2D=not self.is_3D())

    @must_be_open
    def rewind(self):
        """Rewind vector map to cause reads to start at beginning."""
        if libvect.Vect_rewind(self.c_mapinfo) == -1:
            raise GrassError("Vect_rewind raise an error.")

    @must_be_open
    def write(self, geo_obj, attrs=None, set_cats=True):
        """Write geometry features and attributes.

        :param geo_obj: a geometry grass object define in
                        grass.pygrass.vector.geometry
        :type geo_obj: geometry GRASS object
        :param attrs: a list with the values that will be insert in the
                      attribute table.
        :type attrs: list
        :param set_cats: if True, the category of the geometry feature is set
                         using the default layer of the vector map and a
                         progressive category value (default), otherwise the
                         c_cats attribute of the geometry object will be used.
        :type set_cats: bool

        Open a new vector map ::

            >>> new = VectorTopo('newvect')
            >>> new.exist()
            False

        define the new columns of the attribute table ::

            >>> cols = [(u'cat',       'INTEGER PRIMARY KEY'),
            ...         (u'name',      'TEXT')]

        open the vector map in write mode

            >>> new.open('w', tab_name='newvect', tab_cols=cols)

        import a geometry feature ::

            >>> from grass.pygrass.vector.geometry import Point

        create two points ::

            >>> point0 = Point(636981.336043, 256517.602235)
            >>> point1 = Point(637209.083058, 257970.129540)

        then write the two points on the map, with ::

            >>> new.write(point0, ('pub', ))
            >>> new.write(point1, ('resturnat', ))

        commit the db changes ::

            >>> new.table.conn.commit()
            >>> new.table.execute().fetchall()
            [(1, u'pub'), (2, u'resturnat')]

        close the vector map ::

            >>> new.close()
            >>> new.exist()
            True

        then play with the map ::

            >>> new.open(mode='r')
            >>> new.read(1)
            Point(636981.336043, 256517.602235)
            >>> new.read(2)
            Point(637209.083058, 257970.129540)
            >>> new.read(1).attrs['name']
            u'pub'
            >>> new.read(2).attrs['name']
            u'resturnat'
            >>> new.close()
            >>> new.remove()

        """
        self.n_lines += 1
        if self.table is not None and attrs:
            attr = [self.n_lines, ]
            attr.extend(attrs)
            cur = self.table.conn.cursor()
            cur.execute(self.table.columns.insert_str, attr)
            cur.close()

        if set_cats:
            cats = Cats(geo_obj.c_cats)
            cats.reset()
            cats.set(self.n_lines, self.layer)

        if geo_obj.gtype == _Area.gtype:
            result = self._write_area(geo_obj)
        result = libvect.Vect_write_line(self.c_mapinfo, geo_obj.gtype,
                                         geo_obj.c_points, geo_obj.c_cats)
        if result == -1:
            raise GrassError("Not able to write the vector feature.")
        if self._topo_level == 2:
            # return new feature id (on level 2)
            geo_obj.id = result
        else:
            # return offset into file where the feature starts (on level 1)
            geo_obj.offset = result

    @must_be_open
    def has_color_table(self):
        """Return if vector has color table associated in file system;
        Color table stored in the vector's attribute table well be not checked

        >>> cens = Vector('census')
        >>> cens.open(mode='r')
        >>> cens.has_color_table()
        False

        >>> cens.close()
        >>> from grass.pygrass.utils import copy, remove
        >>> copy('census','mycensus','vect')
        >>> from grass.pygrass.modules.shortcuts import vector as v
        >>> v.colors(map='mycensus', color='population', column='TOTAL_POP')
        Module('v.colors')
        >>> mycens = Vector('mycensus')
        >>> mycens.open(mode='r')
        >>> mycens.has_color_table()
        True
        >>> mycens.close()
        >>> remove('mycensus', 'vect')
        """
        loc = Location()
        path = join(loc.path(), self.mapset, 'vector', self.name, 'colr')
        return True if exists(path) else False


#=============================================
# VECTOR WITH TOPOLOGY
#=============================================

class VectorTopo(Vector):
    """Vector class with the support of the GRASS topology.

    Open a vector map using the *with statement*: ::

        >>> with VectorTopo('schools', mode='r') as schools:
        ...     for school in schools[:3]:
        ...         print school.attrs['NAMESHORT']
        ...
        SWIFT CREEK
        BRIARCLIFF
        FARMINGTON WOODS
        >>> schools.is_open()
        False

    ..
    """
    def __init__(self, name, mapset='', *args, **kwargs):
        super(VectorTopo, self).__init__(name, mapset, *args, **kwargs)
        self._topo_level = 2
        self._class_name = 'VectorTopo'

    def __len__(self):
        return libvect.Vect_get_num_lines(self.c_mapinfo)

    def __getitem__(self, key):
        """::

            >>> cens = VectorTopo('census')
            >>> cens.open(mode='r')
            >>> cens[:3]
            [Boundary(v_id=1), Boundary(v_id=2), Boundary(v_id=3)]
            >>> cens.close()

        ..
        """
        if isinstance(key, slice):
            return [self.read(indx)
                    for indx in range(key.start if key.start else 1,
                                      key.stop if key.stop else len(self),
                                      key.step if key.step else 1)]
        elif isinstance(key, int):
            return self.read(key)
        else:
            raise ValueError("Invalid argument type: %r." % key)

    @must_be_open
    def num_primitive_of(self, primitive):
        """Return the number of primitive

        :param primitive: the name of primitive to query; the supported values are:

                            * *boundary*,
                            * *centroid*,
                            * *face*,
                            * *kernel*,
                            * *line*,
                            * *point*
                            * *area*
                            * *volume*

        :type primitive: str

        ::

            >>> cens = VectorTopo('census')
            >>> cens.open(mode='r')
            >>> cens.num_primitive_of('point')
            0
            >>> cens.num_primitive_of('line')
            0
            >>> cens.num_primitive_of('centroid')
            2537
            >>> cens.num_primitive_of('boundary')
            6383
            >>> cens.close()

        ..
        """
        return libvect.Vect_get_num_primitives(self.c_mapinfo,
                                               VTYPE[primitive])

    @must_be_open
    def number_of(self, vtype):
        """Return the number of the choosen element type

        :param vtype: the name of type to query; the supported values are:
                      *areas*, *dblinks*, *faces*, *holes*, *islands*,
                      *kernels*, *line_points*, *lines*, *nodes*,
                      *update_lines*, *update_nodes*, *volumes*
        :type vtype: str

            >>> cens = VectorTopo('census')
            >>> cens.open(mode='r')
            >>> cens.number_of("areas")
            2547
            >>> cens.number_of("islands")
            49
            >>> cens.number_of("holes")
            0
            >>> cens.number_of("lines")
            8920
            >>> cens.number_of("nodes")
            3885
            >>> cens.number_of("pizza")
            ...                     # doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
            Traceback (most recent call last):
                ...
            ValueError: vtype not supported, use one of: 'areas', ...
            >>> cens.close()


        ..
        """
        if vtype in _NUMOF.keys():
            return _NUMOF[vtype](self.c_mapinfo)
        else:
            keys = "', '".join(sorted(_NUMOF.keys()))
            raise ValueError("vtype not supported, use one of: '%s'" % keys)

    @must_be_open
    def num_primitives(self):
        """Return dictionary with the number of all primitives
        """
        output = {}
        for prim in VTYPE.keys():
            output[prim] = self.num_primitive_of(prim)
        return output

    @must_be_open
    def viter(self, vtype, idonly=False):
        """Return an iterator of vector features

        :param vtype: the name of type to query; the supported values are:
                      *areas*, *dblinks*, *faces*, *holes*, *islands*,
                      *kernels*, *line_points*, *lines*, *nodes*,
                      *update_lines*, *update_nodes*, *volumes*
        :type vtype: str
        :param idonly: variable to return only the id of features instead of
                       full features
        :type idonly: bool

            >>> cens = VectorTopo('census', mode='r')
            >>> cens.open(mode='r')
            >>> big = [area for area in cens.viter('areas')
            ...        if area.alive() and area.area() >= 10000]
            >>> big[:3]
            [Area(5), Area(6), Area(13)]


        to sort the result in a efficient way, use: ::

            >>> from operator import methodcaller as method
            >>> big.sort(key=method('area'), reverse=True)  # sort the list
            >>> for area in big[:3]:
            ...     print area, area.area()
            Area(2099) 5392751.5304
            Area(2171) 4799921.30863
            Area(495) 4055812.49695
            >>> cens.close()

        """
        if vtype in _GEOOBJ.keys():
            if _GEOOBJ[vtype] is not None:
                ids = (indx for indx in range(1, self.number_of(vtype) + 1))
                if idonly:
                    return ids
                return (_GEOOBJ[vtype](v_id=indx, c_mapinfo=self.c_mapinfo,
                                       table=self.table,
                                       writable=self.writable)
                        for indx in ids)
        else:
            keys = "', '".join(sorted(_GEOOBJ.keys()))
            raise ValueError("vtype not supported, use one of: '%s'" % keys)

    @must_be_open
    def rewind(self):
        """Rewind vector map to cause reads to start at beginning. ::

            >>> cens = VectorTopo('census')
            >>> cens.open(mode='r')
            >>> cens.next()
            Boundary(v_id=1)
            >>> cens.next()
            Boundary(v_id=2)
            >>> cens.next()
            Boundary(v_id=3)
            >>> cens.rewind()
            >>> cens.next()
            Boundary(v_id=1)
            >>> cens.close()

        ..
        """
        libvect.Vect_rewind(self.c_mapinfo)

    @must_be_open
    def cat(self, cat_id, vtype, layer=None, generator=False, geo=None):
        """Return the geometry features with category == cat_id.

        :param cat_id: the category number
        :type cat_id: int
        :param vtype: the type of geometry feature that we are looking for
        :type vtype: str
        :param layer: the layer number that will be used
        :type layer: int
        :param generator: if True return a generator otherwise it return a
                          list of features
        :type generator: bool
        """
        if geo is None and vtype not in _GEOOBJ:
            keys = "', '".join(sorted(_GEOOBJ.keys()))
            raise ValueError("vtype not supported, use one of: '%s'" % keys)
        Obj = _GEOOBJ[vtype] if geo is None else geo
        ilist = Ilist()
        libvect.Vect_cidx_find_all(self.c_mapinfo,
                                   layer if layer else self.layer,
                                   Obj.gtype, cat_id, ilist.c_ilist)
        is2D = not self.is_3D()
        if generator:
            return (read_line(feature_id=v_id, c_mapinfo=self.c_mapinfo,
                              table=self.table, writable=self.writable,
                              is2D=is2D)
                    for v_id in ilist)
        else:
            return [read_line(feature_id=v_id, c_mapinfo=self.c_mapinfo,
                              table=self.table, writable=self.writable,
                              is2D=is2D)
                    for v_id in ilist]

    @must_be_open
    def read(self, feature_id):
        """Return a geometry object given the feature id.

        :param int feature_id: the id of feature to obtain

        >>> cens = VectorTopo('census')
        >>> cens.open(mode='r')
        >>> feature1 = cens.read(0)                     #doctest: +ELLIPSIS
        Traceback (most recent call last):
            ...
        ValueError: The index must be >0, 0 given.
        >>> feature1 = cens.read(1)
        >>> feature1
        Boundary(v_id=1)
        >>> feature1.length()
        444.54490917696944
        >>> cens.read(-1)
        Centoid(642963.159711, 214994.016279)
        >>> len(cens)
        8920
        >>> cens.read(8920)
        Centoid(642963.159711, 214994.016279)
        >>> cens.read(8921)                             #doctest: +ELLIPSIS
        Traceback (most recent call last):
          ...
        IndexError: Index out of range
        >>> cens.close()

        """
        return read_line(feature_id, self.c_mapinfo, self.table, self.writable,
                         is2D=not self.is_3D())

    @must_be_open
    def is_empty(self):
        """Return if a vector map is empty or not
        """
        primitives = self.num_primitives()
        output = True
        for v in primitives.values():
            if v != 0:
                output = False
                break
        return output

    @must_be_open
    def rewrite(self, line, geo_obj, attrs=None, **kargs):
        """Rewrite a geometry features
        """
        if self.table is not None and attrs:
            attr = [line, ]
            attr.extend(attrs)
            self.table.update(key=line, values=attr)
        elif self.table is None and attrs:
            print "Table for vector {name} does not exist, attributes not" \
                  " loaded".format(name=self.name)
        libvect.Vect_cat_set(geo_obj.c_cats, self.layer, line)
        result = libvect.Vect_rewrite_line(self.c_mapinfo,
                                           line, geo_obj.gtype,
                                           geo_obj.c_points,
                                           geo_obj.c_cats)
        if result == -1:
            raise GrassError("Not able to write the vector feature.")

        # return offset into file where the feature starts
        geo_obj.offset = result

    @must_be_open
    def delete(self, feature_id):
        """Remove a feature by its id

        :param feature_id: the id of the feature
        :type feature_id: int
        """
        if libvect.Vect_rewrite_line(self.c_mapinfo, feature_id) == -1:
            raise GrassError("C funtion: Vect_rewrite_line.")

    @must_be_open
    def restore(self, geo_obj):
        if hasattr(geo_obj, 'offset'):
            if libvect.Vect_restore_line(self.c_mapinfo, geo_obj.id,
                                         geo_obj.offset) == -1:
                raise GrassError("C funtion: Vect_restore_line.")
        else:
            raise ValueError("The value have not an offset attribute.")

    @must_be_open
    def bbox(self):
        """Return the BBox of the vecor map
        """
        bbox = Bbox()
        if libvect.Vect_get_map_box(self.c_mapinfo, bbox.c_bbox) == 0:
            raise GrassError("I can not find the Bbox.")
        return bbox

    @must_be_open
    def select_by_bbox(self, bbox):
        """Return the BBox of the vector map
        """
        # TODO replace with bbox if bbox else Bbox() ??
        bbox = Bbox()
        if libvect.Vect_get_map_box(self.c_mapinfo, bbox.c_bbox) == 0:
            raise GrassError("I can not find the Bbox.")
        return bbox

    def close(self, build=True, release=True):
        """Close the VectorTopo map, if release is True, the memory
        occupied by spatial index is released"""
        if release:
            libvect.Vect_set_release_support(self.c_mapinfo)
        super(VectorTopo, self).close(build=build)
