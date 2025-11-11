import os
import pytest
import yaml
from src.generator import generate_linkml_schema

class TestGenerateLinkMLSchema:
    """Tests for generate_linkml_schema function"""
    
    def test_generate_linkml_schema_sample(self, sample_xsd_path, temp_output_file):
        """Test generating a LinkML schema from a simple XSD file"""
        # Generate LinkML schema
        temp_output_file = temp_output_file.replace('.json', '.yaml')
        generate_linkml_schema(sample_xsd_path, temp_output_file)
        
        # Check that the output file was created
        assert os.path.exists(temp_output_file)
        
        # Load the generated schema
        with open(temp_output_file, "r") as f:
            schema = yaml.safe_load(f)
        
        # Check that the schema contains the Sample class
        assert schema is not None
        assert "classes" in schema
        assert "Sample" in schema["classes"]
    
    def test_generate_linkml_schema_complex(self, complex_xsd_path, temp_output_file):
        """Test generating a LinkML schema from a complex XSD file"""
        # Generate LinkML schema
        temp_output_file = temp_output_file.replace('.json', '.yaml')
        generate_linkml_schema(complex_xsd_path, temp_output_file)
        
        # Check that the output file was created
        assert os.path.exists(temp_output_file)
        
        # Load the generated schema
        with open(temp_output_file, "r") as f:
            schema = yaml.safe_load(f)
        
        # Check that the schema contains the Organization class
        assert schema is not None
        assert "classes" in schema
        assert "Organization" in schema["classes"]
    
    def test_partition_schema(self, complex_xsd_path, temp_output_dir):
        """Test partitioning a schema into multiple files"""
        # Generate LinkML schema with partition=True
        generate_linkml_schema(complex_xsd_path, temp_output_dir, partition=True)
        
        # Check that output files were created
        files = os.listdir(temp_output_dir)
        assert len(files) > 0
        
        # Load one of the generated schemas
        schema_file = os.path.join(temp_output_dir, files[0])
        with open(schema_file, "r") as f:
            schema = yaml.safe_load(f)
        
        # Check schema structure
        assert schema is not None
        assert "classes" in schema
        assert len(schema["classes"]) > 0
    
    
    def test_error_handling_nonexistent_file(self, temp_output_file):
        """Test error handling for a nonexistent XSD file"""
        with pytest.raises(Exception):
            generate_linkml_schema("nonexistent.xsd", temp_output_file)
    
    def test_error_handling_invalid_xml(self, temp_output_file):
        """Test error handling for an invalid XML file"""
        # Create a file with invalid XML
        invalid_xml_path = "invalid.xml"
        with open(invalid_xml_path, "w") as f:
            f.write("<invalid>xml<unclosed>")
        
        try:
            with pytest.raises(Exception):
                generate_linkml_schema(invalid_xml_path, temp_output_file)
        finally:
            # Clean up
            if os.path.exists(invalid_xml_path):
                os.remove(invalid_xml_path) 