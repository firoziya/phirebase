"""Tests for Authentication service."""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from requests.exceptions import HTTPError


class TestAuth:
    """Test cases for Auth class."""
    
    def test_init(self, mock_firebase):
        """Test Auth initialization."""
        auth = mock_firebase.auth()
        assert auth.api_key == "test-api-key"
        assert auth.current_user is None
    
    @patch('phirebase.phirebase.requests.post')
    def test_sign_in_with_email_and_password(self, mock_post, mock_firebase, sample_auth_response):
        """Test sign in with email and password."""
        mock_response = Mock()
        mock_response.json.return_value = sample_auth_response
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        auth = mock_firebase.auth()
        result = auth.sign_in_with_email_and_password("test@example.com", "password")
        
        assert result == sample_auth_response
        assert auth.current_user == sample_auth_response
        assert result["idToken"] == "test-id-token"
        assert result["email"] == "test@example.com"
        
        # Verify the correct URL was called
        mock_post.assert_called_once()
        call_args = mock_post.call_args[0][0]
        assert "verifyPassword" in call_args
        assert "test-api-key" in call_args
    
    @patch('phirebase.phirebase.requests.post')
    def test_sign_in_with_email_and_password_error(self, mock_post, mock_firebase):
        """Test sign in with invalid credentials."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = HTTPError("Invalid password")
        mock_response.text = json.dumps({"error": {"message": "INVALID_PASSWORD"}})
        mock_post.return_value = mock_response
        
        auth = mock_firebase.auth()
        
        with pytest.raises(HTTPError):
            auth.sign_in_with_email_and_password("test@example.com", "wrong_password")
    
    @patch('phirebase.phirebase.requests.post')
    def test_create_user_with_email_and_password(self, mock_post, mock_firebase, sample_auth_response):
        """Test creating a new user."""
        mock_response = Mock()
        mock_response.json.return_value = sample_auth_response
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        auth = mock_firebase.auth()
        result = auth.create_user_with_email_and_password("newuser@example.com", "password123")
        
        assert result == sample_auth_response
        assert "signupNewUser" in mock_post.call_args[0][0]
    
    @patch('phirebase.phirebase.requests.post')
    def test_get_account_info(self, mock_post, mock_firebase):
        """Test getting account information."""
        account_info = {
            "users": [{
                "localId": "user123",
                "email": "test@example.com",
                "emailVerified": False,
                "providerUserInfo": [{
                    "providerId": "password",
                    "email": "test@example.com"
                }]
            }]
        }
        
        mock_response = Mock()
        mock_response.json.return_value = account_info
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        auth = mock_firebase.auth()
        result = auth.get_account_info("test-id-token")
        
        assert result == account_info
        assert result["users"][0]["email"] == "test@example.com"
    
    @patch('phirebase.phirebase.requests.post')
    def test_send_password_reset_email(self, mock_post, mock_firebase):
        """Test sending password reset email."""
        mock_response = Mock()
        mock_response.json.return_value = {"email": "test@example.com"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        auth = mock_firebase.auth()
        result = auth.send_password_reset_email("test@example.com")
        
        assert result["email"] == "test@example.com"
        assert "getOobConfirmationCode" in mock_post.call_args[0][0]
    
    @patch('phirebase.phirebase.requests.post')
    def test_verify_password_reset_code(self, mock_post, mock_firebase):
        """Test verifying password reset code."""
        mock_response = Mock()
        mock_response.json.return_value = {"email": "test@example.com", "requestType": "PASSWORD_RESET"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        auth = mock_firebase.auth()
        result = auth.verify_password_reset_code("reset-code", "newpassword123")
        
        assert result["email"] == "test@example.com"
    
    @patch('phirebase.phirebase.requests.post')
    def test_send_email_verification(self, mock_post, mock_firebase):
        """Test sending email verification."""
        mock_response = Mock()
        mock_response.json.return_value = {"email": "test@example.com"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        auth = mock_firebase.auth()
        result = auth.send_email_verification("test-id-token")
        
        assert result["email"] == "test@example.com"
    
    @patch('phirebase.phirebase.requests.post')
    def test_refresh_token(self, mock_post, mock_firebase):
        """Test refreshing ID token."""
        refresh_response = {
            "access_token": "new-access-token",
            "expires_in": "3600",
            "token_type": "Bearer",
            "refresh_token": "new-refresh-token",
            "id_token": "new-id-token",
            "user_id": "user123",
            "project_id": "test-project-id"
        }
        
        mock_response = Mock()
        mock_response.json.return_value = refresh_response
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        auth = mock_firebase.auth()
        result = auth.refresh("old-refresh-token")
        
        assert result["userId"] == "user123"
        assert result["idToken"] == "new-id-token"
        assert result["refreshToken"] == "new-refresh-token"