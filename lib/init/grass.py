#!/usr/bin/env python
#############################################################################
#
# MODULE:       GRASS initialization script
# AUTHOR(S):    Original author unknown - probably CERL
#               Andreas Lange <andreas.lange rhein-main.de>
#               Huidae Cho <grass4u gmail.com>
#               Justin Hickey <jhickey hpcc.nectec.or.th>
#               Markus Neteler <neteler osgeo.org>
#               Hamish Bowman <hamish_b yahoo.com>
#
#               GRASS 7: converted to Python (based on init.sh shell
#               script from GRASS 6) by Glynn Clements
#               Martin Landa <landa.martin gmail.com>
#               Luca Delucchi <lucadeluge gmail.com>
# PURPOSE:      Sets up environment variables, parses any remaining
#               command line options for setting the GISDBASE, LOCATION,
#               and/or MAPSET. Finally it starts GRASS with the appropriate
#               user interface and cleans up after it is finished.
# COPYRIGHT:    (C) 2000-2015 by the GRASS Development Team
#
#               This program is free software under the GNU General
#               Public License (>=v2). Read the file COPYING that
#               comes with GRASS for details.
#
#############################################################################

import sys
import os
import atexit
import string
import subprocess
import re
import platform
import tempfile

# Variables substituted during build process
if 'GISBASE' in os.environ:
    gisbase = os.environ['GISBASE']
else:
    gisbase = "@GISBASE@"
cmd_name = "@START_UP@"
grass_version = "@GRASS_VERSION_NUMBER@"
ld_library_path_var = '@LD_LIBRARY_PATH_VAR@'
if 'GRASS_PROJSHARE' in os.environ:
    config_projshare = os.environ['GRASS_PROJSHARE']
else:
    config_projshare = "@CONFIG_PROJSHARE@"

# configuration directory
grass_env_file = None  # see check_shell()
if sys.platform == 'win32':
    grass_config_dirname = "GRASS7"
    grass_config_dir = os.path.join(os.getenv('APPDATA'), grass_config_dirname)
else:
    grass_config_dirname = ".grass7"
    grass_config_dir = os.path.join(os.getenv('HOME'), grass_config_dirname)

gisbase = os.path.normpath(gisbase)

# i18N
import gettext
gettext.install('grasslibs', os.path.join(gisbase, 'locale'))

tmpdir = None
lockfile = None
remove_lockfile = True
location = None
create_new = None
grass_gui = None
exit_grass = None

def warning(text):
    sys.stderr.write(_("WARNING") + ': ' + text + os.linesep)


def try_remove(path):
    try:
        os.remove(path)
    except:
        pass


def try_rmdir(path):
    try:
        os.rmdir(path)
    except:
        pass


def clean_env():
    env_curr = read_gisrc()
    env_new = {}
    for k,v in env_curr.iteritems():
        if 'MONITOR' not in k:
            env_new[k] = v

    write_gisrc(env_new)


def cleanup_dir(path):
    if not path:
        return

    for root, dirs, files in os.walk(path, topdown=False):
        for name in files:
            try_remove(os.path.join(root, name))
        for name in dirs:
            try_rmdir(os.path.join(root, name))


def cleanup():
    tmpdir, lockfile, remove_lockfile
    # all exits after setting up tmp dirs (system/location) should
    # also tidy it up
    cleanup_dir(tmpdir)
    try_rmdir(tmpdir)
    if location:
        tmpdir_loc = os.path.join(location, ".tmp")
        cleanup_dir(tmpdir_loc)
        try_rmdir(tmpdir_loc)

    # remove lock-file if requested
    if lockfile and remove_lockfile:
        try_remove(lockfile)


def fatal(msg):
    sys.stderr.write("%s: " % _('ERROR') + msg + os.linesep)
    sys.exit(_("Exiting..."))


def message(msg):
    sys.stderr.write(msg + "\n")
    sys.stderr.flush()


def readfile(path):
    f = open(path, 'r')
    s = f.read()
    f.close()
    return s


def writefile(path, s):
    f = open(path, 'w')
    f.write(s)
    f.close()


def call(cmd, **kwargs):
    if windows:
        kwargs['shell'] = True
    return subprocess.call(cmd, **kwargs)


def Popen(cmd, **kwargs):
    if windows:
        kwargs['shell'] = True
    return subprocess.Popen(cmd, **kwargs)


def gfile(*args):
    return os.path.join(gisbase, *args)

help_text = r"""GRASS GIS %s
Geographic Resources Analysis Support System (GRASS GIS).

%s:
  $CMD_NAME [-h | -help | --help] [-v | --version] [-c | -c geofile | -c EPSG:code[:datum_trans]]
          [-e] [-text | -gui] [--config param]
          [[[<GISDBASE>/]<LOCATION_NAME>/]<MAPSET>]

%s:
  -h or -help or --help          %s
  -v or --version                %s
  -c                             %s
  -e                             %s
  -text                          %s
                                   %s
  -gtext                         %s
                                   %s
  -gui                           %s
                                   %s
  --config                       %s
                                   %s

%s:
  GISDBASE                       %s
  LOCATION_NAME                  %s
  MAPSET                         %s

  GISDBASE/LOCATION_NAME/MAPSET  %s

%s:
  GRASS_GUI                      %s
  GRASS_HTML_BROWSER             %s
  GRASS_ADDON_PATH               %s
  GRASS_ADDON_BASE               %s
  GRASS_BATCH_JOB                %s
  GRASS_PYTHON                   %s
""" % (grass_version,
       _("Usage"),
       _("Flags"),
       _("print this help message"),
       _("show version information and exit"),
       _("create given database, location or mapset if it doesn't exist"),
       _("exit after creation of location or mapset. Only with -c flag"),
       _("use text based interface (skip welcome screen)"),
       _("and set as default"),
       _("use text based interface (show welcome screen)"),
       _("and set as default"),
       _("use $DEFAULT_GUI graphical user interface"),
       _("and set as default"),
       _("print GRASS configuration parameters"),
       _("options: arch,build,compiler,path,revision"),
       _("Parameters"),
       _("initial database (path to GIS data)"),
       _("initial location"),
       _("initial mapset"),
       _("fully qualified initial mapset directory"),
       _("Environment variables relevant for startup"),
       _("select GUI (text, gui)"),
       _("set html web browser for help pages"),
       _("set additional path(s) to local GRASS modules or user scripts"),
       _("set additional GISBASE for locally installed GRASS Addons"),
       _("shell script to be processed as batch job"),
       _("set python shell name to override 'python'"))


