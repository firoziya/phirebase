"""Tests for utility functions and classes."""

import pytest
import json
from unittest.mock import Mock, patch
from phirebase.phirebase import (
    _convert_to_firestore_fields,
    _convert_value_to_firestore,
    _parse_firestore_response,
    _parse_document,
    _parse_fields,
    _extract_value,
    _parse_query_response,
    convert_to_pyre,
    convert_list_to_pyre,
    raise_detailed_error,
    PyreResponse,
    Pyre
)


class TestFirestoreConverters:
    """Test cases for Firestore data converters."""
    
    def test_convert_string_value(self):
        """Test converting string value."""
        result = _convert_value_to_firestore("hello")
        assert result == {"stringValue": "hello"}
    
    def test_convert_boolean_value(self):
        """Test converting boolean value."""
        result = _convert_value_to_firestore(True)
        assert result == {"booleanValue": True}
        
        result = _convert_value_to_firestore(False)
        assert result == {"booleanValue": False}
    
    def test_convert_integer_value(self):
        """Test converting integer value."""
        result = _convert_value_to_firestore(42)
        assert result == {"integerValue": "42"}
    
    def test_convert_float_value(self):
        """Test converting float value."""
        result = _convert_value_to_firestore(3.14)
        assert result == {"doubleValue": 3.14}
    
    def test_convert_null_value(self):
        """Test converting None value."""
        result = _convert_value_to_firestore(None)
        assert result == {"nullValue": None}
    
    def test_convert_array_value(self):
        """Test converting array value."""
        result = _convert_value_to_firestore([1, "two", True])
        assert "arrayValue" in result
        assert len(result["arrayValue"]["values"]) == 3
        assert result["arrayValue"]["values"][0] == {"integerValue": "1"}
        assert result["arrayValue"]["values"][1] == {"stringValue": "two"}
        assert result["arrayValue"]["values"][2] == {"booleanValue": True}
    
    def test_convert_map_value(self):
        """Test converting map/dict value."""
        data = {"name": "Rick", "age": 70}
        result = _convert_value_to_firestore(data)
        
        assert "mapValue" in result
        fields = result["mapValue"]["fields"]
        assert fields["name"] == {"stringValue": "Rick"}
        assert fields["age"] == {"integerValue": "70"}
    
    def test_convert_server_timestamp(self):
        """Test converting server timestamp."""
        result = _convert_value_to_firestore({"serverTimestamp": {}})
        assert result == {"timestampValue": "REQUEST_TIME"}
    
    def test_convert_array_union(self):
        """Test converting array union."""
        result = _convert_value_to_firestore({"arrayUnion": ["a", "b"]})
        assert "arrayValue" in result
        assert len(result["arrayValue"]["values"]) == 2
    
    def test_convert_array_remove(self):
        """Test converting array remove."""
        result = _convert_value_to_firestore({"arrayRemove": ["x"]})
        assert "arrayValue" in result
    
    def test_convert_increment(self):
        """Test converting increment."""
        result = _convert_value_to_firestore({"incrementValue": 5})
        assert result == {"integerValue": "5"}
    
    def test_convert_delete_field(self):
        """Test converting delete field."""
        result = _convert_value_to_firestore({"deleteField": {}})
        assert result == {"nullValue": None}
    
    def test_convert_to_firestore_fields(self):
        """Test converting dict to firestore fields."""
        data = {
            "name": "Morty",
            "age": 14,
            "active": True,
            "scores": [90, 85, 95]
        }
        result = _convert_to_firestore_fields(data)
        
        assert "fields" not in result
        assert result["name"] == {"stringValue": "Morty"}
        assert result["age"] == {"integerValue": "14"}
        assert result["active"] == {"booleanValue": True}
        assert "arrayValue" in result["scores"]


