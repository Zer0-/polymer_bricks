import os
import re
from shutil import copyfile
from collections import namedtuple
from enum import Enum
from lxml.html import parse, fromstring, tostring
from lxml.etree import ParserError
import html5lib
from bricks.static_manager import path_to_src
import logging

class MissingDependency(Exception):
    pass

all_extensions = ('css', 'js', 'html')
find_extensions = ('html',)
src_attrib_map = {'link': 'href', 'script': 'src'}
ignore = (
    'demo',
    'index',
    'core-popup-menu/metadata',
    'smoke',
    'jquery',
    'highlightjs',
)
name_escape_chars = ('/', '-', '.', '_')
qmark_escape_string = "_and_questionmark"
qmark_regex = "\S+[?]="

depless_template = "{classname}('{typename}', asset=asset_root + '{asset}')"
assign_template = "{varname} = {value}"
component_class_template = """
class {classname}:
    depends_on = [
{deplist}
    ]
    def __init__(self, *args):
        pass
"""
module_topmatter = """from bricks.staticfiles import StaticJs, StaticCss, StaticFile
from polymer_bricks.webcomponent import WebComponent

asset_root='polymer_bricks:polymer_components/components'

"""

class ComponentTypes(Enum):
    css = 1
    js = 2
    html = 3

    def __repr__(self):
        return self.name.capitalize()

typemap = {
    ComponentTypes.css: "StaticCss",
    ComponentTypes.js: "StaticJs",
    ComponentTypes.html: "WebComponent",
}

Component = namedtuple('Component', ['type', 'path', 'inlined'])

def src_external(src):
    return src.startswith('http') or src.startswith('//')

def file_extension(filepath):
    return os.path.splitext(filepath)[1][1:]

def filename(path):
    return os.path.splitext(os.path.basename(path))[0]

def escape_qmarks(bad_html):
    return re.sub(
        qmark_regex,
        lambda x: x.group(0).replace('?', qmark_escape_string),
        bad_html
    )

def unescape_qmarks(escaped_bad_html):
    return re.sub(qmark_escape_string, '?', escaped_bad_html)

def _capitalize(word):
    return word[0].capitalize() + word[1:]

def _preproc_name(name):
    """escapes dashes and dots by making the word camelCase"""
    escaped = name
    for char in name_escape_chars:
        escaped = ''.join(_capitalize(i) for i in escaped.split(char))
    return _capitalize(escaped)

def get_name(component):
    """Attempts to create a "unique", readable, camelcase variable name from a filepath"""
    path = component.path
    return _preproc_name(path_to_src(path))

def component_from_path(path, inlined=False):
    return Component(ComponentTypes[file_extension(path)], path, inlined)

def find_files(directory, extensions, ignore=None):
    subdirectories = iter(d for d in os.listdir(directory) if os.path.isdir(os.path.join(directory, d)))
    targets = []
    for subdir in subdirectories:
        subdir = os.path.join(directory, subdir)
        files = iter(os.path.join(subdir, f) for f in os.listdir(subdir))
        files = iter(f for f in files if os.path.isfile(f))
        files = iter(f for f in files if sum((f.endswith(i) for i in extensions)))
        if ignore:
            files = iter(f for f in files if not sum((i in f for i in ignore)))
        if files:
            targets.extend(files)
    return targets
        
def find_components(directory):
    files = find_files(directory, find_extensions, ignore)
    return [component_from_path(f) for f in files]

def find_external_external_resources(doc):
    links = doc.xpath("//link[@href]")
    links = [l for l in links if l.attrib['href'] and file_extension(l.attrib['href']) in all_extensions]#filter out blank hrefs
    scripts = doc.xpath('//script[@src]')
    scripts = [s for s in scripts if s.attrib['src']]#filter out blank hrefs
    return links + scripts

def elem_is_import(elem):
    return elem.attrib.get('rel') == 'import'

def elem_has_parent(elem, tagname):
    parent = elem.getparent()
    if parent is None:
        return False
    elif parent.tag == tagname:
        return True
    else:
        return elem_has_parent(parent, tagname)

def elem_needs_removal(elem):
    if elem_is_import(elem):
        return True
    else:
        return not elem_has_parent(elem, 'template')

def get_element_resource_url(elem):
    src_attrib = src_attrib_map[elem.tag]
    return elem.attrib[src_attrib]

def path_from_src(elem, parent_component):
    src = get_element_resource_url(elem)
    if src_external(src):
        resource = src
    else:
        resource = os.path.join(os.path.dirname(parent_component.path), src)
        resource = os.path.realpath(resource)
        if not os.path.isfile(resource):
            logging.warn("Parent component {} "
                         "imports non-existant file {} ({})".format(
                             parent_component.path,
                             src,
                             resource
                         ))
            raise MissingDependency(resource)
    return resource

