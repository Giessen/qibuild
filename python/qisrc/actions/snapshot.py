## Copyright (c) 2012-2014 Aldebaran Robotics. All rights reserved.
## Use of this source code is governed by a BSD-style license that can be
## found in the COPYING file.

""" Generate a snapshot of all the git projects """

from qisys import ui

import qisys

import qisrc.git
import qisrc.snapshot

def configure_parser(parser):
    """Configure parser for this action."""
    qisys.parsers.worktree_parser(parser)
    qisys.parsers.project_parser(parser)
    group = parser.add_argument_group("qisrc snapshot options")
    group.add_argument("snapshot_path", help="Path to the output snapshot file. " +
        "Use `qisrc reset --force --snapshot snapshot_path` to load a snapshot" )


def do(args):
    """Main entry point."""
    git_worktree = qisrc.parsers.get_git_worktree(args)
    ui.info(ui.green, "Current worktree:", ui.reset, ui.bold, git_worktree.root)
    snapshot_path = args.snapshot_path
    qisrc.snapshot.generate_snapshot(git_worktree, snapshot_path)