def help_message():
    t = string.Template(help_text)
    s = t.substitute(CMD_NAME=cmd_name, DEFAULT_GUI=default_gui)
    sys.stderr.write(s)


def create_tmp():
    global tmpdir
    ## use $TMPDIR if it exists, then $TEMP, otherwise /tmp
    tmp = os.getenv('TMPDIR')
    if not tmp:
        tmp = os.getenv('TEMP')
    if not tmp:
        tmp = os.getenv('TMP')
    if not tmp:
        tmp = tempfile.gettempdir()
    if tmp:
        tmpdir = os.path.join(tmp, "grass7-%(user)s-%(lock)s" % {'user': user,
                                                             'lock': gis_lock})
        try:
            os.mkdir(tmpdir, 0700)
        except:
            tmp = None
    if not tmp:
        for ttmp in ("/tmp", "/var/tmp", "/usr/tmp"):
            tmp = ttmp
            tmpdir = os.path.join(tmp, "grass7-%(user)s-%(lock)s" % {
                                              'user': user, 'lock': gis_lock})
            try:
                os.mkdir(tmpdir, 0700)
            except:
                tmp = None
            if tmp:
                break
    if not tmp:
        fatal(_("Unable to create temporary directory <grass7-%(user)s-" \
                "%(lock)s>! Exiting.") % {'user': user, 'lock': gis_lock})


def create_gisrc():
    global gisrc, gisrcrc
    # Set the session grassrc file
    gisrc = os.path.join(tmpdir, "gisrc")
    os.environ['GISRC'] = gisrc

    # remove invalid GISRC file to avoid disturbing error messages:
    try:
        s = readfile(gisrcrc)
        if "UNKNOWN" in s:
            try_remove(gisrcrc)
            s = None
    except:
        s = None

    # Copy the global grassrc file to the session grassrc file
    if s:
        writefile(gisrc, s)


def read_gisrc():
    kv = {}
    try:
        f = open(gisrc, 'r')
    except IOError:
        return kv

    for line in f:
        k, v = line.split(':', 1)
        kv[k.strip()] = v.strip()
    f.close()

    return kv


def read_env_file(path):
    kv = {}
    f = open(path, 'r')
    for line in f:
        k, v = line.split(':', 1)
        kv[k.strip()] = v.strip()
    f.close()
    return kv


def write_gisrc(kv):
    f = open(gisrc, 'w')
    for k, v in kv.iteritems():
        f.write("%s: %s\n" % (k, v))
    f.close()


def read_gui():
    global grass_gui
    # At this point the GRASS user interface variable has been set from the
    # command line, been set from an external environment variable, or is 
    # not set. So we check if it is not set
    if not grass_gui:
        # Check for a reference to the GRASS user interface in the grassrc file
        if os.access(gisrc, os.R_OK):
            kv = read_gisrc()
            if 'GRASS_GUI' in os.environ:
                grass_gui = os.environ['GRASS_GUI']
            elif 'GUI' in kv:
                grass_gui = kv['GUI']
            elif 'GRASS_GUI' in kv:
                # For backward compatibility (GRASS_GUI renamed to GUI)
                grass_gui = kv['GRASS_GUI']
            else:
                # Set the GRASS user interface to the default if needed
                grass_gui = default_gui

    if not grass_gui:
        grass_gui = default_gui

    if grass_gui == 'gui':
        grass_gui = default_gui

    # FIXME oldtcltk, gis.m, d.m no longer exist
    if grass_gui in ['d.m', 'gis.m', 'oldtcltk', 'tcltk']:
        warning(_("GUI <%s> not supported in this version") % grass_gui)
        grass_gui = default_gui


def path_prepend(dir, var):
    path = os.getenv(var)
    if path:
        path = dir + os.pathsep + path
    else:
        path = dir
    os.environ[var] = path


def path_append(dir, var):
    path = os.getenv(var)
    if path:
        path = path + os.pathsep + dir
    else:
        path = dir
    os.environ[var] = path


def set_paths():
    # addons (path)
    addon_path = os.getenv('GRASS_ADDON_PATH')
    if addon_path:
        for path in addon_path.split(os.pathsep):
            path_prepend(addon_path, 'PATH')

    # addons (base)
    addon_base = os.getenv('GRASS_ADDON_BASE')
    if not addon_base:
        addon_base = os.path.join(grass_config_dir, 'addons')
        os.environ['GRASS_ADDON_BASE'] = addon_base
    if not windows:
        path_prepend(os.path.join(addon_base, 'scripts'), 'PATH')
    path_prepend(os.path.join(addon_base, 'bin'), 'PATH')
    
    # standard installation
    if not windows:
        path_prepend(gfile('scripts'), 'PATH')
    path_prepend(gfile('bin'), 'PATH')

    # Set PYTHONPATH to find GRASS Python modules
    if os.path.exists(gfile('gui', 'wxpython')):
        path_prepend(gfile('gui', 'wxpython'), 'PYTHONPATH')
    if os.path.exists(gfile('etc', 'python')):
        path_prepend(gfile('etc', 'python'), 'PYTHONPATH')

    # set path for the GRASS man pages
    grass_man_path = os.path.join(gisbase, 'docs', 'man')
    addons_man_path = os.path.join(addon_base, 'docs', 'man')
    man_path = os.getenv('MANPATH')
    sys_man_path = None
    if man_path:
        path_prepend(addons_man_path, 'MANPATH')
        path_prepend(grass_man_path, 'MANPATH')
    else:
        try:
            nul = open(os.devnull, 'w')
            p = Popen(['manpath'], stdout=subprocess.PIPE, stderr=nul)
            nul.close()
            s = p.stdout.read()
            p.wait()
            sys_man_path = s.strip()
        except:
            pass

        if sys_man_path:
            os.environ['MANPATH'] = sys_man_path
            path_prepend(addons_man_path, 'MANPATH')
            path_prepend(grass_man_path, 'MANPATH')
        else:
            os.environ['MANPATH'] = addons_man_path
            path_prepend(grass_man_path, 'MANPATH')


