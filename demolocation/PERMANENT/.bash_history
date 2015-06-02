v.unpack country_boundaries.pack 
g.proj -w
v.unpack country_boundaries.pack -v
v.unpack country_boundaries.pack --v
g.proj -w
g.proj -p
cd grass70/demolocation/PERMANENT/
pwd
meld PROJ_INFO ~/grassdata/ll/PERMANENT/PERMANENT/PROJ_INFO 
cp ~/grassdata/ll/PERMANENT/PERMANENT/PROJ_INFO .
svn diff
cat PROJ_
cat PROJ_INFO 
cat PROJ_UNITS Ã
cat PROJ_UNITS
ccat ~/grassdata/ll/PERMANENT/PERMANENT/PROJ_UNITS 
cat ~/grassdata/ll/PERMANENT/PERMANENT/PROJ_UNITS 
svn ci -m"demolocation: update to current file structure as generated with 'grass70 -c EPSG:4326 ~/grassdata/ll/PERMANENT'" PROJ_INFO 
v.unpack country_boundaries.pack --v
l /home/neteler/grass70/demolocation/PERMANENT/
cd grass70/demolocation/PERMANENT/
mkdir sqlite
cd
v.unpack country_boundaries.pack --v
v.unpack country_boundaries.pack --v --o
v.info country_boundaries.pack
v.info country_boundaries
v.db.connect -p country_boundaries
g.region -p
g.gui
v.info -c country_boundaries
cd demolocation/PERMANENT/
l
g.list vect
g.remove vect=country_boundaries
sqlite3 sqlite/sqlite.db 
rmdir dbf/
rm -rf sqlite/
cd
v.unpack country_boundaries.pack
r.fuzzy.system help
R
cd
R
