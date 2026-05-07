import requests
from requests import Session
from requests.exceptions import HTTPError

try:
    from urllib.parse import urlencode, quote
except ImportError:
    from urllib import urlencode, quote

import json
import math
from random import uniform
import time
from collections import OrderedDict
import threading
import socket

# Updated imports for authentication
try:
    from google.oauth2 import service_account
    from google.auth.transport.requests import AuthorizedSession
    HAS_GOOGLE_AUTH = True
except ImportError:
    HAS_GOOGLE_AUTH = False
    try:
        from oauth2client.service_account import ServiceAccountCredentials
        HAS_OAUTH2CLIENT = True
    except ImportError:
        HAS_OAUTH2CLIENT = False

from google.cloud import storage

try:
    from urllib3.contrib.appengine import is_appengine_sandbox
    from requests_toolbelt.adapters import appengine
    HAS_APPENGINE_SUPPORT = True
except ImportError:
    HAS_APPENGINE_SUPPORT = False
    is_appengine_sandbox = lambda: False

import python_jwt as jwt
from Crypto.PublicKey import RSA
import datetime

# Import from the fixed sseclient module
from .sseclient import SSEClient


def initialize_app(config):
    """Initialize and return a Phirebase instance"""
    return Phirebase(config)


class Phirebase:
    """Phirebase Interface"""
    def __init__(self, config):
        self.api_key = config.get("apiKey")
        self.auth_domain = config.get("authDomain")
        self.database_url = config.get("databaseURL")
        self.storage_bucket = config.get("storageBucket")
        self.credentials = None
        self.requests = requests.Session()
        
        if config.get("serviceAccount"):
            scopes = [
                'https://www.googleapis.com/auth/firebase.database',
                'https://www.googleapis.com/auth/userinfo.email',
                'https://www.googleapis.com/auth/cloud-platform',
                'https://www.googleapis.com/auth/datastore'
            ]
            service_account_type = type(config["serviceAccount"])
            
            if HAS_GOOGLE_AUTH:
                # Use modern google-auth library
                if service_account_type is str:
                    self.credentials = service_account.Credentials.from_service_account_file(
                        config["serviceAccount"], scopes=scopes
                    )
                elif service_account_type is dict:
                    self.credentials = service_account.Credentials.from_service_account_info(
                        config["serviceAccount"], scopes=scopes
                    )
            elif HAS_OAUTH2CLIENT:
                # Fallback to deprecated oauth2client
                if service_account_type is str:
                    self.credentials = ServiceAccountCredentials.from_json_keyfile_name(
                        config["serviceAccount"], scopes
                    )
                elif service_account_type is dict:
                    self.credentials = ServiceAccountCredentials.from_json_keyfile_dict(
                        config["serviceAccount"], scopes
                    )
            else:
                raise ImportError(
                    "Service account requires either 'google-auth' or 'oauth2client' package. "
                    "Install with: pip install google-auth"
                )
        
        self.project_id = config.get("projectId") or self._extract_project_id()
        
        if HAS_APPENGINE_SUPPORT and is_appengine_sandbox():
            adapter = appengine.AppEngineAdapter(max_retries=3)
        else:
            adapter = requests.adapters.HTTPAdapter(max_retries=3)
        
        for scheme in ('http://', 'https://'):
            self.requests.mount(scheme, adapter)
    
    def _extract_project_id(self):
        """Extract project ID from database URL or storage bucket"""
        if self.database_url:
            return self.database_url.split('//')[1].split('.')[0]
        elif self.storage_bucket:
            return self.storage_bucket.split('.')[0]
        return None
    
    def auth(self):
        return Auth(self.api_key, self.requests, self.credentials)
    
    def database(self):
        return Database(self.credentials, self.api_key, self.database_url, self.requests)
    
    def firestore(self):
        """Returns a Firestore service instance"""
        return Firestore(
            credentials=self.credentials,
            api_key=self.api_key,
            project_id=self.project_id,
            requests_session=self.requests
        )
    
    def storage(self):
        return Storage(self.credentials, self.storage_bucket, self.requests)


