"""Tests for Firestore service."""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock


class TestFirestore:
    """Test cases for Firestore class."""
    
    def test_init(self, mock_firebase):
        """Test Firestore initialization."""
        db = mock_firebase.firestore()
        assert db.project_id == "test-project-id"
        assert db.api_key == "test-api-key"
        assert "firestore.googleapis.com" in db.base_url
    
    def test_collection(self, mock_firebase):
        """Test collection reference."""
        db = mock_firebase.firestore()
        ref = db.collection("users")
        assert "users" in ref.path
        assert ref._query_filters == []
    
    def test_document(self, mock_firebase):
        """Test document reference."""
        db = mock_firebase.firestore()
        ref = db.collection("users").document("user123")
        assert "users/user123" in ref.path
    
    def test_document_without_collection_error(self, mock_firebase):
        """Test document without collection raises error."""
        db = mock_firebase.firestore()
        with pytest.raises(ValueError, match="Must call .collection"):
            db.document("user123")
    
    @patch('phirebase.phirebase.requests.Session.post')
    def test_add_document(self, mock_post, mock_firebase, sample_user_data):
        """Test adding a document."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "name": "projects/test-project-id/databases/(default)/documents/users/abc123",
            "fields": {},
            "createTime": "2024-01-01T00:00:00Z",
            "updateTime": "2024-01-01T00:00:00Z"
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        db = mock_firebase.firestore()
        result = db.collection("users").add(sample_user_data)
        
        assert result["id"] == "abc123"
        assert "id" in result
        assert "path" in result
        assert "create_time" in result
        mock_post.assert_called_once()
    
    @patch('phirebase.phirebase.requests.Session.get')
    def test_get_document(self, mock_get, mock_firebase):
        """Test getting a document."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "name": "projects/test-project-id/databases/(default)/documents/users/user123",
            "fields": {
                "name": {"stringValue": "Rick Sanchez"},
                "age": {"integerValue": "70"},
                "active": {"booleanValue": True}
            },
            "createTime": "2024-01-01T00:00:00Z",
            "updateTime": "2024-01-01T00:00:00Z"
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        db = mock_firebase.firestore()
        result = db.collection("users").document("user123").get()
        
        assert result is not None
        assert result["id"] == "user123"
        assert result["name"] == "Rick Sanchez"
        assert result["age"] == 70
        assert result["active"] is True
    
    @patch('phirebase.phirebase.requests.Session.get')
    def test_get_nonexistent_document(self, mock_get, mock_firebase):
        """Test getting a non-existent document."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "name": "projects/test-project-id/databases/(default)/documents/users/nonexistent"
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        db = mock_firebase.firestore()
        result = db.collection("users").document("nonexistent").get()
        
        assert result is None
    
    @patch('phirebase.phirebase.requests.Session.patch')
    def test_set_document(self, mock_patch, mock_firebase, sample_user_data):
        """Test setting a document."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "name": "projects/test-project-id/databases/(default)/documents/users/user123",
            "fields": {},
            "updateTime": "2024-01-01T00:00:00Z"
        }
        mock_response.raise_for_status.return_value = None
        mock_patch.return_value = mock_response
        
        db = mock_firebase.firestore()
        result = db.collection("users").document("user123").set(sample_user_data)
        
        assert result is not None
        mock_patch.assert_called_once()
    
    @patch('phirebase.phirebase.requests.Session.patch')
    def test_set_document_with_merge(self, mock_patch, mock_firebase):
        """Test setting a document with merge."""
        mock_response = Mock()
        mock_response.json.return_value = {"updateTime": "2024-01-01T00:00:00Z"}
        mock_response.raise_for_status.return_value = None
        mock_patch.return_value = mock_response
        
        db = mock_firebase.firestore()
        result = db.collection("users").document("user123").set(
            {"age": 71}, merge=True
        )
        
        assert result is not None
        # Verify merge parameter was included
        call_args = mock_patch.call_args[0][0]
        assert "updateMask.fieldPaths" in call_args
    
    @patch('phirebase.phirebase.requests.Session.patch')
    def test_update_document(self, mock_patch, mock_firebase):
        """Test updating a document."""
        mock_response = Mock()
        mock_response.json.return_value = {"updateTime": "2024-01-01T00:00:00Z"}
        mock_response.raise_for_status.return_value = None
        mock_patch.return_value = mock_response
        
        db = mock_firebase.firestore()
        result = db.collection("users").document("user123").update({
            "age": 71,
            "active": False
        })
        
        assert result is not None
        call_args = mock_patch.call_args[0][0]
        assert "updateMask.fieldPaths" in call_args
        assert "age" in call_args
        assert "active" in call_args
    
    @patch('phirebase.phirebase.requests.Session.delete')
    def test_delete_document(self, mock_delete, mock_firebase):
        """Test deleting a document."""
        mock_response = Mock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status.return_value = None
        mock_delete.return_value = mock_response
        
        db = mock_firebase.firestore()
        result = db.collection("users").document("user123").delete()
        
        assert result is not None
        mock_delete.assert_called_once()
    
    def test_where_clause(self, mock_firebase):
        """Test adding where clause."""
        db = mock_firebase.firestore()
        ref = db.collection("users").where("age", ">=", 18)
        
        assert len(ref._query_filters) == 1
        assert ref._query_filters[0]["field"] == "age"
        assert ref._query_filters[0]["op"] == "GREATER_THAN_OR_EQUAL"
        assert ref._query_filters[0]["value"] == 18
    
    def test_where_invalid_operator(self, mock_firebase):
        """Test where with invalid operator."""
        db = mock_firebase.firestore()
        with pytest.raises(ValueError, match="Unsupported operator"):
            db.collection("users").where("age", "===", 18)
    
    def test_order_by(self, mock_firebase):
        """Test ordering query."""
        db = mock_firebase.firestore()
        ref = db.collection("users").order_by("age", "DESCENDING")
        
        assert len(ref._query_orders) == 1
        assert ref._query_orders[0]["field"] == "age"
        assert ref._query_orders[0]["direction"] == "DESCENDING"
    
    def test_limit(self, mock_firebase):
        """Test limiting query results."""
        db = mock_firebase.firestore()
        ref = db.collection("users").limit(10)
        
        assert ref._query_limit == 10
    
    def test_offset(self, mock_firebase):
        """Test offsetting query results."""
        db = mock_firebase.firestore()
        ref = db.collection("users").offset(5)
        
        assert ref._query_offset == 5
    
    def test_method_chaining(self, mock_firebase):
        """Test method chaining for queries."""
        db = mock_firebase.firestore()
        ref = (db.collection("users")
               .where("age", ">=", 18)
               .where("active", "==", True)
               .order_by("name", "ASCENDING")
               .limit(10))
        
        assert len(ref._query_filters) == 2
        assert len(ref._query_orders) == 1
        assert ref._query_limit == 10
    
    @patch('phirebase.phirebase.requests.Session.get')
    def test_get_all_documents(self, mock_get, mock_firebase):
        """Test getting all documents in collection."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "documents": [
                {
                    "name": "projects/test-project-id/databases/(default)/documents/users/user1",
                    "fields": {
                        "name": {"stringValue": "User 1"},
                        "age": {"integerValue": "25"}
                    }
                },
                {
                    "name": "projects/test-project-id/databases/(default)/documents/users/user2",
                    "fields": {
                        "name": {"stringValue": "User 2"},
                        "age": {"integerValue": "30"}
                    }
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        db = mock_firebase.firestore()
        results = db.collection("users").get_all()
        
        assert len(results) == 2
        assert results[0]["name"] == "User 1"
        assert results[1]["name"] == "User 2"
    
    def test_server_timestamp(self, mock_firebase):
        """Test server timestamp sentinel."""
        db = mock_firebase.firestore()
        timestamp = db.server_timestamp()
        assert timestamp == {"serverTimestamp": {}}
    
    def test_array_union(self, mock_firebase):
        """Test array union sentinel."""
        db = mock_firebase.firestore()
        union = db.array_union("tag1", "tag2")
        assert union == {"arrayUnion": ["tag1", "tag2"]}
    
    def test_array_remove(self, mock_firebase):
        """Test array remove sentinel."""
        db = mock_firebase.firestore()
        remove = db.array_remove("tag1")
        assert remove == {"arrayRemove": ["tag1"]}
    
    def test_increment(self, mock_firebase):
        """Test increment sentinel."""
        db = mock_firebase.firestore()
        inc = db.increment(5)
        assert inc == {"incrementValue": 5}
    
    def test_delete_field_value(self, mock_firebase):
        """Test delete field sentinel."""
        db = mock_firebase.firestore()
        delete_field = db.delete_field_value()
        assert delete_field == {"deleteField": {}}
    
    def test_subcollection(self, mock_firebase):
        """Test subcollection reference."""
        db = mock_firebase.firestore()
        ref = db.collection("users").document("user123").subcollection("posts")
        assert "users/user123/posts" in ref.path
    
    def test_subcollection_without_document_error(self, mock_firebase):
        """Test subcollection without document raises error."""
        db = mock_firebase.firestore()
        with pytest.raises(ValueError, match="Must call .document"):
            db.collection("users").subcollection("posts")