def find_exe(pgm):
    for dir in os.getenv('PATH').split(os.pathsep):
        path = os.path.join(dir, pgm)
        if os.access(path, os.X_OK):
            return path
    return None


def set_defaults():
    # GRASS_PAGER
    if not os.getenv('GRASS_PAGER'):
        if find_exe("more"):
            pager = "more"
        elif find_exe("less"):
            pager = "less"
        elif windows:
            pager = "more"
        else:
            pager = "cat"
        os.environ['GRASS_PAGER'] = pager

    # GRASS_PYTHON
    if not os.getenv('GRASS_PYTHON'):
        if windows:
            os.environ['GRASS_PYTHON'] = "python.exe"
        else:
            os.environ['GRASS_PYTHON'] = "python"

    # GRASS_GNUPLOT
    if not os.getenv('GRASS_GNUPLOT'):
        os.environ['GRASS_GNUPLOT'] = "gnuplot -persist"

    # GRASS_PROJSHARE
    if not os.getenv('GRASS_PROJSHARE'):
        os.environ['GRASS_PROJSHARE'] = config_projshare

    
def set_browser():
    # GRASS_HTML_BROWSER
    browser = os.getenv('GRASS_HTML_BROWSER')
    if not browser:
        if macosx:
            # OSX doesn't execute browsers from the shell PATH - route thru a
            # script
            browser = gfile('etc', "html_browser_mac.sh")
            os.environ['GRASS_HTML_BROWSER_MACOSX'] = "-b com.apple.helpviewer"

        if windows or cygwin:
            # MinGW startup moved to into init.bat
            browser = "explorer"
        else:
            # the usual suspects
            browsers = ["xdg-open", "x-www-browser", "htmlview", "konqueror", "mozilla",
                        "mozilla-firefox", "firefox", "iceweasel", "opera",
                        "netscape", "dillo", "lynx", "links", "w3c"]
            for b in browsers:
                if find_exe(b):
                    browser = b
                    break

    elif macosx:
        # OSX doesn't execute browsers from the shell PATH - route thru a
        # script
        os.environ['GRASS_HTML_BROWSER_MACOSX'] = "-b %s" % browser
        browser = gfile('etc', "html_browser_mac.sh")

    if not browser:
        warning(_("Searched for a web browser, but none found"))
        # even so we set konqueror to make lib/gis/parser.c happy:
        browser = "konqueror"

    os.environ['GRASS_HTML_BROWSER'] = browser


def create_initial_gisrc():
    # for convenience, define GISDBASE as pwd:
    s = r"""GISDBASE: %s
LOCATION_NAME: <UNKNOWN>
MAPSET: <UNKNOWN>
""" % os.getcwd()
    writefile(gisrc, s)


def check_gui():
    global grass_gui, wxpython_base
    # Check if we are running X windows by checking the DISPLAY variable
    if os.getenv('DISPLAY') or windows or macosx:
        # Check if python is working properly
        if grass_gui in ('wxpython', 'gtext'):
            nul = open(os.devnull, 'w')
            p = Popen([os.environ['GRASS_PYTHON']], stdin=subprocess.PIPE,
                      stdout=nul, stderr=nul)
            nul.close()
            p.stdin.write("variable=True")
            p.stdin.close()
            p.wait()
            if p.returncode == 0:
                # Set the wxpython base directory
                wxpython_base = gfile("gui", "wxpython")
            else:
                # Python was not found - switch to text interface mode
                warning(_("The python command does not work as expected!\n"
                          "Please check your GRASS_PYTHON environment variable.\n"
                          "Use the -help option for details.\n"
                          "Switching to text based interface mode.\n\n"
                          "Hit RETURN to continue.\n"))
                sys.stdin.readline()
                grass_gui = 'text'

    else:
        # Display a message if a graphical interface was expected
        if grass_gui != 'text':
            # Set the interface mode to text
            warning(_("It appears that the X Windows system is not active.\n"
                      "A graphical based user interface is not supported.\n"
                      "Switching to text based interface mode.\n\n"
                      "Hit RETURN to continue"""))
            sys.stdin.readline()
            grass_gui = 'text'

    # Save the user interface variable in the grassrc file - choose a temporary
    # file name that should not match another file
    if os.access(gisrc, os.F_OK):
        kv = read_gisrc()
        kv['GUI'] = grass_gui
        write_gisrc(kv)