def rewrite_elem_src(elem, parent_component):
    resource = path_from_src(elem, parent_component)
    elem.attrib[src_attrib_map[elem.tag]] = '/' + path_to_src(resource)

def component_from_elem(elem, parent_component):
    resource = path_from_src(elem, parent_component)
    return component_from_path(resource, not elem_needs_removal(elem))

def find_deps(component):
    doc = parse(component.path)
    if doc.getroot() is None:
        return []
    elems = find_external_external_resources(doc)
    return [component_from_elem(elem, component) for elem in elems]

def _build_depmap(components, depmap):
    for component in components:
        if component in depmap:
            continue
        if component.type == ComponentTypes.html:
            deps = find_deps(component)
        else:
            deps = []
        _build_depmap([d for d in deps if d not in depmap], depmap)
        depmap[component] = deps

def build_depmap(sources_dir):
    components = find_components(sources_dir)
    depmap = {}
    for component in components:
        try:
            _build_depmap([component], depmap)
        except MissingDependency:
            logging.warn("Component " + str(component) + " will not be be built due to missing/poorly defined dependencies.")
    return depmap

def string_from_doc(doc):
    walker = html5lib.getTreeWalker("lxml")
    serializer = html5lib.serializer.HTMLSerializer()
    output = unescape_qmarks(serializer.render(walker(doc)))
    return output

def modify_web_component(component):
    """removes external script and link tags from doc"""
    with open(component.path, 'r') as f:
        doc = f.read()
    try:
        doc = fromstring(escape_qmarks(doc))
    except ParserError:
        return doc
    link_elems = find_external_external_resources(doc)
    for elem in link_elems:
        if elem_needs_removal(elem):
            elem.getparent().remove(elem)
        else:
            rewrite_elem_src(elem, component)
    return string_from_doc(doc)

def _render_nodep_component(component, directory):
    typename = get_name(component).lower()
    if component.inlined:
        classname = 'StaticFile'
    else:
        classname = typemap[component.type]
    asset = component.path[len(directory):]
    return depless_template.format(
        classname=classname,
        typename=typename,
        asset=asset
    )

def _render_nodep_component_var(component, directory):
    varname = get_name(component)
    return assign_template.format(
        varname=varname,
        value=_render_nodep_component(component, directory)
    )

def render_component(component, deps, directory):
    indent = ' ' * 4 * 2
    if deps:
        classname = get_name(component)
        depnames = [indent + get_name(c) for c in deps]
        deplist = ',\n'.join(depnames)
        deplist += ',\n' + indent + _render_nodep_component(component, directory)
        return component_class_template.format(
                classname=classname,
                deplist=deplist
        ) + '\n'
    else:
        return _render_nodep_component_var(component, directory) + '\n'

def _render_all_components(component, depmap, visited, directory):
    if component in visited:
        return
    visited.add(component)
    deps = depmap[component]
    source = ""
    for dep in deps:
        #the 'if s' is to prevent adding lots of whitespace
        s = _render_all_components(dep, depmap, visited, directory)
        if s:
            source += s + '\n'
    return source + render_component(component, deps, directory)
        
def render_all_components(depmap, directory):
    visited = set()
    module = ""
    for component in depmap:
        if component in visited:
            continue
        module += _render_all_components(component, depmap, visited, directory)
    return module

def copy_component(component, sources_dir, out_dir):
    if src_external(component.path):
        return
    rel_path = os.path.relpath(component.path, sources_dir)
    rel_dir = os.path.dirname(rel_path)
    os.makedirs(os.path.join(out_dir, rel_dir), exist_ok=True)
    if component.type == ComponentTypes.html:
        src = modify_web_component(component)
        with open(os.path.join(out_dir, rel_path), 'w') as out:
            out.write(src)
        logging.info("Wrote (modified) {}".format(rel_path))
    else:
        copyfile(component.path, os.path.join(out_dir, rel_path))
        logging.info("Copied {}".format(rel_path))

def render_python_module(depmap, sources_dir):
    source = render_all_components(depmap, sources_dir)
    return module_topmatter + source

def build_component_directory(sources_dir, out_dir):
    depmap = build_depmap(sources_dir)
    components_out_dir = os.path.join(out_dir, 'components')
    for component in depmap:
        copy_component(component, sources_dir, components_out_dir)
    with open(os.path.join(out_dir, '__init__.py'), 'w') as out:
        out.write(render_python_module(depmap, sources_dir))
    logging.info("Wrote python module")
    logging.info("Done. ({} components)".format(len(depmap)))