class Auth:
    """Authentication Service"""
    def __init__(self, api_key, requests_session, credentials):
        self.api_key = api_key
        self.current_user = None
        self.requests = requests_session
        self.credentials = credentials
    
    def sign_in_with_email_and_password(self, email, password):
        request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyPassword?key={0}".format(
            self.api_key
        )
        headers = {"content-type": "application/json; charset=UTF-8"}
        data = json.dumps({"email": email, "password": password, "returnSecureToken": True})
        request_object = requests.post(request_ref, headers=headers, data=data)
        raise_detailed_error(request_object)
        self.current_user = request_object.json()
        return request_object.json()
    
    def create_custom_token(self, uid, additional_claims=None):
        if not self.credentials:
            raise ValueError("Service account credentials required for custom token creation")
        
        service_account_email = self.credentials.service_account_email
        private_key = RSA.importKey(self.credentials._private_key_pkcs8_pem)
        payload = {
            "iss": service_account_email,
            "sub": service_account_email,
            "aud": "https://identitytoolkit.googleapis.com/google.identity.identitytoolkit.v1.IdentityToolkit",
            "uid": uid
        }
        if additional_claims:
            payload["claims"] = additional_claims
        exp = datetime.timedelta(minutes=60)
        return jwt.generate_jwt(payload, private_key, "RS256", exp)
    
    def sign_in_with_custom_token(self, token):
        request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyCustomToken?key={0}".format(
            self.api_key
        )
        headers = {"content-type": "application/json; charset=UTF-8"}
        data = json.dumps({"returnSecureToken": True, "token": token})
        request_object = requests.post(request_ref, headers=headers, data=data)
        raise_detailed_error(request_object)
        return request_object.json()
    
    def refresh(self, refresh_token):
        request_ref = "https://securetoken.googleapis.com/v1/token?key={0}".format(self.api_key)
        headers = {"content-type": "application/json; charset=UTF-8"}
        data = json.dumps({"grantType": "refresh_token", "refreshToken": refresh_token})
        request_object = requests.post(request_ref, headers=headers, data=data)
        raise_detailed_error(request_object)
        request_object_json = request_object.json()
        user = {
            "userId": request_object_json["user_id"],
            "idToken": request_object_json["id_token"],
            "refreshToken": request_object_json["refresh_token"]
        }
        return user
    
    def get_account_info(self, id_token):
        request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/getAccountInfo?key={0}".format(
            self.api_key
        )
        headers = {"content-type": "application/json; charset=UTF-8"}
        data = json.dumps({"idToken": id_token})
        request_object = requests.post(request_ref, headers=headers, data=data)
        raise_detailed_error(request_object)
        return request_object.json()
    
    def send_email_verification(self, id_token):
        request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/getOobConfirmationCode?key={0}".format(
            self.api_key
        )
        headers = {"content-type": "application/json; charset=UTF-8"}
        data = json.dumps({"requestType": "VERIFY_EMAIL", "idToken": id_token})
        request_object = requests.post(request_ref, headers=headers, data=data)
        raise_detailed_error(request_object)
        return request_object.json()
    
    def send_password_reset_email(self, email):
        request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/getOobConfirmationCode?key={0}".format(
            self.api_key
        )
        headers = {"content-type": "application/json; charset=UTF-8"}
        data = json.dumps({"requestType": "PASSWORD_RESET", "email": email})
        request_object = requests.post(request_ref, headers=headers, data=data)
        raise_detailed_error(request_object)
        return request_object.json()
    
    def verify_password_reset_code(self, reset_code, new_password):
        request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/resetPassword?key={0}".format(
            self.api_key
        )
        headers = {"content-type": "application/json; charset=UTF-8"}
        data = json.dumps({"oobCode": reset_code, "newPassword": new_password})
        request_object = requests.post(request_ref, headers=headers, data=data)
        raise_detailed_error(request_object)
        return request_object.json()
    
    def create_user_with_email_and_password(self, email, password):
        request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/signupNewUser?key={0}".format(
            self.api_key
        )
        headers = {"content-type": "application/json; charset=UTF-8"}
        data = json.dumps({"email": email, "password": password, "returnSecureToken": True})
        request_object = requests.post(request_ref, headers=headers, data=data)
        raise_detailed_error(request_object)
        return request_object.json()