def non_interactive(arg, geofile=None):
    global gisdbase, location_name, mapset, location
    # Try non-interactive startup
    l = None

    if arg == '-':
        if location:
            l = location
    else:
        l = arg

    if l:
        if l == '.':
            l = os.getcwd()
        elif not os.path.isabs(l):
            l = os.path.abspath(l)

        l, mapset = os.path.split(l)
        if not mapset:
            l, mapset = os.path.split(l)
        l, location_name = os.path.split(l)
        gisdbase = l
    
    if gisdbase and location_name and mapset:
        location = os.path.join(gisdbase, location_name, mapset)

        # check if 'location' is a valid GRASS location/mapset
        if not os.access(os.path.join(location, "WIND"), os.R_OK):
            if not create_new:
                # 'location' is not valid, check if 'location_name' is
                # a valid GRASS location
                if not os.path.exists(os.path.join(gisdbase, location_name)):
                    fatal(_("Location <%s> doesn't exist") % os.path.join(gisdbase, location_name))
                elif 'PERMANENT' not in os.listdir(os.path.join(gisdbase, location_name)) or \
                        not os.path.isdir(os.path.join(gisdbase, location_name, 'PERMANENT')) or \
                        not os.path.isfile((os.path.join(gisdbase, location_name, 'PERMANENT',
                                                         'DEFAULT_WIND'))):
                        fatal(_("ERROR: <%s> is not a valid GRASS location") % \
                                  os.path.join(gisdbase, location_name))
                else:
                    fatal(_("Mapset <%s> doesn't exist in GRASS location <%s>. "
                            "A new mapset can be created by '-c' switch.") % (mapset, location_name))

            else:
                # 'location' is not valid, the user wants to create
                # mapset on the fly
                if not os.access(os.path.join(gisdbase, location_name,
                                              "PERMANENT",
                                              "DEFAULT_WIND"), os.F_OK):
                    # 'location_name' is not a valid GRASS location,
                    # create new location and 'PERMANENT' mapset
                    gisdbase = os.path.join(gisdbase, location_name)
                    location_name = mapset
                    mapset = "PERMANENT"
                    if os.access(os.path.join(os.path.join(gisdbase,
                                                           location_name,
                                                           "PERMANENT",
                                                           "DEFAULT_WIND")),
                                 os.F_OK):
                        fatal(_("Failed to create new location. "
                                "The location <%s> already exists." % location_name))
                        
                    if gfile('etc', 'python') not in sys.path:
                        sys.path.append(gfile('etc', 'python'))
                    from grass.script import core as grass
                    
                    try:
                        if geofile and geofile.upper().find('EPSG:') > -1:
                            # create location using EPSG code
                            epsg = geofile.split(':', 1)[1]
                            if ':' in epsg:
                                epsg, datum_trans = epsg.split(':', 1)
                            else:
                                datum_trans = None
                            grass.create_location(gisdbase, location_name,
                                                  epsg=epsg, datum_trans=datum_trans)
                        else:
                            # create location using georeferenced file
                            grass.create_location(gisdbase, location_name,
                                                  filename=geofile)
                    except grass.ScriptError as e:
                        fatal(e.value.strip('"').strip("'").replace('\\n',
                                                                   os.linesep))
                else:
                    # 'location_name' is a valid GRASS location,
                    # create new mapset
                    os.mkdir(location)
                    # copy PERMANENT/DEFAULT_WIND to <mapset>/WIND
                    s = readfile(os.path.join(gisdbase, location_name,
                                              "PERMANENT", "DEFAULT_WIND"))
                    writefile(os.path.join(location, "WIND"), s)
                    message(_("Missing WIND file fixed"))

        if os.access(gisrc, os.R_OK):
            kv = read_gisrc()
        else:
            kv = {}

        kv['GISDBASE'] = gisdbase
        kv['LOCATION_NAME'] = location_name
        kv['MAPSET'] = mapset
        write_gisrc(kv)
    else:
        fatal(_("GISDBASE, LOCATION_NAME and MAPSET variables not set properly.\n"
                "Interactive startup needed."))


def set_data():
    # User selects LOCATION and MAPSET if not set
    if not location:
        # Check for text interface
        if grass_gui == 'text':
            pass
        # Check for GUI
        elif grass_gui in ('gtext', 'wxpython'):
            gui_startup(grass_gui == 'gtext')
        else:
            # Shouldn't need this but you never know
            fatal(_("Invalid user interface specified - <%s>. " 
                    "Use the --help option to see valid interface names.") % grass_gui)


def gui_startup(wscreen_only = False):
    if grass_gui in ('wxpython', 'gtext'):
        ret = call([os.getenv('GRASS_PYTHON'), gfile(wxpython_base, "gis_set.py")])

    if ret == 0:
        pass
    elif ret == 1:
        # The startup script printed an error message so wait
        # for user to read it
        message(_("Error in GUI startup. If necessary, please "
                  "report this error to the GRASS developers.\n"
                  "Switching to text mode now.\n\n"
                  "Hit RETURN to continue..."))
        sys.stdin.readline()

        os.execlp(cmd_name, "-text")
        sys.exit(1)
    elif ret == 2:
        # User wants to exit from GRASS
        message(_("Received EXIT message from GUI.\nGRASS is not started. Bye."))
        sys.exit(0)
    else:
        fatal(_("Invalid return code from GUI startup script.\n"
                "Please advise GRASS developers of this error."))


def load_gisrc():
    global gisdbase, location_name, mapset, location
    kv = read_gisrc()
    gisdbase = kv.get('GISDBASE')
    location_name = kv.get('LOCATION_NAME')
    mapset = kv.get('MAPSET')
    if not gisdbase or not location_name or not mapset:
        fatal(_("Error reading data path information from g.gisenv.\n"
                "GISDBASE=%(gisbase)s\n"
                "LOCATION_NAME=%(location)s\n"
                "MAPSET=%(mapset)s\n\n"
                "Check the <%s(file)> file." % \
                    {'gisbase': gisdbase, 'location': location_name,
                     'mapset': mapset, 'file': gisrcrc}))

    location = os.path.join(gisdbase, location_name, mapset)


# load environmental variables from grass_env_file
def load_env():
    if not os.access(grass_env_file, os.R_OK):
        return

    for line in readfile(grass_env_file).split(os.linesep):
        try:
            k, v = map(lambda x: x.strip(), line.strip().split(' ', 1)[1].split('=', 1))
        except:
            continue
        
        evalue = os.getenv(k)
        if evalue:
            if k == 'GRASS_ADDON_PATH':
                os.environ[k] = evalue + os.pathsep + v
            else:
                warning(_("Environmental variable '%s' already set, ignoring value '%s'") % \
                            (k, v))
        else:
            os.environ[k] = v
    
    # Allow for mixed ISIS-GRASS Environment
    if os.getenv('ISISROOT'):
        isis = os.getenv('ISISROOT')
        os.environ['ISIS_LIB'] = isis + os.sep + "lib"
        os.environ['ISIS_3RDPARTY'] = isis + os.sep + "3rdParty" + os.sep + "lib"
        os.environ['QT_PLUGIN_PATH'] = isis + os.sep + "3rdParty" + os.sep + "plugins"
        #os.environ['ISIS3DATA'] = isis + "$ISIS3DATA"
        libpath = os.getenv('LD_LIBRARY_PATH', '')
        isislibpath = os.getenv('ISIS_LIB')
        isis3rdparty = os.getenv('ISIS_3RDPARTY')
        os.environ['LD_LIBRARY_PATH'] = libpath + os.pathsep + isislibpath + os.pathsep + isis3rdparty

