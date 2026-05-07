"""Tests for Realtime Database service."""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from collections import OrderedDict


class TestDatabase:
    """Test cases for Database class."""
    
    def test_init(self, mock_firebase):
        """Test Database initialization."""
        db = mock_firebase.database()
        assert db.api_key == "test-api-key"
        assert db.database_url == "https://test-project.firebaseio.com/"
        assert db.path == ""
    
    def test_child(self, mock_firebase):
        """Test child path building."""
        db = mock_firebase.database()
        ref = db.child("users")
        assert ref.path == "users"
        
        ref = ref.child("user123")
        assert ref.path == "users/user123"
        
        ref = db.child("posts", "post1", "comments")
        assert ref.path == "posts/post1/comments"
    
    def test_build_request_url(self, mock_firebase):
        """Test building request URL."""
        db = mock_firebase.database()
        db.path = "users"
        url = db.build_request_url(None)
        assert "users.json" in url
        assert db.path == ""  # Path should be reset
    
    def test_build_request_url_with_token(self, mock_firebase):
        """Test building request URL with auth token."""
        db = mock_firebase.database()
        db.path = "users"
        url = db.build_request_url("test-token")
        assert "auth=test-token" in url
    
    def test_build_request_url_with_query(self, mock_firebase):
        """Test building request URL with query parameters."""
        db = mock_firebase.database()
        db.path = "users"
        db.build_query = {"orderBy": '"$key"', "limitToFirst": 5}
        url = db.build_request_url(None)
        assert "orderBy" in url
        assert "limitToFirst" in url
    
    @patch('phirebase.phirebase.requests.Session.get')
    def test_get_data(self, mock_get, mock_firebase):
        """Test getting data from database."""
        mock_response = Mock()
        mock_response.json.return_value = {"name": "Rick", "age": 70}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        db = mock_firebase.database()
        result = db.child("users").child("user123").get()
        
        assert isinstance(result.val(), OrderedDict)
        assert result.val()["name"] == "Rick"
    
    @patch('phirebase.phirebase.requests.Session.get')
    def test_get_list_data(self, mock_get, mock_firebase):
        """Test getting list data from database."""
        mock_response = Mock()
        mock_response.json.return_value = ["item1", "item2", "item3"]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        db = mock_firebase.database()
        result = db.child("items").get()
        
        assert result.val() == ["item1", "item2", "item3"]
    
    @patch('phirebase.phirebase.requests.Session.put')
    def test_set_data(self, mock_put, mock_firebase):
        """Test setting data in database."""
        mock_response = Mock()
        mock_response.json.return_value = {"name": "user123"}
        mock_response.raise_for_status.return_value = None
        mock_put.return_value = mock_response
        
        db = mock_firebase.database()
        result = db.child("users").child("user123").set({
            "name": "Rick",
            "age": 70
        })
        
        assert result == {"name": "user123"}
        mock_put.assert_called_once()
    
    @patch('phirebase.phirebase.requests.Session.post')
    def test_push_data(self, mock_post, mock_firebase):
        """Test pushing data to database."""
        mock_response = Mock()
        mock_response.json.return_value = {"name": "-Mx2sKL9pQr"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        db = mock_firebase.database()
        result = db.child("posts").push({
            "title": "Test Post"
        })
        
        assert result["name"] == "-Mx2sKL9pQr"
        mock_post.assert_called_once()
    
    @patch('phirebase.phirebase.requests.Session.patch')
    def test_update_data(self, mock_patch, mock_firebase):
        """Test updating data in database."""
        mock_response = Mock()
        mock_response.json.return_value = {"age": 71}
        mock_response.raise_for_status.return_value = None
        mock_patch.return_value = mock_response
        
        db = mock_firebase.database()
        result = db.child("users").child("user123").update({"age": 71})
        
        assert result["age"] == 71
        mock_patch.assert_called_once()
    
    @patch('phirebase.phirebase.requests.Session.delete')
    def test_remove_data(self, mock_delete, mock_firebase):
        """Test removing data from database."""
        mock_response = Mock()
        mock_response.json.return_value = None
        mock_response.raise_for_status.return_value = None
        mock_delete.return_value = mock_response
        
        db = mock_firebase.database()
        result = db.child("users").child("user123").remove()
        
        assert result is None
        mock_delete.assert_called_once()
    
    def test_generate_key(self, mock_firebase):
        """Test generating a unique key."""
        db = mock_firebase.database()
        key = db.generate_key()
        
        assert isinstance(key, str)
        assert len(key) == 20
    
    def test_generate_key_uniqueness(self, mock_firebase):
        """Test that generated keys are unique."""
        db = mock_firebase.database()
        keys = set()
        for _ in range(100):
            keys.add(db.generate_key())
        
        assert len(keys) == 100  # All keys should be unique
    
    def test_order_by_key(self, mock_firebase):
        """Test order by key query."""
        db = mock_firebase.database()
        ref = db.order_by_key()
        assert ref.build_query["orderBy"] == "$key"
    
    def test_order_by_value(self, mock_firebase):
        """Test order by value query."""
        db = mock_firebase.database()
        ref = db.order_by_value()
        assert ref.build_query["orderBy"] == "$value"
    
    def test_order_by_child(self, mock_firebase):
        """Test order by child query."""
        db = mock_firebase.database()
        ref = db.order_by_child("age")
        assert ref.build_query["orderBy"] == "age"
    
    def test_query_methods(self, mock_firebase):
        """Test query builder methods."""
        db = mock_firebase.database()
        ref = (db.child("users")
               .order_by_child("age")
               .start_at(18)
               .end_at(65)
               .limit_to_first(10))
        
        assert ref.build_query["orderBy"] == "age"
        assert ref.build_query["startAt"] == 18
        assert ref.build_query["endAt"] == 65
        assert ref.build_query["limitToFirst"] == 10
    
    def test_equal_to(self, mock_firebase):
        """Test equal to query."""
        db = mock_firebase.database()
        ref = db.order_by_child("name").equal_to("Rick")
        assert ref.build_query["equalTo"] == "Rick"
    
    def test_shallow(self, mock_firebase):
        """Test shallow query."""
        db = mock_firebase.database()
        ref = db.shallow()
        assert ref.build_query["shallow"] is True
    
    def test_check_token(self, mock_firebase):
        """Test URL generation with token."""
        db = mock_firebase.database()
        url = db.check_token(db.database_url, "users", "test-token")
        assert "auth=test-token" in url
        
        url = db.check_token(db.database_url, "users", None)
        assert "auth=" not in url
    
    def test_pyre_response_val_dict(self, mock_firebase):
        """Test PyreResponse val() for dictionary data."""
        from phirebase.phirebase import PyreResponse, Pyre
        
        pyres = [Pyre(("name", "Rick")), Pyre(("age", 70))]
        response = PyreResponse(pyres, "users")
        result = response.val()
        
        assert isinstance(result, OrderedDict)
        assert result["name"] == "Rick"
        assert result["age"] == 70
    
    def test_pyre_response_val_list(self, mock_firebase):
        """Test PyreResponse val() for list data."""
        from phirebase.phirebase import PyreResponse, Pyre
        
        pyres = [Pyre((0, "item1")), Pyre((1, "item2")), Pyre((2, "item3"))]
        response = PyreResponse(pyres, "items")
        result = response.val()
        
        assert isinstance(result, list)
        assert result == ["item1", "item2", "item3"]
    
    def test_pyre_response_each(self, mock_firebase):
        """Test PyreResponse each() method."""
        from phirebase.phirebase import PyreResponse, Pyre
        
        pyres = [Pyre(("key1", "val1")), Pyre(("key2", "val2"))]
        response = PyreResponse(pyres, "test")
        
        result = response.each()
        assert len(result) == 2
        assert result[0].key() == "key1"
        assert result[0].val() == "val1"