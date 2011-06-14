## Copyright (C) 2011 Aldebaran Robotics

"""Uninstall a toolchain

"""

import logging

import qibuild
import qitoolchain

import ConfigParser

LOGGER = logging.getLogger(__name__)

def configure_parser(parser):
    """Configure parser for this action """
    qibuild.qiworktree.work_tree_parser(parser)
    parser.add_argument("name",
        help="The name of the toolchain to remove")

def do(args):
    """ Main entry point  """
    tc_name = args.name
    LOGGER.info("Removing toolchain %s", tc_name)

    LOGGER.info("Removing cache ...")
    tc_cache_path = qitoolchain.get_tc_cache(args.name)
    qibuild.sh.rm(tc_cache_path)

    LOGGER.info("Removing packages ...")
    tc_path = qitoolchain.get_tc_path(tc_name)
    qibuild.sh.rm(tc_path)

    LOGGER.info("Updating configuration ...")
    cfg_path = qitoolchain.get_tc_config_path()

    tc_names = qitoolchain.get_toolchain_names()
    tc_names = [x for x in tc_names if x != tc_name]

    tc_section = 'toolchain "%s"' % tc_name

    config = ConfigParser.RawConfigParser()
    config.read(cfg_path)

    config.remove_section(tc_section)
    with open(cfg_path, "w") as fp:
        config.write(fp)

    LOGGER.info("Done removing toolchain %s", tc_name)