class Database:
    """Database Service for Realtime Database"""
    def __init__(self, credentials, api_key, database_url, requests_session):
        if not database_url.endswith('/'):
            url = ''.join([database_url, '/'])
        else:
            url = database_url
        
        self.credentials = credentials
        self.api_key = api_key
        self.database_url = url
        self.requests = requests_session
        
        self.path = ""
        self.build_query = {}
        self.last_push_time = 0
        self.last_rand_chars = []
    
    def order_by_key(self):
        self.build_query["orderBy"] = "$key"
        return self
    
    def order_by_value(self):
        self.build_query["orderBy"] = "$value"
        return self
    
    def order_by_child(self, order):
        self.build_query["orderBy"] = order
        return self
    
    def start_at(self, start):
        self.build_query["startAt"] = start
        return self
    
    def end_at(self, end):
        self.build_query["endAt"] = end
        return self
    
    def equal_to(self, equal):
        self.build_query["equalTo"] = equal
        return self
    
    def limit_to_first(self, limit_first):
        self.build_query["limitToFirst"] = limit_first
        return self
    
    def limit_to_last(self, limit_last):
        self.build_query["limitToLast"] = limit_last
        return self
    
    def shallow(self):
        self.build_query["shallow"] = True
        return self
    
    def child(self, *args):
        new_path = "/".join([str(arg) for arg in args])
        if self.path:
            self.path += "/{}".format(new_path)
        else:
            if new_path.startswith("/"):
                new_path = new_path[1:]
            self.path = new_path
        return self
    
    def build_request_url(self, token):
        parameters = {}
        if token:
            parameters['auth'] = token
        for param in list(self.build_query):
            if type(self.build_query[param]) is str:
                parameters[param] = quote('"' + self.build_query[param] + '"')
            elif type(self.build_query[param]) is bool:
                parameters[param] = "true" if self.build_query[param] else "false"
            else:
                parameters[param] = self.build_query[param]
        request_ref = '{0}{1}.json?{2}'.format(self.database_url, self.path, urlencode(parameters))
        self.path = ""
        self.build_query = {}
        return request_ref
    
    def _get_access_token(self):
        """Get access token from credentials (supports both auth libraries)."""
        if self.credentials is None:
            return None
        
        if HAS_GOOGLE_AUTH and hasattr(self.credentials, 'token'):
            # google-auth credentials
            if not self.credentials.valid:
                from google.auth.transport.requests import Request
                self.credentials.refresh(Request())
            return self.credentials.token
        elif hasattr(self.credentials, 'get_access_token'):
            # oauth2client credentials
            return self.credentials.get_access_token().access_token
        return None
    
    def build_headers(self, token=None):
        headers = {"content-type": "application/json; charset=UTF-8"}
        if not token and self.credentials:
            access_token = self._get_access_token()
            if access_token:
                headers['Authorization'] = 'Bearer ' + access_token
        return headers
    
    def get(self, token=None, json_kwargs=None):
        if json_kwargs is None:
            json_kwargs = {}
        
        build_query = self.build_query.copy()
        query_key = self.path.split("/")[-1] if self.path else ""
        request_ref = self.build_request_url(token)
        headers = self.build_headers(token)
        request_object = self.requests.get(request_ref, headers=headers)
        raise_detailed_error(request_object)
        request_dict = request_object.json(**json_kwargs)
        
        if isinstance(request_dict, list):
            return PyreResponse(convert_list_to_pyre(request_dict), query_key)
        if not isinstance(request_dict, dict):
            return PyreResponse(request_dict, query_key)
        if not build_query:
            return PyreResponse(convert_to_pyre(request_dict.items()), query_key)
        if build_query.get("shallow"):
            return PyreResponse(request_dict.keys(), query_key)
        
        sorted_response = None
        if build_query.get("orderBy"):
            if build_query["orderBy"] == "$key":
                sorted_response = sorted(request_dict.items(), key=lambda item: item[0])
            elif build_query["orderBy"] == "$value":
                sorted_response = sorted(request_dict.items(), key=lambda item: item[1])
            else:
                sorted_response = sorted(
                    request_dict.items(),
                    key=lambda item: item[1].get(build_query["orderBy"], "")
                )
        else:
            sorted_response = request_dict.items()
        
        return PyreResponse(convert_to_pyre(sorted_response), query_key)
    
    def push(self, data, token=None, json_kwargs=None):
        if json_kwargs is None:
            json_kwargs = {}
        
        request_ref = self.check_token(self.database_url, self.path, token)
        self.path = ""
        headers = self.build_headers(token)
        request_object = self.requests.post(
            request_ref,
            headers=headers,
            data=json.dumps(data, **json_kwargs).encode("utf-8")
        )
        raise_detailed_error(request_object)
        return request_object.json()
    
    def set(self, data, token=None, json_kwargs=None):
        if json_kwargs is None:
            json_kwargs = {}
        
        request_ref = self.check_token(self.database_url, self.path, token)
        self.path = ""
        headers = self.build_headers(token)
        request_object = self.requests.put(
            request_ref,
            headers=headers,
            data=json.dumps(data, **json_kwargs).encode("utf-8")
        )
        raise_detailed_error(request_object)
        return request_object.json()
    
    def update(self, data, token=None, json_kwargs=None):
        if json_kwargs is None:
            json_kwargs = {}
        
        request_ref = self.check_token(self.database_url, self.path, token)
        self.path = ""
        headers = self.build_headers(token)
        request_object = self.requests.patch(
            request_ref,
            headers=headers,
            data=json.dumps(data, **json_kwargs).encode("utf-8")
        )
        raise_detailed_error(request_object)
        return request_object.json()
    
    def remove(self, token=None):
        request_ref = self.check_token(self.database_url, self.path, token)
        self.path = ""
        headers = self.build_headers(token)
        request_object = self.requests.delete(request_ref, headers=headers)
        raise_detailed_error(request_object)
        return request_object.json()
    
    def stream(self, stream_handler, token=None, stream_id=None):
        request_ref = self.build_request_url(token)
        return Stream(request_ref, stream_handler, self.build_headers, stream_id)
    
    def check_token(self, database_url, path, token):
        if token:
            return '{0}{1}.json?auth={2}'.format(database_url, path, token)
        else:
            return '{0}{1}.json'.format(database_url, path)
    
    def generate_key(self):
        push_chars = '-0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxyz'
        now = int(time.time() * 1000)
        duplicate_time = now == self.last_push_time
        self.last_push_time = now
        time_stamp_chars = [0] * 8
        for i in reversed(range(0, 8)):
            time_stamp_chars[i] = push_chars[now % 64]
            now = int(math.floor(now / 64))
        new_id = "".join(time_stamp_chars)
        if not duplicate_time:
            self.last_rand_chars = []
            for i in range(0, 12):
                self.last_rand_chars.append(int(math.floor(uniform(0, 1) * 64)))
        else:
            for i in range(0, 11):
                if self.last_rand_chars[i] == 63:
                    self.last_rand_chars[i] = 0
                else:
                    self.last_rand_chars[i] += 1
        for i in range(0, 12):
            new_id += push_chars[self.last_rand_chars[i]]
        return new_id


