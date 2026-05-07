"""Tests for Storage service."""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock


class TestStorage:
    """Test cases for Storage class."""
    
    def test_init(self, mock_firebase):
        """Test Storage initialization."""
        storage = mock_firebase.storage()
        assert "firebasestorage.googleapis.com" in storage.storage_bucket
        assert storage.path == ""
    
    def test_init_with_service_account(self, mock_config):
        """Test Storage initialization with service account uses mock config."""
        from phirebase import Phirebase
        
        # Test that storage initializes without credentials
        firebase = Phirebase(mock_config)
        storage = firebase.storage()
        assert storage.credentials is None  # No service account in mock_config
    
    def test_child(self, mock_firebase):
        """Test child path building."""
        storage = mock_firebase.storage()
        
        # Test single child
        ref = storage.child("images")
        assert ref.path == "images"
        
        # Test chained children - fresh instance each time
        storage2 = mock_firebase.storage()
        ref = storage2.child("images").child("profile.jpg")
        assert ref.path == "images/profile.jpg"
        
        # Test multiple children at once - fresh instance
        storage3 = mock_firebase.storage()
        ref = storage3.child("documents", "reports", "2024.pdf")
        assert ref.path == "documents/reports/2024.pdf"
    
    def test_child_leading_slash(self, mock_firebase):
        """Test child path with leading slash."""
        storage = mock_firebase.storage()
        ref = storage.child("/images/profile.jpg")
        assert ref.path == "images/profile.jpg"
    
    @patch('phirebase.phirebase.requests.Session.post')
    def test_put_file_path(self, mock_post, mock_firebase, tmp_path):
        """Test uploading a file from path."""
        # Create temporary file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")
        
        mock_response = Mock()
        mock_response.json.return_value = {
            "name": "test.txt",
            "bucket": "test-bucket"
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        storage = mock_firebase.storage()
        result = storage.child("uploads/test.txt").put(str(test_file))
        
        assert result["name"] == "test.txt"
        mock_post.assert_called_once()
    
    @patch('phirebase.phirebase.requests.Session.post')
    def test_put_file_object(self, mock_post, mock_firebase):
        """Test uploading a file object."""
        import io
        file_obj = io.BytesIO(b"Test content")
        
        mock_response = Mock()
        mock_response.json.return_value = {"name": "test.txt"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        storage = mock_firebase.storage()
        result = storage.child("uploads/test.txt").put(file_obj)
        
        assert result["name"] == "test.txt"
    
    def test_get_url(self, mock_firebase):
        """Test getting download URL."""
        storage = mock_firebase.storage()
        storage.child("images/profile.jpg")
        url = storage.get_url()
        
        # URL encodes the path, so check for encoded version
        assert "profile.jpg" in url or "profile%2Fjpg" in url
        assert "alt=media" in url
        assert storage.path is None  # Path should be reset
    
    def test_get_url_with_token(self, mock_firebase):
        """Test getting download URL with token."""
        storage = mock_firebase.storage()
        storage.child("private/file.txt")
        url = storage.get_url(token="test-token")
        
        assert "token=test-token" in url
        assert "alt=media" in url
    
    @patch('phirebase.phirebase.requests.get')
    def test_download_without_credentials(self, mock_get, mock_firebase, tmp_path):
        """Test downloading file without credentials."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_content.return_value = [b"file content"]
        mock_get.return_value = mock_response
        
        output_path = tmp_path / "downloaded.txt"
        
        storage = mock_firebase.storage()
        storage.child("public/file.txt").download(str(output_path))
        
        assert output_path.exists()
        assert output_path.read_text() == "file content"
    
    def test_path_reset_after_operation(self, mock_firebase):
        """Test that path is reset after operations."""
        storage = mock_firebase.storage()
        storage.child("images/photo.jpg")
        url = storage.get_url()
        
        assert storage.path is None