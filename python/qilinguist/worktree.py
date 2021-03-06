import os


import qisys.worktree
import qisys.qixml


class LinguistWorkTree(qisys.worktree.WorkTreeObserver):
    def __init__(self, worktree):
        self.worktree = worktree
        self.root = worktree.root
        self.linguist_projects = list()
        self._load_linguist_projects()
        worktree.register(self)

    def _load_linguist_projects(self):
        self.linguist_projects = list()
        for worktree_project in self.worktree.projects:
            linguist_project = new_linguist_project(self, worktree_project)
            if linguist_project:
                self.check_unique_name(linguist_project)
                self.linguist_projects.append(linguist_project)

    def on_project_added(self, project):
        """ Called when a new project has been registered """
        self._load_linguist_projects()

    def on_project_removed(self, project):
        """ Called when a build project has been removed """
        self._load_linguist_projects()

    def on_project_moved(self, project):
        """ Called when a build project has been moved """
        self._load_linguist_projects()

    def get_linguist_project(self, name, raises=False):
        for project in self.linguist_projects:
            if project.name == name:
                return project
        if raises:
            raise Exception("No such linguist project: %s" % name)
        else:
            return None

    def check_unique_name(self, new_project):
        project_with_same_name = self.get_linguist_project(new_project.name,
                                                           raises=False)
        if project_with_same_name:
            raise Exception("""\
Found two projects with the same name ({0})
In:
* {1}
* {2}
""".format(new_project.name,
               project_with_same_name.path,
               new_project.path))


def new_linguist_project(linguist_worktree, project):
    if not os.path.exists(project.qiproject_xml):
        return None
    tree = qisys.qixml.read(project.qiproject_xml)
    root = tree.getroot()
    if root.get("version") != "3":
        return None
    translate_elem = root.find("translate")
    if translate_elem is None:
        return None
    name = translate_elem.get("name")
    if not name:
        raise BadProjectConfig(project.qiproject_xml,
                               "Expecting a 'name' attribute")

    domain = translate_elem.get("domain")
    if not domain:
        domain = name

    linguas = translate_elem.get("linguas").split()
    if not linguas:
        linguas = ["en_US"]

    tr_framework = translate_elem.get("tr")
    if not tr_framework:
        raise BadProjectConfig(project.qiproject_xml,
                               "Expecting a 'tr' attribute")

    if tr_framework not in ["linguist", "gettext"]:
        mess = """ \
Unknow translation framework: {}.
Choose between 'linguist' or 'gettext'
"""
        raise BadProjectConfig(mess.format(tr_framework))

    if tr_framework == "linguist":
        from qilinguist.qtlinguist import QtLinguistProject
        new_project =  QtLinguistProject(project, name, domain=domain,
                                         linguas=linguas)
    else:
        from qilinguist.qigettext import GettextProject
        new_project = GettextProject(project, name, domain=domain,
                                     linguas=linguas)
    return new_project

class BadProjectConfig(Exception):
    def __str__(self):
        return """
Incorrect configuration detected for project in {0}
{1}
""".format(*self.args)
