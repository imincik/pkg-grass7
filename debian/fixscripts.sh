#!/bin/sh

# this script tries to locate all the GRASS scripts than have something
# that makes lintian complain and fix them.

CURDIR=$(pwd)
VERSION=$(echo $(head -2 $CURDIR/include/VERSION)|sed -e 's/ //') 


