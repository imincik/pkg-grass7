# -*- coding: utf-8 -*-
from __future__ import (nested_scopes, generators, division, absolute_import,
                        with_statement, print_function, unicode_literals)
from grass.pygrass.utils import docstring_property
from grass.pygrass.modules.interface import read


class Flag(object):
    """The Flag object store all information about a flag of module.

    It is possible to set flags of command using this object.

    >>> flag = Flag(diz=dict(name='a', description='Flag description',
    ...                      default=True))
    >>> flag.name
    u'a'
    >>> flag.special
    False
    >>> flag.description
    u'Flag description'
    >>> flag = Flag(diz=dict(name='overwrite'))
    >>> flag.name
    u'overwrite'
    >>> flag.special
    True
    """
    def __init__(self, xflag=None, diz=None):
        self.value = False
        diz = read.element2dict(xflag) if xflag is not None else diz
        self.name = diz['name']
        self.special = True if self.name in (
            'verbose', 'overwrite', 'quiet', 'run') else False
        self.description = diz.get('description', None)
        self.default = diz.get('default', None)
        self.guisection = diz.get('guisection', None)

    def get_bash(self):
        """Return the BASH representation of a flag.

        >>> flag = Flag(diz=dict(name='a', description='Flag description',
        ...                      default=True))
        >>> flag.get_bash()
        u''
        >>> flag.value = True
        >>> flag.get_bash()
        u'-a'
        >>> flag = Flag(diz=dict(name='overwrite'))
        >>> flag.get_bash()
        u''
        >>> flag.value = True
        >>> flag.get_bash()
        u'--o'
        """
        if self.value:
            if self.special:
                return '--%s' % self.name[0]
            else:
                return '-%s' % self.name
        else:
            return ''

    def get_python(self):
        """Return the python representation of a flag.

        >>> flag = Flag(diz=dict(name='a', description='Flag description',
        ...                      default=True))
        >>> flag.get_python()
        u''
        >>> flag.value = True
        >>> flag.get_python()
        u'a'
        >>> flag = Flag(diz=dict(name='overwrite'))
        >>> flag.get_python()
        u''
        >>> flag.value = True
        >>> flag.get_python()
        u'overwrite=True'
        """
        if self.value:
            return '%s=True' % self.name if self.special else self.name
        return ''

    def __str__(self):
        """Return the BASH representation of the flag."""
        return self.get_bash()

    def __repr__(self):
        """Return a string with the python representation of the instance."""
        return "Flag <%s> (%s)" % (self.name, self.description)

    @docstring_property(__doc__)
    def __doc__(self):
        """Return a documentation string, something like:

        {name}: {default}
            {description}

        >>>  flag = Flag(diz=dict(name='a', description='Flag description',
        ...                      default=True))
        >>> print(flag.__doc__)
        a: True
            Flag description

        >>> flag = Flag(diz=dict(name='overwrite'))
        >>> print(flag.__doc__)
        overwrite: None
            None

        """
        return read.DOC['flag'].format(name=self.name,
                                       default=repr(self.default),
                                       description=self.description)
