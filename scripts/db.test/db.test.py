#!/usr/bin/env python
############################################################################
#
# MODULE:	db.test
# AUTHOR(S):	Radim Blazek
#               Converted to Python by Glynn Clements
# PURPOSE:	Test database driver
# COPYRIGHT:	(C) 2004-2014 by the GRASS Development Team
#
#		This program is free software under the GNU General Public
#		License (version 2). Read the file COPYING that comes with GRASS
#		for details.
#
#############################################################################

#%module
#% description: Test database driver, database must exist and set by db.connect.
#% keyword: database
#% keyword: attribute table
#%end
#%option
#% key: test
#% type: string
#% description: Test name
#% required: yes
#% options: test1
#%end

import sys
import os
from grass.script import core as grass
from grass.script import db as grassdb
from grass.exceptions import CalledModuleError

def main():
    test_file = options['test']

    expected = grass.tempfile()
    result = grass.tempfile()

    dbconn = grassdb.db_connection()
    grass.message(_("Using DB driver: %s") % dbconn['driver'])

    infile = os.path.join(os.environ['GISBASE'], 'etc', 'db.test', test_file)
    inf = file(infile)

    while True:
	type = inf.readline()
	if not type:
	    break
	type = type.rstrip('\r\n')

	sql = inf.readline().rstrip('\r\n')
	sys.stdout.write(sql + '\n')

	# Copy expected result to temp file

        try:
            if type == 'X':
                grass.write_command('db.execute', input = '-', stdin = sql + '\n')
            else:
                resf = file(result, 'w')
                grass.write_command('db.select', input = '-', flags = 'c', stdin = sql + '\n', stdout = resf)
                resf.close()

        except CalledModuleError:
            grass.error("EXECUTE: ******** ERROR ********")
        else:
            grass.message(_("EXECUTE: OK"))

	expf = file(expected, 'w')
	while True:
	    res = inf.readline().rstrip('\r\n')
	    if not res:
		break
	    expf.write(res + '\n')
	expf.close()

	if type == 'S':
	    if grass.call(['diff', result, expected]) != 0:
		grass.error("RESULT: ******** ERROR ********")
	    else:
		grass.message(_("RESULT: OK"))

if __name__ == "__main__":
    options, flags = grass.parser()
    main()

