#!/bin/sh
# generates dbdriver.h

tmp=mk_dbdriver_h.tmp.$$
cat <<'EOT'> dbdriver.h
/* this file was automatically generated by ../mk_dbdriver_h.sh */
#ifndef DBDRIVER_H
#define	DBDRIVER_H

#include <grass/dbstubs.h>

EOT

grep -h '^\( *int *\)\?db__driver' *.c | sed \
	-e 's/^\( *int *\)*/int /' \
	-e 's/ *(.*$/();/' > $tmp
cat $tmp >> dbdriver.h

cat <<'EOT' >> dbdriver.h

#define	init_dbdriver() do{\
EOT

sed 's/^int *db__\([a-zA-Z_]*\).*$/db_\1 = db__\1;\\/' $tmp >> dbdriver.h
cat <<'EOT'>> dbdriver.h
}while(0)

#endif
EOT

rm $tmp