def set_language():
    # This function is used to override system default language and locale
    # Such override can be requested only from wxGUI
    # An override if user has provided correct environmental variables as
    # LC_MESSAGES or LANG is not necessary.
    # Unfortunately currently a working solution for Windows is lacking
    # thus it always on Vista and XP will print an error.
    # See discussion for Windows not following its own documentation and
    # not accepting ISO codes as valid locale identifiers http://bugs.python.org/issue10466
    import locale
    
    language = 'None' # Such string sometimes is present in wx file
    encoding = None
    
    # Override value is stored in wxGUI preferences file.
    # As it's the only thing required, we'll just grep it out.
    try:
        fd = open(os.path.join(grass_config_dir, 'wx'), 'r')
    except:
        # Even if there is no override, we still need to set locale.
        pass
    else:
        for line in fd:
            if re.search('^language', line):
                line = line.rstrip(' %s' % os.linesep)
                language = ''.join(line.split(';')[-1:])
                break
        fd.close()
    
    if language == 'None' or language == '' or not language:
        # Language override is disabled (system language specified)
        # As by default program runs with C locale, but users expect to
        # have their default locale, we'll just set default locale
        try:
            locale.setlocale(locale.LC_ALL, '')
        except locale.Error as e:
            # If we get here, system locale settings are terribly wrong
            # There is no point to continue as GRASS/Python will fail
            # in some other unpredictable way.
            print "System locale is not usable. It indicates misconfigured environment."
            print "Reported error message: %s" % e
            sys.exit("Fix system locale settings and then try again.")
        
        language, encoding = locale.getdefaultlocale()
        if not language:
            warning(_("Default locale settings are missing. GRASS running with C locale."))
            return
    
    else:
        message(_("A language override has been requested. Trying to switch GRASS into '%s'...") % language)
        
        try:
            locale.setlocale(locale.LC_ALL, language)
        except locale.Error as e:
            try:
                # Locale lang.encoding might be missing. Let's try
                # UTF-8 encoding before giving up as on Linux systems
                # lang.UTF-8 locales are more common than legacy
                # ISO-8859 ones.
                encoding = 'UTF-8'
                normalized = locale.normalize('%s.%s' % (language, encoding))
                locale.setlocale(locale.LC_ALL, normalized)
            except locale.Error as e:
                # The last attempt...
                try:
                    encoding = locale.getpreferredencoding()
                    normalized = locale.normalize('%s.%s' % (language, encoding))
                    locale.setlocale(locale.LC_ALL, normalized)
                except locale.Error as e:
                    # If we got so far, attempts to set up language and locale have failed
                    # on this system
                    sys.stderr.write("Failed to enforce user specified language '%s' with error: '%s'\n" % (language, e))
                    sys.stderr.write("A LANGUAGE environmental variable has been set.\nPart of messages will be displayed in the requested language.\n")
                    # Even if setting locale will fail, let's set LANG in a hope,
                    # that UI will use it GRASS texts will be in selected language,
                    # system messages (i.e. OK, Cancel etc.) - in system default
                    # language
                    os.environ['LANGUAGE'] = language
                    return
    
    # Set up environment for subprocesses
    os.environ['LANGUAGE'] = language
    os.environ['LANG'] = language
    if encoding:
        normalized = locale.normalize('%s.%s' % (language, encoding))
    else:
        normalized = language
    for lc in ('LC_CTYPE', 'LC_MESSAGES', 'LC_TIME', 'LC_COLLATE',
               'LC_MONETARY', 'LC_PAPER', 'LC_NAME', 'LC_ADDRESS',
               'LC_TELEPHONE', 'LC_MEASUREMENT', 'LC_IDENTIFICATION'):
        os.environ[lc] = normalized

    # Some code in GRASS might not like other decimal separators than .
    # Other potential sources for problems are: LC_TIME LC_CTYPE
    locale.setlocale(locale.LC_NUMERIC, 'C')
    os.environ['LC_NUMERIC'] = 'C'
    if os.getenv('LC_ALL'):
        del os.environ['LC_ALL']  # Remove LC_ALL to not override LC_NUMERIC
    
    # From now on enforce the new language
    if encoding: 
        gettext.install('grasslibs', os.path.join(gisbase, 'locale'), codeset=encoding)
    else:
        gettext.install('grasslibs', os.path.join(gisbase, 'locale'))

def check_lock():
    global lockfile
    if not os.path.exists(location):
        fatal(_("Path '%s' doesn't exist") % location)

    # Check for concurrent use
    lockfile = os.path.join(location, ".gislock")
    ret = call([gfile("etc", "lock"), lockfile, "%d" % os.getpid()])
    if ret == 0:
        msg = None
    elif ret == 2:
        msg = _("%(user)s is currently running GRASS in selected mapset (" \
                "file %(file)s found). Concurrent use not allowed." % {
                'user': user, 'file': lockfile})
    else:
        msg = _("Unable to properly access '%s'.\n"
                "Please notify system personel.") % lockfile

    if msg:
        if grass_gui == "wxpython":
            call([os.getenv('GRASS_PYTHON'), gfile(wxpython_base, "gis_set_error.py"), msg])
        else:
            global remove_lockfile
            remove_lockfile = False
            fatal(msg)


def make_fontcap():
    fc = os.getenv('GRASS_FONT_CAP')
    if fc and not os.access(fc, os.R_OK):
        message(_("Building user fontcap..."))
        call(["g.mkfontcap"])