class Firestore:
    """Firestore Service using REST API"""
    
    def __init__(self, credentials=None, api_key=None, project_id=None, requests_session=None):
        self.credentials = credentials
        self.api_key = api_key
        self.project_id = project_id
        self.requests = requests_session or requests.Session()
        self.base_url = f"https://firestore.googleapis.com/v1/projects/{project_id}/databases/(default)/documents"
        
        self.path = ""
        self._query_filters = []
        self._query_orders = []
        self._query_limit = None
        self._query_offset = None
        self._collection_group = None
    
    def collection(self, collection_name):
        """Reference a Firestore collection"""
        self.path = f"{self.base_url}/{collection_name}"
        self._reset_query()
        return self
    
    def document(self, document_id=None):
        """Reference a document in the current collection"""
        if not self.path:
            raise ValueError("Must call .collection() before .document()")
        
        if document_id:
            self.path += f"/{document_id}"
        
        return self
    
    def subcollection(self, subcollection_name):
        """Reference a subcollection within the current document"""
        if not self.path:
            raise ValueError("Must call .document() before .subcollection()")
        
        self.path += f"/{subcollection_name}"
        self._reset_query()
        return self
    
    def collection_group(self, collection_name):
        """Query across all collections with the same name"""
        self.path = f"{self.base_url}:runQuery"
        self._collection_group = collection_name
        self._reset_query()
        return self
    
    def where(self, field, operator, value):
        """Filter documents with a where clause"""
        operator_map = {
            '==': 'EQUAL',
            '!=': 'NOT_EQUAL',
            '<': 'LESS_THAN',
            '<=': 'LESS_THAN_OR_EQUAL',
            '>': 'GREATER_THAN',
            '>=': 'GREATER_THAN_OR_EQUAL',
            'array_contains': 'ARRAY_CONTAINS',
            'in': 'IN',
            'not_in': 'NOT_IN',
            'array_contains_any': 'ARRAY_CONTAINS_ANY'
        }
        
        firestore_op = operator_map.get(operator)
        if not firestore_op:
            raise ValueError(f"Unsupported operator: {operator}")
        
        self._query_filters.append({
            'field': field,
            'op': firestore_op,
            'value': value
        })
        return self
    
    def order_by(self, field, direction='ASCENDING'):
        """Order query results"""
        self._query_orders.append({
            'field': field,
            'direction': direction.upper()
        })
        return self
    
    def limit(self, count):
        """Limit the number of query results"""
        self._query_limit = count
        return self
    
    def offset(self, count):
        """Skip a number of query results"""
        self._query_offset = count
        return self
    
    def add(self, data, token=None):
        """Add a new document with auto-generated ID"""
        if not self.path:
            raise ValueError("Must call .collection() before .add()")
        
        url = self.path
        headers = self._build_headers(token)
        firestore_data = {"fields": _convert_to_firestore_fields(data)}
        
        request_object = self.requests.post(url, headers=headers, data=json.dumps(firestore_data))
        raise_detailed_error(request_object)
        
        result = request_object.json()
        doc_name = result['name'].split('/')[-1]
        
        return {
            'id': doc_name,
            'path': result['name'],
            'update_time': result.get('updateTime'),
            'create_time': result.get('createTime')
        }
    
    def set(self, data, merge=False, token=None):
        """Set document data (creates or overwrites)"""
        self._ensure_document_path()
        
        url = self.path
        headers = self._build_headers(token)
        firestore_data = {"fields": _convert_to_firestore_fields(data)}
        
        params = {}
        if merge:
            params['updateMask.fieldPaths'] = list(data.keys())
        
        if params:
            url += '?' + urlencode(params, doseq=True)
        
        request_object = self.requests.patch(url, headers=headers, data=json.dumps(firestore_data))
        raise_detailed_error(request_object)
        return request_object.json()
    
    def get(self, token=None):
        """Get document(s) data"""
        # Check if we need to run a query
        if self._query_filters or self._query_orders or self._collection_group:
            return self._execute_query(token)
        
        url = self.path
        headers = self._build_headers(token)
        
        # Add API key for unauthenticated requests
        if not self.credentials and self.api_key and not token:
            params = {'key': self.api_key}
            url += '?' + urlencode(params)
        
        request_object = self.requests.get(url, headers=headers)
        raise_detailed_error(request_object)
        
        response = request_object.json()
        return _parse_firestore_response(response)
    
    def get_all(self, token=None):
        """Get all documents in the current collection"""
        return self.get(token)
    
    def get_by_id(self, document_id, token=None):
        """Get a specific document by ID"""
        if not self.path:
            raise ValueError("Must call .collection() before .get_by_id()")
        
        original_path = self.path
        self.path = f"{original_path}/{document_id}"
        result = self.get(token)
        self.path = original_path
        return result
    
    def update(self, data, token=None):
        """Update specific fields of a document"""
        self._ensure_document_path()
        
        url = self.path
        headers = self._build_headers(token)
        firestore_data = {"fields": _convert_to_firestore_fields(data)}
        
        params = {'updateMask.fieldPaths': list(data.keys())}
        url += '?' + urlencode(params, doseq=True)
        
        request_object = self.requests.patch(url, headers=headers, data=json.dumps(firestore_data))
        raise_detailed_error(request_object)
        return request_object.json()
    
    def delete(self, token=None):
        """Delete the current document"""
        self._ensure_document_path()
        
        url = self.path
        headers = self._build_headers(token)
        
        request_object = self.requests.delete(url, headers=headers)
        raise_detailed_error(request_object)
        return request_object.json()
    
    def batch(self):
        """Create a new batch write operation"""
        return BatchHelper(self)
    
    @staticmethod
    def server_timestamp():
        """Set a field to server timestamp"""
        return {"serverTimestamp": {}}
    
    @staticmethod
    def array_union(*values):
        """Add elements to an array field"""
        return {"arrayUnion": list(values)}
    
    @staticmethod
    def array_remove(*values):
        """Remove elements from an array field"""
        return {"arrayRemove": list(values)}
    
    @staticmethod
    def increment(value):
        """Increment a numeric field"""
        return {"incrementValue": value}
    
    @staticmethod
    def delete_field_value():
        """Delete a field when updating"""
        return {"deleteField": {}}
    
    def _build_headers(self, token=None):
        """Build request headers"""
        headers = {"content-type": "application/json; charset=UTF-8"}
        
        if token:
            headers['Authorization'] = f'Bearer {token}'
        elif self.credentials:
            access_token = self._get_access_token()
            if access_token:
                headers['Authorization'] = f'Bearer {access_token}'
        
        return headers
    
    def _get_access_token(self):
        """Get access token from credentials."""
        if self.credentials is None:
            return None
        
        try:
            if hasattr(self.credentials, 'token'):
                # google-auth credentials
                if not self.credentials.valid:
                    from google.auth.transport.requests import Request
                    self.credentials.refresh(Request())
                return self.credentials.token
            elif hasattr(self.credentials, 'get_access_token'):
                # oauth2client credentials
                return self.credentials.get_access_token().access_token
        except Exception:
            pass
        return None
    
    def _ensure_document_path(self):
        """Ensure we have a document path"""
        if not self.path or self.path.count('/') < 8:
            raise ValueError("Must call .collection().document() before this operation")
    
    def _reset_query(self):
        """Reset query parameters"""
        self._query_filters = []
        self._query_orders = []
        self._query_limit = None
        self._query_offset = None
        self._collection_group = None
    
    def _execute_query(self, token=None):
        """Execute a structured query"""
        if self._collection_group:
            url = f"{self.base_url}:runQuery"
        else:
            # Extract collection name from path
            if '/documents/' in self.path:
                url = self.path.rsplit('/', 1)[0] + ':runQuery'
            else:
                url = self.path + ':runQuery'
        
        headers = self._build_headers(token)
        
        query_data = {"structuredQuery": {}}
        
        # Set from clause
        if self._collection_group:
            query_data['structuredQuery']['from'] = [{
                'collectionId': self._collection_group,
                'allDescendants': True
            }]
        else:
            collection_name = self.path.split('/')[-1]
            query_data['structuredQuery']['from'] = [{'collectionId': collection_name}]
        
        # Set where clause
        if self._query_filters:
            filters = []
            for f in self._query_filters:
                filters.append({
                    'fieldFilter': {
                        'field': {'fieldPath': f['field']},
                        'op': f['op'],
                        'value': _convert_value_to_firestore(f['value'])
                    }
                })
            
            if len(filters) == 1:
                query_data['structuredQuery']['where'] = filters[0]
            else:
                query_data['structuredQuery']['where'] = {
                    'compositeFilter': {
                        'op': 'AND',
                        'filters': filters
                    }
                }
        
        # Set order by
        if self._query_orders:
            query_data['structuredQuery']['orderBy'] = [
                {
                    'field': {'fieldPath': o['field']},
                    'direction': o['direction']
                }
                for o in self._query_orders
            ]
        
        # Set limit and offset
        if self._query_limit:
            query_data['structuredQuery']['limit'] = self._query_limit
        
        if self._query_offset:
            query_data['structuredQuery']['offset'] = self._query_offset
        
        request_object = self.requests.post(
            url,
            headers=headers,
            data=json.dumps(query_data)
        )
        raise_detailed_error(request_object)
        
        return _parse_query_response(request_object.json())


