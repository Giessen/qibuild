## Copyright (c) 2012, 2013 Aldebaran Robotics. All rights reserved.
## Use of this source code is governed by a BSD-style license that can be
## found in the COPYING file.

""" Topological sort

"""

__all__ = [ "DagError", "assert_dag", "topological_sort" ]

class DagError(Exception):
    """ Dag Exception """
    def __init__(self, node, parent, result):
        Exception.__init__(self)
        self.node   = node
        self.parent = parent
        self.result = result

    def __str__(self):
        return "Circular dependency error: Starting from '%s', node '%s' depends on '%s', complete path %s" \
               % (self.node, self.parent, self.node, self.result)

def assert_dag(data):
    """ Check if data is a dag
    >>> assert_dag({
    ...   'a' : ( 'g', 'b', 'c', 'd' ),
    ...   'b' : ( 'e', 'c' ),
    ...   'e' : ( 'g', 'c' )})


    >>> assert_dag({
    ...   'a' : ( 'g', 'b', 'c', 'd' ),
    ...   'b' : ( 'e', 'c' ),
    ...   'e' : ( 'e', 'c' )})
    Traceback (most recent call last):
        ...
    DagError: Circular dependency error: Starting from 'e', node 'e' depends on 'e', complete path []
    """

    for node, _ in data.items():
        _topological_sort(data, node, node, True)

def topological_sort(data, heads):
    """ Topological sort

    data should be a dictionary like that (it's a dag):
    {
      'a' : ( 'b', 'c', 'd' ),
      'b' : ( 'e', 'c' )
    }

    heads are the top of the dag, the result will include all specified heads and their deps

    This function return a list. Head will be the last element.

    Warning: this sort always find a solution even is data is not a dag!!
             If a depend on b and b depend on a, the solution is [ a, b ].
             This is ok in our case but could be a problem in other situation.
             (you know what? try to use the result you will see if it work!).

    >>> topological_sort({
    ...   'head'         : ['telepathe', 'opennao-tools', 'naoqi'],
    ...   'toolchain'    : [],
    ...   'python-pc'    : ['toolchain'],
    ...   'telepathe'    : ['naoqi'],
    ...   'qt-pc'        : ['toolchain'],
    ...   'opennao-tools': ['toolchain'],
    ...   'naoqi'        : ['qt-pc', 'python-pc', 'streamer', 'toolchain']}, 'head' )
    ['toolchain', 'qt-pc', 'python-pc', 'streamer', 'naoqi', 'telepathe', 'opennao-tools', 'head']

    >>> topological_sort({
    ...   'a' : ( 'b', 'c', 'd' ),
    ...   'b' : ( 'e', 'c' )}, 'a')
    ['e', 'c', 'b', 'd', 'a']

    >>> topological_sort({
    ...   'a' : ( 'g', 'b', 'c', 'd' ),
    ...   'b' : ( 'e', 'c' ),
    ...   'e' : ( 'e', 'c' )}, 'a')
    ['g', 'c', 'e', 'b', 'd', 'a']

    >>> topological_sort({
    ...   'a' : ( 'g', 'b', 'c', 'd' ),
    ...   'b' : ( 'e', 'c' ),
    ...   'e' : ( 'g', 'c' )}, 'a')
    ['g', 'c', 'e', 'b', 'd', 'a']

    >>> topological_sort({
    ...   'a' : ( 'b' ),
    ...   'b' : ( 'a' ),
    ... }, 'a')
    ['b', 'a']

    >>> topological_sort({
    ...   'a' : ( 'g', 'b', 'c', 'd' ),
    ...   'b' : ( 'e', 'c' ),
    ...   'q' : ( 'u', 'i' ),
    ...   'i' : ( 'y', 'o' ),
    ...   'e' : ( 'g', 'c' )}, 'a')
    ['g', 'c', 'e', 'b', 'd', 'a']

    >>> topological_sort({
    ...   'a' : ( 'g', 'b', 'c', 'd' ),
    ...   'b' : ( 'e', 'c' ),
    ...   'q' : ( 'u', 'i' ),
    ...   'i' : ( 'y', 'o' ),
    ...   'e' : ( 'g', 'c' )}, [ 'a', 'q' ])
    ['g', 'c', 'e', 'b', 'd', 'a', 'u', 'y', 'o', 'i', 'q']
    """
    if isinstance(heads, list):
        data['internalfakehead'] = heads
        head = 'internalfakehead'
        result =  _topological_sort(data, head, head)
        return [ x for x in result if x != 'internalfakehead' ]
    else:
        head = heads
        return _topological_sort(data, head, head)

def _topological_sort(data, head, top_node, raise_exception = False, result = None, visited = None):
    """ Internal function
    """
    if not result:
        result = []
    if not visited:
        visited = []
    deps = data.get(head, list())
    if head in visited:
        if head == top_node and raise_exception:
            raise DagError(head, head, result)
        return result
    visited.append(head)
    for i in deps:
        try:
            result.index(i)
        except ValueError:
            #the item does not exist
            result = _topological_sort(data, i, top_node, raise_exception, result, visited)
    result.append(head)
    return result



class DependenciesSolver:
    """This class is able to resolve dependencies between projects,
    and between projects and packages

    """
    def __init__(self):
        self.projects = list()
        self.packages = list()

    def get_projects(self, projects, dep_types=None):
        """Given a list of projects, sort them in the correct order

        :param dep_types: is a list of dependency types
            (``["build"]``, ``["runtime", "test"]``, etc.)
        :return: a list of projects

        """
        if not dep_types:
            dep_types = ["build", "runtime"]
        else:
            dep_types = dep_types

        project_names = [p.name for p in self.projects]

        # Assert that all the names are known projects:
        for name in names:
            if name not in project_names:
                raise Exception("Unknown project: %s" % name)

        to_sort = dict()
        for project in self.projects:
            deps = set()
            if "runtime" in dep_types:
                deps = deps.union(project.depends)
            if "build" in dep_types:
                deps = deps.union(project.rdepends)

        sorted_names = topological_sort(to_sort, names)
        return sorted_names

    def get_packages(self, names, dep_types=None):
        """Given a list of names, try to sort them in the correct order.

        :param dep_types: is a list of dependency types
            (``["build"]``, ``["runtime", "test"]``, etc.)
        :return: a list of projects
        """
        if not dep_types:
            dep_types = ["build", "runtime"]
        else:
            dep_types = dep_types

        to_sort = dict()
        for project in self.projects:
            deps = set()
            if "runtime" in dep_types:
                deps = deps.union(project.depends)
            if "build" in dep_types:
                deps = deps.union(project.rdepends)

        sorted_names = topological_sort(to_sort, names)

        for name in sorted_names:
            if name in package_names:
                res.append(name)

        return name

if __name__ == "__main__":
    import doctest
    doctest.testmod()