def check_shell():
    global sh, shellname, grass_env_file
    # cygwin has many problems with the shell setup
    # below, so i hardcoded everything here.
    if sys.platform == 'cygwin':
        sh = "cygwin"
        shellname = "GNU Bash (Cygwin)"
        os.environ['SHELL'] = "/usr/bin/bash.exe"
        os.environ['OSTYPE'] = "cygwin"
    else:
        # in docker the 'SHELL' variable may not be
        # visible in a Python session
        try:
            sh = os.path.basename(os.getenv('SHELL'))
        except:
            sh = 'sh'
            os.environ['SHELL'] = sh
        
        if windows and sh:
            sh = os.path.splitext(sh)[0]
        
        if sh == "ksh":
            shellname = "Korn Shell"
        elif sh == "csh":
            shellname = "C Shell"
        elif sh == "tcsh":
            shellname = "TC Shell"
        elif sh == "bash":
            shellname = "Bash Shell"
        elif sh == "sh":
            shellname = "Bourne Shell"
        elif sh == "zsh":
            shellname = "Z Shell"
        elif sh == "cmd":
            shellname = "Command Shell"
        else:
            shellname = "shell"

    if sh in ['csh', 'tcsh']:
        grass_env_file = os.path.join(grass_config_dir, 'cshrc')
    elif sh in ['bash', 'msh', 'cygwin', 'sh']:
        grass_env_file = os.path.join(grass_config_dir, 'bashrc')
    elif sh == 'zsh':
        grass_env_file = os.path.join(grass_config_dir, 'zshrc')
    elif sh == 'cmd':
        grass_env_file = os.path.join(grass_config_dir, 'env.bat')
    else:
        grass_env_file = os.path.join(grass_config_dir, 'bashrc')
        warning(_("Unsupported shell <%(sh)s>: %(env)s") % {'sh': sh,
                                                       'env': grass_env_file})

    # check for SHELL
    if not os.getenv('SHELL'):
        fatal(_("The SHELL variable is not set"))


def check_batch_job():
    global batch_job
    # hack to process batch jobs:
    batch_job = os.getenv('GRASS_BATCH_JOB')
    if batch_job:
        # defined, but ...
        if not os.access(batch_job, os.F_OK):
          # wrong file
          fatal(_("Job file '%s' has been defined in "
                  "the 'GRASS_BATCH_JOB' variable but not found. Exiting.\n\n"
                  "Use 'unset GRASS_BATCH_JOB' to disable batch job processing.") % batch_job)
        elif not os.access(batch_job, os.X_OK):
            # right file, but ...
            fatal(_("Change file permission to 'executable' for '%s'") % batch_job)
        else:
            message(_("Executing '%s' ...") % batch_job)
            grass_gui = "text"
            shell = batch_job
            bj = Popen(shell, shell=True)
            bj.wait()
            message(_("Execution of '%s' finished.") % batch_job)


def start_gui():
    # Start the chosen GUI but ignore text
    if grass_debug:
        message(_("GRASS GUI should be <%s>") % grass_gui)

    # Check for gui interface
    if grass_gui == "wxpython":
        Popen([os.getenv('GRASS_PYTHON'), gfile(wxpython_base, "wxgui.py")])


def clear_screen():
    if windows:
        pass
    # TODO: uncomment when PDCurses works.
    #   cls
    else:
        if not os.getenv('GRASS_BATCH_JOB') and not grass_debug and not exit_grass:
            call(["tput", "clear"])


def show_banner():
    sys.stderr.write(r"""
          __________  ___   __________    _______________
         / ____/ __ \/   | / ___/ ___/   / ____/  _/ ___/
        / / __/ /_/ / /| | \__ \\_  \   / / __ / / \__ \ 
       / /_/ / _, _/ ___ |___/ /__/ /  / /_/ // / ___/ / 
       \____/_/ |_/_/  |_/____/____/   \____/___//____/  

""")


def say_hello():
    sys.stderr.write(_("Welcome to GRASS GIS %s") % grass_version)
    if grass_version.endswith('svn'):
        try:
            filerev = open(os.path.join(gisbase, 'etc', 'VERSIONNUMBER'))
            linerev = filerev.readline().rstrip('\n')
            filerev.close()
            
            revision = linerev.split(' ')[1]
            sys.stderr.write(' (' + revision + ')')
        except:
            pass
    
def show_info():
    sys.stderr.write(
r"""
%-41shttp://grass.osgeo.org
%-41s%s (%s)
%-41sg.manual -i
%-41sg.version -c
""" % (_("GRASS GIS homepage:"),
       _("This version running through:"),
       shellname, os.getenv('SHELL'),
       _("Help is available with the command:"),
       _("See the licence terms with:")))
    
    if grass_gui == 'wxpython':
        message("%-41sg.gui wxpython" % _("If required, restart the GUI with:"))
    else:
        message("%-41sg.gui %s" % (_("Start the GUI with:"), default_gui))
    
    message("%-41sexit" % _("When ready to quit enter:"))
    message("")


def csh_startup():
    global exit_val

    userhome = os.getenv('HOME')      # save original home
    home = location
    os.environ['HOME'] = home

    cshrc = os.path.join(home, ".cshrc")
    tcshrc = os.path.join(home, ".tcshrc")
    try_remove(cshrc)
    try_remove(tcshrc)

    f = open(cshrc, 'w')
    f.write("set home = %s\n" % userhome)
    f.write("set history = 3000 savehist = 3000  noclobber ignoreeof\n")
    f.write("set histfile = %s\n" % os.path.join(os.getenv('HOME'),
                                                 ".history"))

    f.write("set prompt = '\\\n")
    f.write("Mapset <%s> in Location <%s> \\\n" % (mapset, location_name))
    f.write("GRASS GIS %s > '\n" % grass_version)
    f.write("set BOGUS=``;unset BOGUS\n")

    path = os.path.join(userhome, ".grass.cshrc") # left for backward compatibility
    if os.access(path, os.R_OK):
        f.write(readfile(path) + '\n')
    if os.access(grass_env_file, os.R_OK):
        f.write(readfile(grass_env_file) + '\n')

    mail_re = re.compile(r"^ *set  *mail *= *")

    for filename in [".cshrc", ".tcshrc", ".login"]:
        path = os.path.join(userhome, filename)
        if os.access(path, os.R_OK):
            s = readfile(path)
            lines = s.splitlines()
            for l in lines:
                if mail_re.match(l):
                    f.write(l)

    path = os.getenv('PATH').split(':')
    f.write("set path = ( %s ) \n" % ' '.join(path))

    f.close()
    writefile(tcshrc, readfile(cshrc))

    exit_val = call([gfile("etc", "run"), os.getenv('SHELL')])

    os.environ['HOME'] = userhome