class BatchHelper:
    """Helper for batch write operations"""
    
    def __init__(self, firestore_instance):
        self.fs = firestore_instance
        self.writes = []
    
    def set(self, collection_name, document_id, data, merge=False):
        """Add a set operation"""
        doc_path = f"{self.fs.base_url}/{collection_name}/{document_id}"
        write = {
            'update': {
                'name': doc_path,
                'fields': _convert_to_firestore_fields(data)
            }
        }
        if merge:
            write['updateMask'] = {'fieldPaths': list(data.keys())}
        self.writes.append(write)
        return self
    
    def update(self, collection_name, document_id, data):
        """Add an update operation"""
        doc_path = f"{self.fs.base_url}/{collection_name}/{document_id}"
        self.writes.append({
            'update': {
                'name': doc_path,
                'fields': _convert_to_firestore_fields(data)
            },
            'updateMask': {
                'fieldPaths': list(data.keys())
            }
        })
        return self
    
    def delete(self, collection_name, document_id):
        """Add a delete operation"""
        doc_path = f"{self.fs.base_url}/{collection_name}/{document_id}"
        self.writes.append({
            'delete': doc_path
        })
        return self
    
    def commit(self, token=None):
        """Execute all batch operations (max 500)"""
        if len(self.writes) > 500:
            raise ValueError("Maximum 500 operations per batch")
        
        commit_url = f"{self.fs.base_url}:commit"
        headers = self.fs._build_headers(token)
        
        request_object = self.fs.requests.post(
            commit_url,
            headers=headers,
            data=json.dumps({'writes': self.writes})
        )
        raise_detailed_error(request_object)
        return request_object.json()


