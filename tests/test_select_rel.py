from cattrs.preconf.pyyaml import make_converter as make_yaml_converter
from packaging.requirements import Requirement
import pytest
from textwrap import dedent
import yaml


from external_resources.resinfo import (find_resources,
        ItemInfo, Resource, ResourceObject, Release,
        )


@pytest.fixture
def res_dict1():
    data = dedent("""
            ---
            bootstrap:
               type: css
               homepage: https://getbootstrap.com
               base_url: "https://stackpath.bootstrapcdn.com/bootstrap"
               full_url: "{base_url}/{version}/css/bootstrap.min.css"
               local_name: "bootstrap.{version}.css"
               releases:
                  4.3:
                     local_name: bootstrap.css
                  4.4: {}

            htmx:
               comment: "A Hypermedia extension for HTML"
               type: js
               homepage: "https://hypermedia.systems"
               base_url: "https://unpkg.com/htmx.org"
               filename: "htmx.min.js"
               full_url: "{base_url}@{version}/dist/{filename}"
               local_name: "htmx.{major}.min.js"
               releases:
                  1.9.10:
                     integrity: null

            pyodide:
               comment: "Python on WASM"
               type: js
               homepage: https://pyodide.org
               base_url: "https://cdn.jsdelivr.net/pyodide"
               filename: "pyodide.js"
               full_url: "{base_url}/v{version}/full/{filename}"
               local_name: "pyodide.{major}.{minor}.js"
               releases:
                  0.25.0:
                     integrity: null
            """)
    
    converter = make_yaml_converter()
    content = converter.loads(data, dict[str, Resource])
    
    return content

def test_css_sel(res_dict1):
    
    ro_list = find_resources(res_dict1, [Requirement("bootstrap >= 4.3")])
    assert len(ro_list) == 1
    ro = ro_list[0]
    assert ro.name == "bootstrap"
    assert ro.version == "4.4"
    assert ro.get_full_url() == "https://stackpath.bootstrapcdn.com/bootstrap/4.4/css/bootstrap.min.css"
    assert ro.get_local_name() == "bootstrap.4.4.css"

    ro_list = find_resources(res_dict1, [Requirement("bootstrap < 4.4")])
    assert len(ro_list) == 1
    ro = ro_list[0]
    assert ro.name == "bootstrap"
    assert ro.version == "4.3"
    assert ro.get_full_url() == "https://stackpath.bootstrapcdn.com/bootstrap/4.3/css/bootstrap.min.css"
    assert ro.get_local_name() == "bootstrap.css"

