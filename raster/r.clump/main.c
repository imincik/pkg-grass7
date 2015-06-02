
/****************************************************************************
 *
 * MODULE:       r.clump
 *
 * AUTHOR(S):    Michael Shapiro - CERL
 *               Markus Metz
 *
 * PURPOSE:      Recategorizes data in a raster map layer by grouping cells
 *               that form physically discrete areas into unique categories.
 *
 * COPYRIGHT:    (C) 2006-2014 by the GRASS Development Team
 *
 *               This program is free software under the GNU General Public
 *               License (>=v2). Read the file COPYING that comes with GRASS
 *               for details.
 *
 ***************************************************************************/

#include <stdlib.h>
#include <string.h>
#include <grass/gis.h>
#include <grass/raster.h>
#include <grass/glocale.h>
#include "local_proto.h"

int main(int argc, char *argv[])
{
    struct Colors colr;
    struct Range range;
    struct History hist;
    CELL min, max;
    int range_return, n_clumps;
    int in_fd, out_fd;
    char title[512];
    char name[GNAME_MAX];
    char *OUTPUT;
    char *INPUT;
    struct GModule *module;
    struct Option *opt_in;
    struct Option *opt_out;
    struct Option *opt_title;
    struct Flag *flag_diag;
    struct Flag *flag_print;

    G_gisinit(argv[0]);

    /* Define the different options */

    module = G_define_module();
    G_add_keyword(_("raster"));
    G_add_keyword(_("statistics"));
    G_add_keyword(_("reclass"));
    G_add_keyword(_("clumps"));
    module->description =
	_("Recategorizes data in a raster map by grouping cells "
	  "that form physically discrete areas into unique categories.");

    opt_in = G_define_standard_option(G_OPT_R_INPUT);

    opt_out = G_define_standard_option(G_OPT_R_OUTPUT);
    opt_out->required = NO;

    opt_title = G_define_option();
    opt_title->key = "title";
    opt_title->type = TYPE_STRING;
    opt_title->required = NO;
    opt_title->description = _("Title for output raster map");

    flag_diag = G_define_flag();
    flag_diag->key = 'd';
    flag_diag->label = _("Clump also diagonal cells");
    flag_diag->description = _("Clumps are also traced along diagonal neighboring cells");

    flag_print = G_define_flag();
    flag_print->key = 'g';
    flag_print->label = _("Print only the number of clumps in shell script style");

    /* parse options */
    if (G_parser(argc, argv))
	exit(EXIT_FAILURE);

    INPUT = opt_in->answer;
    strcpy(name, INPUT);

    in_fd = Rast_open_old(name, "");

    if (!flag_print->answer) {
	OUTPUT = opt_out->answer;
	out_fd = Rast_open_c_new(OUTPUT);
    }

    clump(in_fd, out_fd, flag_diag->answer, flag_print->answer);

    Rast_close(in_fd);

    if (!flag_print->answer) {
	Rast_close(out_fd);

	G_debug(1, "Creating support files...");

	/* build title */
	if (opt_title->answer != NULL)
	    strcpy(title, opt_title->answer);
	else
	    sprintf(title, "clump of <%s@%s>", name, G_mapset());
	Rast_put_cell_title(OUTPUT, title);

	/* colors */
	range_return = Rast_read_range(OUTPUT, G_mapset(), &range);
	Rast_get_range_min_max(&range, &min, &max);
	Rast_make_random_colors(&colr, min, max);
	Rast_write_colors(OUTPUT, G_mapset(), &colr);

	/* history */
	Rast_short_history(OUTPUT, "raster", &hist);
	Rast_set_history(&hist, HIST_DATSRC_1, INPUT);
	Rast_command_history(&hist);
	Rast_write_history(OUTPUT, &hist);

	n_clumps = range_return == 2 ? 0 : range.max;
	G_done_msg(_n("%d clump.", "%d clumps.", n_clumps), n_clumps);
    }

    exit(EXIT_SUCCESS);
}