def _convert_to_firestore_fields(data):
    """Convert Python dict to Firestore fields format"""
    if data is None:
        return {}
    
    fields = {}
    for key, value in data.items():
        fields[key] = _convert_value_to_firestore(value)
    return fields


def _convert_value_to_firestore(value):
    """Convert a Python value to Firestore Value format"""
    if isinstance(value, str):
        return {"stringValue": value}
    elif isinstance(value, bool):
        return {"booleanValue": value}
    elif isinstance(value, int):
        return {"integerValue": str(value)}
    elif isinstance(value, float):
        return {"doubleValue": value}
    elif isinstance(value, dict):
        if 'serverTimestamp' in value:
            return {"timestampValue": "REQUEST_TIME"}
        elif 'arrayUnion' in value:
            return {
                "arrayValue": {
                    "values": [_convert_value_to_firestore(v) for v in value['arrayUnion']]
                }
            }
        elif 'arrayRemove' in value:
            return {
                "arrayValue": {
                    "values": [_convert_value_to_firestore(v) for v in value['arrayRemove']]
                }
            }
        elif 'incrementValue' in value:
            return {"integerValue": str(value['incrementValue'])}
        elif 'deleteField' in value:
            return {"nullValue": None}
        else:
            return {"mapValue": {"fields": _convert_to_firestore_fields(value)}}
    elif isinstance(value, list):
        return {
            "arrayValue": {
                "values": [_convert_value_to_firestore(item) for item in value]
            }
        }
    elif value is None:
        return {"nullValue": None}
    else:
        return {"stringValue": str(value)}