def bash_startup():
    global exit_val

    # save command history in mapset dir and remember more
    os.environ['HISTFILE'] = os.path.join(location, ".bash_history")
    if not os.getenv('HISTSIZE') and not os.getenv('HISTFILESIZE'):
        os.environ['HISTSIZE'] = "3000"

    # instead of changing $HOME, start bash with: --rcfile "$LOCATION/.bashrc" ?
    #   if so, must care be taken to explicity call .grass.bashrc et al for
    #   non-interactive bash batch jobs?
    userhome = os.getenv('HOME')      # save original home
    home = location                   # save .bashrc in $LOCATION
    os.environ['HOME'] = home

    bashrc = os.path.join(home, ".bashrc")
    try_remove(bashrc)

    f = open(bashrc, 'w')
    f.write("test -r ~/.alias && . ~/.alias\n")
    if os.getenv('ISISROOT'):
        f.write("PS1='ISIS-GRASS %s (%s):\w > '\n" % (grass_version, location_name))
    else:
        f.write("PS1='GRASS %s (%s):\w > '\n" % (grass_version, location_name))
    
    f.write("""grass_prompt() {
	LOCATION="`g.gisenv get=GISDBASE,LOCATION_NAME,MAPSET separator='/'`"
	if test -d "$LOCATION/grid3/G3D_MASK" && test -f "$LOCATION/cell/MASK" ; then
		echo [%s]
	elif test -f "$LOCATION/cell/MASK" ; then
		echo [%s]
	elif test -d "$LOCATION/grid3/G3D_MASK" ; then
		echo [%s]
	fi
}
PROMPT_COMMAND=grass_prompt\n""" % (_("2D and 3D raster MASKs present"),
                                    _("Raster MASK present"),
                                    _("3D raster MASK present")))

    # read environmental variables
    path = os.path.join(userhome, ".grass.bashrc") # left for backward compatibility
    if os.access(path, os.R_OK):
        f.write(readfile(path) + '\n')
    for env in os.environ.keys():
        if env.startswith('GRASS'):
            val = os.environ[env]
            if ' ' in val:
                val = '"%s"' % val
            f.write('export %s=%s\n' % (env, val))
    ### Replaced by code above (do not override already set up environment variables)
    ###    if os.access(grass_env_file, os.R_OK):
    ###        f.write(readfile(grass_env_file) + '\n')

    f.write("export PATH=\"%s\"\n" % os.getenv('PATH'))
    f.write("export HOME=\"%s\"\n" % userhome) # restore user home path

    f.close()

    exit_val = call([gfile("etc", "run"), os.getenv('SHELL')])

    os.environ['HOME'] = userhome


def default_startup():
    global exit_val

    if windows:
        os.environ['PS1'] = "GRASS %s> " % (grass_version)
        # "$ETC/run" doesn't work at all???
        exit_val = subprocess.call([os.getenv('SHELL')])
        cleanup_dir(os.path.join(location, ".tmp"))  # remove GUI session files from .tmp
    else:
        os.environ['PS1'] = "GRASS %s (%s):\w > " % (grass_version, location_name)
        exit_val = call([gfile("etc", "run"), os.getenv('SHELL')])

    if exit_val != 0:
        fatal(_("Failed to start shell '%s'") % os.getenv('SHELL'))


def done_message():
    if batch_job and os.access(batch_job, os.X_OK):
        message(_("Batch job '%s' (defined in GRASS_BATCH_JOB variable) was executed.") % batch_job)
        message(_("Goodbye from GRASS GIS"))
        sys.exit(exit_val)
    else:
        message(_("Done."))
        message("")
        message(_("Goodbye from GRASS GIS"))
        message("")


def clean_temp():
    message(_("Cleaning up temporary files..."))
    nul = open(os.devnull, 'w')
    call([gfile("etc", "clean_temp")], stdout=nul, stderr=nul)
    nul.close()


def grep(string,list):
    expr = re.compile(string)
    return [elem for elem in list if expr.match(elem)]


def print_params():
    plat = gfile(gisbase, 'include', 'Make', 'Platform.make')
    fileplat = open(plat)
    linesplat = fileplat.readlines()
    fileplat.close()

    params = sys.argv[2:]
    if not params:
        params = ['arch', 'build', 'compiler', 'path', 'revision']
    
    for arg in params:
        if arg == 'path':
            sys.stdout.write("%s\n" % gisbase)
        elif arg == 'arch':
            val = grep('ARCH',linesplat)
            sys.stdout.write("%s\n" % val[0].split('=')[1].strip())
        elif arg == 'build':
            build = os.path.join(gisbase,'include','grass','confparms.h')
            filebuild = open(build)
            val = filebuild.readline()
            filebuild.close()
            sys.stdout.write("%s\n" % val.strip().strip('"').strip())
        elif arg == 'compiler':
            val = grep('CC',linesplat)
            sys.stdout.write("%s\n" % val[0].split('=')[1].strip())
        elif arg == 'revision':
            rev = os.path.join(gisbase,'include','grass','gis.h')
            filerev = open(rev)
            linesrev = filerev.readlines()
            val = grep('#define GIS_H_VERSION', linesrev)
            filerev.close()
            sys.stdout.write("%s\n" % val[0].split(':')[1].rstrip('$"\n').strip())
        else:
            message(_("Parameter <%s> not supported") % arg)


def get_username():
    global user
    if windows:
        user = os.getenv('USERNAME')
        if not user:
            user = "user_name"
    else:
        user = os.getenv('USER')
        if not user:
            user = os.getenv('LOGNAME')
        if not user:
            try:
                p = Popen(['whoami'], stdout = subprocess.PIPE)
                s = p.stdout.read()
                p.wait()
                user = s.strip()
            except:
                pass
        if not user:
            user = "user_%d" % os.getuid()


def parse_cmdline():
    global args, grass_gui, create_new, exit_grass
    args = []
    for i in sys.argv[1:]:
        # Check if the user asked for the version
        if i in ["-v", "--version"]:
            message("GRASS GIS %s" % grass_version)
            message('\n' + readfile(gfile("etc", "license")))
            sys.exit()
        # Check if the user asked for help
        elif i in ["help", "-h", "-help", "--help"]:
            help_message()
            sys.exit()
        # Check if the -text flag was given
        elif i in ["-text", "--text"]:
            grass_gui = 'text'
        # Check if the -gtext flag was given
        elif i in ["-gtext", "--gtext"]:
            grass_gui = 'gtext'
        # Check if the -gui flag was given
        elif i in ["-gui", "--gui"]:
            grass_gui = default_gui
        # Check if the -wxpython flag was given
        elif i in ["-wxpython", "-wx", "--wxpython", "--wx"]:
            grass_gui = 'wxpython'
        # Check if the user wants to create a new mapset
        elif i == "-c":
            create_new = True
        elif i == "-e":
            exit_grass = True
        elif i == "--config":
            print_params()
            sys.exit()
        else:
            args.append(i)