class TestFirestoreParsers:
    """Test cases for Firestore response parsers."""
    
    def test_extract_string_value(self):
        """Test extracting string value."""
        result = _extract_value({"stringValue": "hello"})
        assert result == "hello"
    
    def test_extract_boolean_value(self):
        """Test extracting boolean value."""
        result = _extract_value({"booleanValue": True})
        assert result is True
    
    def test_extract_integer_value(self):
        """Test extracting integer value."""
        result = _extract_value({"integerValue": "42"})
        assert result == 42
        assert isinstance(result, int)
    
    def test_extract_double_value(self):
        """Test extracting double value."""
        result = _extract_value({"doubleValue": 3.14})
        assert result == 3.14
    
    def test_extract_null_value(self):
        """Test extracting null value."""
        result = _extract_value({"nullValue": None})
        assert result is None
    
    def test_extract_timestamp_value(self):
        """Test extracting timestamp value."""
        result = _extract_value({"timestampValue": "2024-01-01T00:00:00Z"})
        assert result == "2024-01-01T00:00:00Z"
    
    def test_extract_map_value(self):
        """Test extracting map value."""
        value = {
            "mapValue": {
                "fields": {
                    "name": {"stringValue": "Rick"},
                    "age": {"integerValue": "70"}
                }
            }
        }
        result = _extract_value(value)
        assert result == {"name": "Rick", "age": 70}
    
    def test_extract_array_value(self):
        """Test extracting array value."""
        value = {
            "arrayValue": {
                "values": [
                    {"integerValue": "1"},
                    {"stringValue": "two"},
                    {"booleanValue": True}
                ]
            }
        }
        result = _extract_value(value)
        assert result == [1, "two", True]
    
    def test_parse_fields(self):
        """Test parsing fields."""
        fields = {
            "name": {"stringValue": "Morty"},
            "age": {"integerValue": "14"},
            "tags": {
                "arrayValue": {
                    "values": [
                        {"stringValue": "student"},
                        {"stringValue": "adventurer"}
                    ]
                }
            }
        }
        result = _parse_fields(fields)
        assert result["name"] == "Morty"
        assert result["age"] == 14
        assert result["tags"] == ["student", "adventurer"]
    
    def test_parse_document(self):
        """Test parsing a document."""
        doc = {
            "name": "projects/test/databases/(default)/documents/users/user123",
            "fields": {
                "name": {"stringValue": "Rick"},
                "age": {"integerValue": "70"}
            },
            "createTime": "2024-01-01T00:00:00Z",
            "updateTime": "2024-01-01T00:00:00Z"
        }
        result = _parse_document(doc)
        assert result["id"] == "user123"
        assert result["name"] == "Rick"
        assert result["age"] == 70
    
    def test_parse_firestore_response_single_document(self):
        """Test parsing single document response."""
        response = {
            "name": "projects/test/databases/(default)/documents/users/user1",
            "fields": {
                "name": {"stringValue": "User 1"}
            }
        }
        result = _parse_firestore_response(response)
        assert result["id"] == "user1"
        assert result["name"] == "User 1"
    
    def test_parse_firestore_response_multiple_documents(self):
        """Test parsing multiple documents response."""
        response = {
            "documents": [
                {
                    "name": "projects/test/databases/(default)/documents/users/user1",
                    "fields": {"name": {"stringValue": "User 1"}}
                },
                {
                    "name": "projects/test/databases/(default)/documents/users/user2",
                    "fields": {"name": {"stringValue": "User 2"}}
                }
            ]
        }
        result = _parse_firestore_response(response)
        assert len(result) == 2
        assert result[0]["id"] == "user1"
        assert result[1]["id"] == "user2"
    
    def test_parse_firestore_response_empty(self):
        """Test parsing empty response."""
        result = _parse_firestore_response({"name": "projects/test/databases/(default)/documents/users/nonexistent"})
        assert result is None
    
    def test_parse_query_response(self):
        """Test parsing query response."""
        response = [
            {
                "document": {
                    "name": "projects/test/databases/(default)/documents/users/user1",
                    "fields": {"name": {"stringValue": "User 1"}}
                }
            },
            {
                "document": {
                    "name": "projects/test/databases/(default)/documents/users/user2",
                    "fields": {"name": {"stringValue": "User 2"}}
                }
            }
        ]
        result = _parse_query_response(response)
        assert len(result) == 2
        assert result[0]["id"] == "user1"
        assert result[1]["id"] == "user2"


class TestPyreResponse:
    """Test cases for PyreResponse class."""
    
    def test_pyre_val(self):
        """Test Pyre val() method."""
        pyre = Pyre(("name", "Rick"))
        assert pyre.val() == "Rick"
        assert pyre.key() == "name"
    
    def test_pyre_response_key(self):
        """Test PyreResponse key() method."""
        response = PyreResponse([], "users")
        assert response.key() == "users"
    
    def test_pyre_response_each_empty(self):
        """Test PyreResponse each() with non-list."""
        response = PyreResponse("simple_value", "key")
        result = response.each()
        assert result == []


class TestConverters:
    """Test cases for Realtime Database converters."""
    
    def test_convert_to_pyre(self):
        """Test converting items to Pyre list."""
        items = [("name", "Rick"), ("age", 70)]
        result = convert_to_pyre(items)
        assert len(result) == 2
        assert result[0].val() == "Rick"
        assert result[1].val() == 70
    
    def test_convert_list_to_pyre(self):
        """Test converting list to Pyre list."""
        items = ["item1", "item2", "item3"]
        result = convert_list_to_pyre(items)
        assert len(result) == 3
        assert result[0].key() == 0
        assert result[0].val() == "item1"
        assert result[2].key() == 2
        assert result[2].val() == "item3"


class TestErrorHandling:
    """Test cases for error handling."""
    
    def test_raise_detailed_error_success(self):
        """Test raise_detailed_error with successful response."""
        mock_request = Mock()
        mock_request.raise_for_status.return_value = None
        
        # Should not raise
        raise_detailed_error(mock_request)
    
    def test_raise_detailed_error_http_error(self):
        """Test raise_detailed_error with HTTP error."""
        from requests.exceptions import HTTPError
        
        mock_request = Mock()
        mock_request.text = '{"error": "Not Found"}'
        
        http_error = HTTPError("404 Not Found")
        mock_request.raise_for_status.side_effect = http_error
        
        with pytest.raises(HTTPError):
            raise_detailed_error(mock_request)