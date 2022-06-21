#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#

import time
import argparse
import json
import sys
from ringtail import DBManagerSQLite
from ringtail import Outputter
import logging
import traceback


def cmdline_parser(defaults={}):

    conf_parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False,
    )
    conf_parser.add_argument(
        "-c",
        "--config",
        help="specify a JSON-format file containing the option definitions. NOTE: options defined here will be overridden by command line options!",
    )
    confargs, remaining_argv = conf_parser.parse_known_args()

    defaults = {
        "positive_selection": None,
        "negative_selection": None,
        "bookmark_name": ["passing_results"],
        "log": "selective_log.txt",
        "save_bookmark": None,
        "export_csv": None,
    }

    config = json.loads(
        json.dumps(defaults)
    )  # using dict -> str -> dict as a safe copy method

    if confargs.config is not None:
        logging.info("Reading options from config file")
        with open(confargs.config) as f:
            c = json.load(f)
            config.update(c)

    parser = argparse.ArgumentParser(
        usage="Please see GitHub for full usage details.",
        description="Script for filtering unique passing ligands across multiple virtual screenings. Takes databases created and filtered with run_ringtail.py.",
        epilog="""

        REQUIRED PACKAGES
                Requires RDkit, SciPy, Meeko.\n

        AUTHOR
                Written by Althea Hansel-Harris. Based on code by Stefano Forli, PhD, Andreas Tillack, PhD, and Diogo Santos-Martins, PhD.\n

        REPORTING BUGS
                Please report bugs to:
                AutoDock mailing list   http://autodock.scripps.edu/mailing_list\n

        COPYRIGHT
                Copyright (C) 2022 Stefano Forli Laboratory, Center for Computational Structural Biology,
                             The Scripps Research Institute.
                GNU GPL version 3 or later <http://gnu.org/licenses/gpl.html>
        """,
        exit_on_error=False,
    )

    parser.add_argument(
        "--wanted",
        "-w",
        help="Database for which ligands MUST be included in bookmark",
        nargs="+",
        type=str,
        metavar="[DATABASE_FILE].db",
    )
    parser.add_argument(
        "--unwanted",
        "-n",
        help="Database for which ligands MUST NOT be included in bookmark",
        nargs="+",
        type=str,
        metavar="[DATABASE_FILE].db",
        action="store",
    )
    parser.add_argument(
        "--bookmark_name",
        "-sn",
        help="Name of filter bookmark that ligands should be compared accross. Must be present in all databases",
        type=str,
        metavar="STRING",
        action="store",
        nargs="+",
    )
    parser.add_argument(
        "--log",
        "-l",
        help="Name for log file of passing ligands and data",
        type=str,
        metavar="[LOG FILE].txt",
        action="store",
    )
    parser.add_argument(
        "--save_bookmark",
        "-s",
        help="Name for bookmark of passing cross-reference ligands to be saved as in first database given with --wanted",
        type=str,
        metavar="STRING",
        action="store",
    )
    parser.add_argument(
        "--export_csv",
        "-x",
        help="Save final cross-referenced bookmark as csv. Saved as [save_bookmark].csv or 'crossref.csv' if --save_bookmark not used.",
        action="store_true",
    )
    parser.add_argument(
        "--verbose", "-v", help="Verbose output while running", action="store_true"
    )

    parser.set_defaults(**config)
    args = parser.parse_args(remaining_argv)

    # check that name was given with save_bookmark
    if args.save_bookmark == "":
        raise IOError(
            "--save_bookmark option used but no bookmark name given. Must specify bookmark name as string."
        )

    return args


if __name__ == "__main__":
    time0 = time.perf_counter()

    try:
        args = cmdline_parser()

        # make sure we have a positive db and at least one other database
        if args.wanted is None:
            raise IOError("No wanted database found. Must specify an included database.")
        else:
            db_count = len(args.wanted)
            if args.unwanted is not None:
                db_count += len(args.unwanted)
            if db_count < 2:
                raise IOError("Must specify at least two databases for comparison.")

        # set logging level
        debug = True
        if debug:
            level = logging.DEBUG
        elif args.verbose:
            level = logging.INFO
        else:
            level = logging.WARNING
        logging.basicConfig(level=level)

        wanted_dbs = args.wanted
        unwanted_dbs = args.unwanted

        ref_db = wanted_dbs[0]
        wanted_dbs = wanted_dbs[1:]

        previous_bookmarkname = args.bookmark_name[0]
        original_bookmark_name = args.bookmark_name[0]
        # make list of bookmark names for compared databases
        bookmark_list = []
        if len(args.bookmark_name) > 1:
            bookmark_list = args.bookmark_name[1:]
        else:
            for db in wanted_dbs:
                bookmark_list.append(original_bookmark_name)
            if unwanted_dbs is not None:
                for db in unwanted_dbs:
                    bookmark_list.append(original_bookmark_name)

        logging.info("Starting cross-reference process")

        dbman = DBManagerSQLite(ref_db)

        last_db = None
        for idx, db in enumerate(wanted_dbs):
            logging.info(f"cross-referencing {db}")
            previous_bookmarkname, number_passing_ligands = dbman.crossref_filter(
                db, previous_bookmarkname, bookmark_list[idx], selection_type="+", old_db=last_db
            )
            last_db = db

        if unwanted_dbs is not None:
            for idx, db in enumerate(unwanted_dbs):
                logging.info(f"cross-referencing {db}")
                previous_bookmarkname, number_passing_ligands = dbman.crossref_filter(
                    db, previous_bookmarkname, bookmark_list[idx], selection_type="-", old_db=last_db
                )
                last_db = db

        logging.info("Writing log")
        output_manager = Outputter(args.log)
        if args.save_bookmark is not None:
            output_manager.write_results_bookmark_to_log(args.save_bookmark)
        output_manager.log_num_passing_ligands(number_passing_ligands)
        final_bookmark = dbman.fetch_view(previous_bookmarkname)
        output_manager.write_log(final_bookmark)

        if args.save_bookmark is not None:
            dbman.save_temp_bookmark(args.save_bookmark, original_bookmark_name, args.wanted, args.unwanted)

        if args.export_csv:
            if args.save_bookmark is not None:
                csv_name = args.save_bookmark + ".csv"
            else:
                csv_name = "crossref.csv"
            output_manager.export_csv(previous_bookmarkname, csv_name, True)

    except Exception as e:
        tb = traceback.format_exc()
        logging.debug(tb)
        logging.critical(e)
        sys.exit(1)

    finally:
        try:
            dbman.close_connection()
        except NameError:
            pass