def _parse_firestore_response(response):
    """Parse Firestore REST API response"""
    if 'fields' in response:
        return _parse_document(response)
    elif 'documents' in response:
        return [_parse_document(doc) for doc in response['documents']]
    elif 'name' in response and 'fields' not in response:
        return None
    return response


def _parse_document(doc):
    """Parse a single document"""
    result = _parse_fields(doc.get('fields', {}))
    doc_id = doc['name'].split('/')[-1]
    return {'id': doc_id, **result}


def _parse_fields(fields):
    """Parse fields from Firestore format"""
    result = {}
    for key, value in fields.items():
        result[key] = _extract_value(value)
    return result


def _extract_value(value):
    """Extract a value from Firestore Value format"""
    if 'stringValue' in value:
        return value['stringValue']
    elif 'booleanValue' in value:
        return value['booleanValue']
    elif 'integerValue' in value:
        return int(value['integerValue'])
    elif 'doubleValue' in value:
        return value['doubleValue']
    elif 'timestampValue' in value:
        return value['timestampValue']
    elif 'mapValue' in value:
        return _parse_fields(value['mapValue'].get('fields', {}))
    elif 'arrayValue' in value:
        return [_extract_value(v) for v in value['arrayValue'].get('values', [])]
    elif 'nullValue' in value:
        return None
    return None


def _parse_query_response(response):
    """Parse a query response"""
    results = []
    for item in response:
        if 'document' in item:
            results.append(_parse_document(item['document']))
    return results


