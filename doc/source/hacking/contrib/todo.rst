qibuild TODO
=============

Below you can find a list of tasks that are not worth putting in a bug tracker.

Mostly because they involve some refactoring, or because they would cause
so many changes we are not sure if/when we will tackle them.

Feel free to add your own ideas here.

CMake
-----

qi_stage_lib/qi_use_lib
++++++++++++++++++++++++

* Handle package versions ?
* Use new CMake 2.8.11 features
* avoid using the cache for global variables and use global properties instead

Factorize qi_create_test() and qi_create_perf_test()
+++++++++++++++++++++++++++++++++++++++++++++++++++++

It maybe a good idea to remove the compatibility with
pure cmake tests.

Instead, only use qi_create_test and generate custom
files instead (thus we no longer have to parse cmake-generated
cmake code)

It became easier to write code like this::

  qi_create_test(... NIGHTLY)
  qi_create_test(.... PERF)

Introduce options like ``WITH_TESTS``, ``WITH_PERF_TESTS``
instead of having to deal with ``BUILD_TESTS`` and ``enable_testing()``

Use a build 'prefix'
++++++++++++++++++++

``qibuild`` does lots of black magic so that you can find dependencies and headers paths
from the sources and build dir of your project, without using the "global cmake registry"
or any other tricks.

However:

* this means you can have problems with your headers install rules and not see them
* this also means you cannot easily depdend of a project not using qibuild (even if it uses CMake),
  or a project using autotools

The solution is simple: After building a dependency, install it to ``QI_WOKTREE/root``  and
just set ``CMAKE_INSTALL_PREFIX`` to ``QI_WOKTREE/root``

This will work with any build system, (provided they have correct install rules), and will
force peoploe to have correct install rules.

Make it easier to use 3rd party cmake module
++++++++++++++++++++++++++++++++++++++++++++++


Say you find a `foo-config.cmake` somewhere... If you try to do::

  find_package(FOO)

  qi_create_bin(bar)

  qi_use_lib(bar FOO)

This may or may not work: it depends of what the `foo-config.cmake` does:
`qi_use_lib` , `qi_stage_lib` expects some variables (`FOO_INCLUDE_DIRS`, `FOO_LIBRARIES`) to be
in the cache

It may be cleaner to add a `qi_export` function::

  find_package(FOO)

  # works out of the box if foo follows CMake conventions
  qi_export(foo)


  # can specify alternative variable names (here the case is wrong)
  qi_export(foo
    LIBRARIES ${Foo_LIBRARY}
  )


Command line
------------

* remove `--quiet-commands`

* add group for every action parser, or only dispaly the options
  specific to the given action when using `qibuild <action> --help`

* add a "path" type in argparse so that (on Windows at least) we:

  * always convert to lower case
  * check for forbidden characters

qibuild
-------

* Use 3 components: build, runtime, test (ala maven)

* add --reverse-deps

* `qibuild config` should list the available build profiles

* fix linker problems when using toolchain and third party libraries on mac

* fix XCode support and other "multi-configuration" IDE by having
  two SDK_DIRS (one debug, one release) in the same build dir

* handle custom build dir

* handle custom sdk dir ?

* qibuild deploy: fix gdb config files generation

* always check CMake correctness (find_package(qibuild) *after* project)
  > maybe this could be done in CMake instead ...

* get rid of qibuild test ``--slow``, this makes no sense: the
  list of tests and wether they are nightly or not is managed from cmake

* add qibuild test --failed

* add `qibuild find -z` to look in every build dir

qisrc
-----

* remove ``qisrc snapshot --manifest``

* fix ``qisrc manifest`` API

qitoolchain
-----------

Add metadata in the qitoolchain package format
++++++++++++++++++++++++++++++++++++++++++++++

At the very least ``name``, ``version`` and ``arch``.

Tracking dependencies may be a good idea, too.

This will allow to replace ``qitoolchain add-package foo foo.zip`` with
``qitoolchain add-package foo.zip`` with makes much more sense

Also : use XML for persistent storage of toolchain packages and add override
config files to track the packages the user manually adds or removes

This will solve the bug ``qitoolchain remove-package boost; qitoolchain update`` that
makes boost reappear in the toolchain.


qidoc
-----

* Make it possible to use it without a ``templates`` repository


Python
-------

Port to Python3
+++++++++++++++++

It's the future ! We already removed compatibility with ``Python 2.6``, and
``python3`` is now the default version on most linux distros.

Renames
++++++++

* XMLParser.xml_elem() -> dump()
* XMLParser._write_foo()  -> _dump_foo()

* rewrite qibuild.config using XMLParser

* rename qibuild.config -> qibuild.xml_config ?

* choose between destdir and dest_dir


tests
+++++

* Document ``pytest`` fixtures: we have tons of them, and some of them are
  very magic

* Replace qibuild_action("configure") with a nicer syntax:

  * qibuild_action.call("configure") ?
  * qibuild_action.configure("...") ?

* fix running automatic tests on windows and mac

misc
++++

* parser.get_* functions should be usable with ``**kwargs`` too::

    def get_worktree(args=None, **kwargs):
      options = dict()
      if args:
        options = vars(args[0])
      else:
        options = kwargs

* ``qisrc.parser.get_projects(worktree, args)`` -> ``qisrc.parser.get_projects(args)``
  (just get the worktree from the args)


* replace ``qisys.interact.ask_choice``
  Instead of a ``return_int`` option, use something like:
  ``ask_choice(message, choices, display_fun=None, allow_none=False)``

  ``display_fun`` will be called on each choice to display them
  to the user, returning either an element from the choices
  list, or None if the user did not enter anything and ``allow_none`` is True

* Use same API as ``shutil`` in ``qisys.sh`` and ``qisys.archive``:

  * qisys.command.find -> qisys.command.which

  * qisys.command.archive -> http://docs.python.org/3/library/shutil.html#archiving-operations


qibuild2 leftovers cleanup
++++++++++++++++++++++++++

* remove qitoolchain.Toolchain.get

* remove qitoolchain.remote

* remove qibuild.configstore, use XML for toolchain
  storage

* remove qisrc.git.get_git_projects