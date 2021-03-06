import os
import package_builder as pb

components_dir = "polymer_bricks"

bad_html = """
<div class="scroll-button" hidden?="{{!scrollable || hideScrollButton}}">
    <paper-icon-button data-screwith="?" icon="chevron-left" class="{{ {hidden: leftHidden} | tokenList }}" on-down="{{holdLeft}}" on-up="{{releaseHold}}"></paper-icon-button>
</div>
"""

escaped_html = bad_html.replace('?', pb.qmark_escape_string, 1)

def _monkeypatch_build_depmap():
    #this is just to speed up this test module
    from functools import lru_cache
    cache_fn = lru_cache(maxsize=256)
    pb.build_depmap = cache_fn(pb.build_depmap)

def test_extension():
    ext = pb.file_extension("/home/asdf/image.jpg")
    assert ext == 'jpg'

def test_find_files():
    exts = ('css',)
    paths = pb.find_files(components_dir, exts)
    assert len(paths) > 10
    for path in paths:
        assert sum((path.endswith(i) for i in exts))

def test_find_components():
    components = pb.find_components(components_dir)
    assert len(components) > 20
    for c in components:
        assert isinstance(c, pb.Component)
        assert os.path.isfile(c.path)
        assert c.inlined == False

def test_component_hash():
    p = 'http://localhost:8080/test.js'
    a = pb.component_from_path(p)
    b = pb.component_from_path(p)
    assert a == b

def test_find_deps():
    path = os.path.join(components_dir, 'paper-tabs/paper-tab.html')
    component = pb.component_from_path(path)
    all_components = set(pb.find_components(components_dir))
    deps = pb.find_deps(component)
    assert deps
    for dep in deps:
        assert dep.type in pb.ComponentTypes
        assert os.path.isfile(dep.path)

def test_build_depmap():
    depmap = pb.build_depmap(components_dir)
    for dep in depmap:
        if dep.type == pb.ComponentTypes.html:
            assert dep.inlined == False

def test_modify_web_component():
    from lxml.html import parse
    #Warning: this test might change if paper-tab.html changes!
    path = os.path.join(components_dir, 'paper-tabs/paper-tab.html')
    doc = parse(path)
    assert len(pb.find_external_external_resources(doc)) == 2

def test_pretty_name():
    name = 'lib.min.js'
    pname = pb._preproc_name(name)
    assert pname == "LibMinJs"

def test_get_name():
    path = os.path.join(components_dir, 'paper-tabs/paper-tab.html')
    component = pb.component_from_path(path)
    name = pb.get_name(component)
    assert name == "PaperTabsPaperTabHtml"

def test_component_rendering():
    path = os.path.join(components_dir, 'paper-tabs/paper-tab.html')
    component = pb.component_from_path(path)
    depmap = pb.build_depmap(components_dir)

def test_all_components_rendering():
    from collections import Counter
    depmap = pb.build_depmap(components_dir)
    source = pb.render_all_components(depmap, components_dir)

    #check for duplicate definitions
    definitions = []
    for line in source.split('\n'):
        if not line.startswith(' ') and '=' in line:
            definitions.append(line.split()[0])
            assert line.endswith(')')
    assert Counter(definitions).most_common(1)[0][1] == 1

    #try to run the code:
    #(need some mock definitions first)
    asset_root = "polymer_bricks:components/"
    class _Args:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    class StaticFile(_Args):
        pass

    class WebComponent(_Args):
        pass

    class StaticJs(_Args):
        pass

    class StaticCss(_Args):
        pass

    exec(source, locals())

def test_escape_qmarks():
    subbed = pb.escape_qmarks(bad_html)
    assert subbed == escaped_html

def test_unescape_qmarks():
    assert pb.unescape_qmarks(escaped_html) == bad_html

def test_tostring():
    from lxml.html import fromstring
    doc = fromstring(pb.escape_qmarks(bad_html))
    out = pb.string_from_doc(doc)
    assert "{{!scrollable" in out
    assert "hidden?" in out

tests = (
    test_extension,
    test_find_files,
    test_find_components,
    test_component_hash,
    test_find_deps,
    test_build_depmap,
    test_modify_web_component,
    test_pretty_name,
    test_get_name,
    test_component_rendering,
    test_all_components_rendering,
    test_escape_qmarks,
    test_unescape_qmarks,
    test_tostring,
)

def main():
    import sys
    global components_dir
    if len(sys.argv) < 2:
        print("Usage: python3 test.py <sources_dir>")
        print("where <sources_dir> contains all the polymer components")
        return
    components_dir = os.path.abspath(sys.argv[-1])
    _monkeypatch_build_depmap()
    for test in tests:
        test()
        print('.', end='')
    print("OK [{} passed]".format(len(tests)))

if __name__ == "__main__":
    main()
