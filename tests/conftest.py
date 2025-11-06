import os
import sys
import pytest
import tempfile
import json
from xsdata.formats.dataclass.parsers import XmlParser
from xsdata.formats.dataclass.parsers.config import ParserConfig

# Ensure 'src' is importable as a top-level module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

@pytest.fixture
def sample_xsd_path():
    """Returns the path to the sample XSD file"""
    return os.path.join(os.path.dirname(__file__), "data", "sample.xsd")

@pytest.fixture
def complex_xsd_path():
    """Returns the path to the complex XSD file"""
    return os.path.join(os.path.dirname(__file__), "data", "complex.xsd")

@pytest.fixture
def ome_xsd_path():
    """Returns the path to the OME XSD file"""
    return os.path.join(os.path.dirname(__file__), "..", "data", "ome.xsd")

@pytest.fixture
def xml_parser():
    """Returns an XmlParser instance"""
    return XmlParser()

@pytest.fixture
def xml_parser_with_base_url(request):
    """Returns an XmlParser instance with a base URL set to the specified file"""
    def _parser(xsd_path):
        config = ParserConfig(base_url=xsd_path)
        return XmlParser(config=config)
    return _parser

@pytest.fixture
def temp_output_file():
    """Returns a temporary file for output"""
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)

@pytest.fixture
def temp_output_dir():
    """Returns a temporary directory for output files"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield tmp_dir 