### MAIN script starts here

# Get the system name
windows = sys.platform == 'win32'
cygwin = "cygwin" in sys.platform
macosx = "darwin" in sys.platform

### commented-out: broken winGRASS 
# if 'GISBASE' in os.environ:
#     sys.exit(_("ERROR: GRASS GIS is already running "
#                "(environmental variable GISBASE found)"))

# Set GISBASE
os.environ['GISBASE'] = gisbase

# set HOME
if windows and not os.getenv('HOME'):
    os.environ['HOME'] = os.path.join(os.getenv('HOMEDRIVE'),
                                      os.getenv('HOMEPATH'))

# set SHELL
if windows:
    if os.getenv('GRASS_SH'):
        os.environ['SHELL'] = os.getenv('GRASS_SH')
    if not os.getenv('SHELL'):
        os.environ['SHELL'] = os.getenv('COMSPEC', 'cmd.exe')

atexit.register(cleanup)

# Set default GUI
default_gui = "wxpython"

# the following is only meant to be an internal variable for debugging this
# script. use 'g.gisenv set="DEBUG=[0-5]"' to turn GRASS debug mode on properly
grass_debug = os.getenv('GRASS_DEBUG')

# Set GRASS version number for R interface etc (must be an env_var for MS-Windows)
os.environ['GRASS_VERSION'] = grass_version

# Set the GIS_LOCK variable to current process id
gis_lock = str(os.getpid())
os.environ['GIS_LOCK'] = gis_lock

if not os.path.exists(grass_config_dir):
    os.mkdir(grass_config_dir)

# Set the global grassrc file
batch_job = os.getenv('GRASS_BATCH_JOB')
if batch_job:
    gisrcrc = os.path.join(grass_config_dir, "rc.%s" % platform.node())
    if not os.access(gisrcrc, os.R_OK):
        gisrcrc = os.path.join(grass_config_dir, "rc")
else:
    gisrcrc = os.path.join(grass_config_dir, "rc")

# Set the username and working directory
get_username()

# Parse the command-line options
parse_cmdline()

if exit_grass and not create_new:
    fatal(_("Flag -e required also flag -c"))
# Set language
# This has to be called before any _() function call!
# Subsequent functions are using _() calls and
# thus must be called only after Language has been set.
set_language()

# Create the temporary directory and session grassrc file
create_tmp()

# Create the session grassrc file
create_gisrc()

# Set shell (needs to be called before load_env())
check_shell()

# Load environmental variables from the file
load_env()

# Ensure GUI is set
read_gui()

# Set PATH, PYTHONPATH
set_paths()

# Set LD_LIBRARY_PATH (etc) to find GRASS shared libraries
path_prepend(gfile("lib"), ld_library_path_var)

# Set GRASS_PAGER, GRASS_PYTHON, GRASS_GNUPLOT, GRASS_PROJSHARE
set_defaults()

# Set GRASS_HTML_BROWSER
set_browser()

#predefine monitor size for certain architectures
if os.getenv('HOSTTYPE') == 'arm':
    # small monitor on ARM (iPAQ, zaurus... etc)
    os.environ['GRASS_RENDER_HEIGHT'] = "320"
    os.environ['GRASS_RENDER_WIDTH'] = "240"

# First time user - GISRC is defined in the GRASS script
if not os.access(gisrc, os.F_OK):
    if grass_gui == 'text' and len(args) == 0:
        fatal(_("Unable to start GRASS. You can:\n"
                " - Launch GRASS with '-gui' switch (`grass70 -gui`)\n"
                " - Create manually GISRC file (%s)\n"
                " - Launch GRASS with path to "
                "the location/mapset as an argument (`grass70 /path/to/location/mapset`)") % gisrcrc)
    create_initial_gisrc()
else:
    clean_temp()

if create_new:
    message(_("Creating new GRASS GIS location/mapset..."))
else:
    message(_("Starting GRASS GIS..."))

# Check that the GUI works
check_gui()

# Parsing argument to get LOCATION
if not args:
    # Try interactive startup
    location = None
else:
    if create_new:
        if len(args) > 1:
            non_interactive(args[1], args[0])
        else:
            non_interactive(args[0])
    else:
        non_interactive(args[0])

# User selects LOCATION and MAPSET if not set
set_data()

# Set GISDBASE, LOCATION_NAME, MAPSET, LOCATION from $GISRC
load_gisrc()

# Check .gislock file
check_lock()

# build user fontcap if specified but not present
make_fontcap()

# predefine default driver if DB connection not defined
#  is this really needed?? Modules should call this when/if required.
if not os.access(os.path.join(location, "VAR"), os.F_OK):
    call(['db.connect', '-c', '--quiet'])

check_batch_job()

if not batch_job and not exit_grass:       
    start_gui()

clear_screen()

# Display the version and license info
if batch_job:
    grass_gui = 'text'
    clear_screen()
    clean_temp()
    try_remove(lockfile)
    sys.exit(0)
elif exit_grass:
    clean_temp()
    try_remove(lockfile)
    sys.exit(0)
else:
    show_banner()
    say_hello()
    show_info()
    if grass_gui == "wxpython":
        message(_("Launching <%s> GUI in the background, please wait...") % grass_gui)

if sh in ['csh', 'tcsh']:
    csh_startup()
elif sh in ['bash', 'msh', 'cygwin']:
    bash_startup()
else:
    default_startup()

clear_screen()

clean_env()
clean_temp()

try_remove(lockfile)

# Save GISRC
s = readfile(gisrc)
writefile(gisrcrc, s)

cleanup()

# After this point no more grass modules may be called

done_message()
