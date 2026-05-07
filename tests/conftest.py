"""Pytest configuration and fixtures for Phirebase tests."""

import pytest
import json
import os
from unittest.mock import Mock, patch, MagicMock
from collections import OrderedDict


@pytest.fixture
def mock_config():
    """Mock Firebase configuration."""
    return {
        "apiKey": "test-api-key",
        "authDomain": "test-project.firebaseapp.com",
        "databaseURL": "https://test-project.firebaseio.com",
        "storageBucket": "test-project.appspot.com",
        "projectId": "test-project-id"
    }


@pytest.fixture
def mock_config_with_service_account():
    """Mock Firebase configuration with service account."""
    return {
        "apiKey": "test-api-key",
        "authDomain": "test-project.firebaseapp.com",
        "databaseURL": "https://test-project.firebaseio.com",
        "storageBucket": "test-project.appspot.com",
        "projectId": "test-project-id",
        "serviceAccount": {
            "type": "service_account",
            "project_id": "test-project-id",
            "private_key_id": "test-key-id",
            "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC7VJTUt9Us8cKj\nMzEfYyjiWA4R4/M2bS1+fWI3Q==\n-----END PRIVATE KEY-----\n",
            "client_email": "test@test-project.iam.gserviceaccount.com",
            "client_id": "123456789",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token"
        }
    }


@pytest.fixture
def mock_firebase(mock_config):
    """Create a Phirebase instance with mocked requests."""
    from phirebase import Phirebase
    
    with patch('phirebase.phirebase.requests.Session') as mock_session:
        firebase = Phirebase(mock_config)
        firebase.requests = mock_session
        yield firebase


@pytest.fixture
def mock_requests():
    """Mock requests session."""
    with patch('requests.Session') as mock:
        yield mock


@pytest.fixture
def mock_response():
    """Create a mock HTTP response."""
    mock = Mock()
    mock.status_code = 200
    mock.json.return_value = {}
    mock.text = "{}"
    mock.raise_for_status.return_value = None
    return mock


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "name": "Rick Sanchez",
        "age": 70,
        "email": "rick@c137.com",
        "active": True,
        "tags": ["genius", "scientist"],
        "address": {
            "dimension": "C-137",
            "planet": "Earth"
        }
    }


@pytest.fixture
def sample_auth_response():
    """Sample authentication response."""
    return {
        "kind": "identitytoolkit#VerifyPasswordResponse",
        "localId": "user123",
        "email": "test@example.com",
        "displayName": "",
        "idToken": "test-id-token",
        "registered": True,
        "refreshToken": "test-refresh-token",
        "expiresIn": "3600"
    }