class Storage:
    """Storage Service"""
    def __init__(self, credentials, storage_bucket, requests_session):
        self.storage_bucket = "https://firebasestorage.googleapis.com/v0/b/" + storage_bucket
        self.credentials = credentials
        self.requests = requests_session
        self.path = ""
        self.bucket = None
        if credentials:
            try:
                client = storage.Client(credentials=credentials, project=storage_bucket)
                self.bucket = client.get_bucket(storage_bucket)
            except Exception:
                self.bucket = None
    
    def child(self, *args):
        new_path = "/".join(args)
        if self.path:
            self.path += "/{}".format(new_path)
        else:
            if new_path.startswith("/"):
                new_path = new_path[1:]
            self.path = new_path
        return self
    
    def put(self, file, token=None):
        path = self.path
        self.path = None
        
        if isinstance(file, str):
            file_object = open(file, 'rb')
        else:
            file_object = file
        
        if token:
            request_ref = self.storage_bucket + "/o?name={0}".format(path)
            headers = {"Authorization": "Firebase " + token}
            request_object = self.requests.post(request_ref, headers=headers, data=file_object)
            raise_detailed_error(request_object)
            if isinstance(file, str):
                file_object.close()
            return request_object.json()
        elif self.credentials and self.bucket:
            blob = self.bucket.blob(path)
            if isinstance(file, str):
                result = blob.upload_from_filename(filename=file)
            else:
                result = blob.upload_from_file(file_obj=file)
            return result
        else:
            request_ref = self.storage_bucket + "/o?name={0}".format(path)
            request_object = self.requests.post(request_ref, data=file_object)
            raise_detailed_error(request_object)
            if isinstance(file, str):
                file_object.close()
            return request_object.json()
    
    def delete(self, name):
        if self.bucket:
            self.bucket.delete_blob(name)
    
    def download(self, filename, token=None):
        path = self.path
        self.path = None
        if path.startswith('/'):
            path = path[1:]
        
        if self.credentials and self.bucket:
            blob = self.bucket.get_blob(path)
            blob.download_to_filename(filename)
        else:
            url = "{0}/o/{1}?alt=media".format(self.storage_bucket, quote(path, safe=''))
            if token:
                url += "&token={0}".format(token)
            r = requests.get(url, stream=True)
            if r.status_code == 200:
                with open(filename, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
    
    def get_url(self, token=None):
        path = self.path
        self.path = None
        if path.startswith('/'):
            path = path[1:]
        if token:
            return "{0}/o/{1}?alt=media&token={2}".format(
                self.storage_bucket, quote(path, safe=''), token
            )
        return "{0}/o/{1}?alt=media".format(self.storage_bucket, quote(path, safe=''))
    
    def list_files(self):
        if self.bucket:
            return self.bucket.list_blobs()
        return []


def raise_detailed_error(request_object):
    try:
        request_object.raise_for_status()
    except HTTPError as e:
        raise HTTPError(e, request_object.text)


def convert_to_pyre(items):
    pyre_list = []
    for item in items:
        pyre_list.append(Pyre(item))
    return pyre_list


def convert_list_to_pyre(items):
    pyre_list = []
    for index, item in enumerate(items):
        pyre_list.append(Pyre([index, item]))
    return pyre_list


class PyreResponse:
    def __init__(self, pyres, query_key):
        self.pyres = pyres
        self.query_key = query_key
    
    def val(self):
        if isinstance(self.pyres, list):
            pyre_list = []
            if len(self.pyres) > 0 and isinstance(self.pyres[0].key(), int):
                for pyre in self.pyres:
                    pyre_list.append(pyre.val())
                return pyre_list
            for pyre in self.pyres:
                pyre_list.append((pyre.key(), pyre.val()))
            return OrderedDict(pyre_list)
        else:
            return self.pyres
    
    def key(self):
        return self.query_key
    
    def each(self):
        if isinstance(self.pyres, list):
            return self.pyres
        return []


class Pyre:
    def __init__(self, item):
        self.item = item
    
    def val(self):
        return self.item[1]
    
    def key(self):
        return self.item[0]


class KeepAuthSession(Session):
    """A session that doesn't drop Authentication on redirects between domains."""
    def rebuild_auth(self, prepared_request, response):
        pass


class ClosableSSEClient(SSEClient):
    def __init__(self, *args, **kwargs):
        self.should_connect = True
        super(ClosableSSEClient, self).__init__(*args, **kwargs)
    
    def _connect(self):
        if self.should_connect:
            super(ClosableSSEClient, self)._connect()
        else:
            raise StopIteration()
    
    def close(self):
        self.should_connect = False
        self.retry = 0
        try:
            if hasattr(self.resp.raw._fp, 'fp'):
                self.resp.raw._fp.fp.raw._sock.shutdown(socket.SHUT_RDWR)
                self.resp.raw._fp.fp.raw._sock.close()
        except Exception:
            pass


class Stream:
    def __init__(self, url, stream_handler, build_headers, stream_id):
        self.build_headers = build_headers
        self.url = url
        self.stream_handler = stream_handler
        self.stream_id = stream_id
        self.sse = None
        self.thread = None
        self.start()
    
    def make_session(self):
        session = KeepAuthSession()
        return session
    
    def start(self):
        self.thread = threading.Thread(target=self.start_stream, daemon=True)
        self.thread.start()
        return self
    
    def start_stream(self):
        try:
            self.sse = ClosableSSEClient(
                self.url,
                session=self.make_session(),
                build_headers=self.build_headers
            )
            for msg in self.sse:
                if msg:
                    try:
                        msg_data = json.loads(msg.data)
                        msg_data["event"] = msg.event
                        if self.stream_id:
                            msg_data["stream_id"] = self.stream_id
                        self.stream_handler(msg_data)
                    except json.JSONDecodeError:
                        continue
        except Exception:
            pass
    
    def close(self):
        if self.sse:
            self.sse.running = False
            self.sse.close()
        if self.thread:
            self.thread.join(timeout=5)
        return self