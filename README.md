# Phirebase 🔥

A simple, lightweight Python wrapper for the Firebase API with support for Authentication, Firestore, Realtime Database, and Storage.

[![PyPI version](https://badge.fury.io/py/phirebase.svg)](https://badge.fury.io/py/phirebase)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.6+](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/downloads/)

## Features

- 🔐 **Authentication** - Email/Password, Custom Tokens, OAuth, and more
- 📄 **Firestore** - Full CRUD operations with querying, filtering, and batch writes
- 📊 **Realtime Database** - Real-time data synchronization with streaming support
- 📦 **Storage** - File upload, download, and management
- 🔑 **Service Account Support** - Admin SDK capabilities with service accounts
- 🚀 **Lightweight** - Minimal dependencies, easy to install
- 🔄 **REST API Based** - Firestore uses REST API for broader compatibility

## Installation

### Using pip

```bash
pip install phirebase
```

### From source

```bash
git clone https://github.com/firoziya/phirebase.git
cd phirebase
pip install -e .
```

### Dependencies

- `requests` - HTTP library
- `google-auth` - Google authentication
- `google-cloud-storage` - Cloud Storage client
- `python-jwt` - JWT token generation
- `pycryptodome` - Cryptographic operations
- `oauth2client` - OAuth 2.0 support

## Quick Start

### Basic Setup

```python
from phirebase import initialize_app

config = {
    "apiKey": "your-api-key",
    "authDomain": "your-project.firebaseapp.com",
    "databaseURL": "https://your-project.firebaseio.com",
    "storageBucket": "your-project.appspot.com",
    "projectId": "your-project-id"
}

firebase = initialize_app(config)
```

### With Service Account (Admin SDK)

```python
config = {
    "apiKey": "your-api-key",
    "authDomain": "your-project.firebaseapp.com",
    "databaseURL": "https://your-project.firebaseio.com",
    "storageBucket": "your-project.appspot.com",
    "projectId": "your-project-id",
    "serviceAccount": "path/to/serviceAccountKey.json"  # or dict
}

firebase = initialize_app(config)
```

## Authentication

### Create User

```python
auth = firebase.auth()

# Create user with email and password
user = auth.create_user_with_email_and_password("user@example.com", "securePassword123")
print(user["idToken"])
```

### Sign In

```python
# Sign in with email and password
user = auth.sign_in_with_email_and_password("user@example.com", "securePassword123")

# Get account info
info = auth.get_account_info(user["idToken"])
print(info)
```

### Custom Token Authentication

```python
# Create custom token (requires service account)
custom_token = auth.create_custom_token(
    uid="user123",
    additional_claims={"premium": True}
)

# Sign in with custom token
user = auth.sign_in_with_custom_token(custom_token.decode("utf-8"))
```

### Password Management

```python
# Send password reset email
auth.send_password_reset_email("user@example.com")

# Verify reset code and set new password
auth.verify_password_reset_code("reset-code", "newSecurePassword123")
```

### Email Verification

```python
# Send email verification
auth.send_email_verification(id_token)
```

### Token Refresh

```python
# Refresh ID token
refreshed_user = auth.refresh(refresh_token)
```

## Firestore

### Collections & Documents

```python
db = firebase.firestore()

# Get a collection reference
users_ref = db.collection("users")

# Get all documents in a collection
all_users = users_ref.get()
for user in all_users:
    print(user["id"], user.get("name"))
```

### Adding Documents

```python
# Add document with auto-generated ID
result = db.collection("users").add({
    "name": "Morty Smith",
    "age": 14,
    "email": "morty@example.com",
    "active": True
})
print(f"Document ID: {result['id']}")

# Add with nested data
db.collection("users").add({
    "name": "Rick Sanchez",
    "age": 70,
    "address": {
        "street": "123 Portal Lane",
        "city": "Seattle",
        "dimension": "C-137"
    },
    "tags": ["genius", "scientist", "grandfather"]
})
```

### Setting Documents

```python
# Set document with specific ID (overwrites)
db.collection("users").document("user123").set({
    "name": "Summer Smith",
    "age": 17
})

# Set with merge (updates only specified fields)
db.collection("users").document("user123").set({
    "age": 18
}, merge=True)
```

### Getting Documents

```python
# Get a single document
user = db.collection("users").document("user123").get()
if user:
    print(user["name"], user["age"])

# Get document by ID
user = db.collection("users").get_by_id("user123")

# Get all documents
all_users = db.collection("users").get_all()
```

### Updating Documents

```python
# Update specific fields
db.collection("users").document("user123").update({
    "age": 19,
    "active": False
})
```

### Deleting Documents

```python
# Delete a document
db.collection("users").document("user123").delete()
```

### Subcollections

```python
# Access subcollection
posts = db.collection("users").document("user123").subcollection("posts")

# Add to subcollection
posts.add({
    "title": "My First Post",
    "content": "Hello world!",
    "created_at": db.server_timestamp()
})

# Get all posts
all_posts = posts.get()
```

### Querying Data

```python
# Where clause examples
results = db.collection("users") \
    .where("age", ">=", 18) \
    .where("active", "==", True) \
    .get()

# Order by
results = db.collection("users") \
    .order_by("age", "DESCENDING") \
    .limit(10) \
    .get()

# Array contains
results = db.collection("users") \
    .where("tags", "array_contains", "premium") \
    .get()

# In query
results = db.collection("users") \
    .where("status", "in", ["active", "pending"]) \
    .get()

# Combined queries
results = db.collection("products") \
    .where("price", "<=", 100) \
    .where("category", "==", "electronics") \
    .order_by("price", "DESCENDING") \
    .limit(5) \
    .get()

# Collection group queries
results = db.collection_group("posts") \
    .where("published", "==", True) \
    .get()
```

### Supported Query Operators

| Operator | Description |
|----------|-------------|
| `==` | Equal to |
| `!=` | Not equal to |
| `<` | Less than |
| `<=` | Less than or equal to |
| `>` | Greater than |
| `>=` | Greater than or equal to |
| `array_contains` | Array contains value |
| `in` | Value in array |
| `not_in` | Value not in array |
| `array_contains_any` | Array contains any of the values |

### Special Field Values

```python
# Server timestamp
db.collection("posts").add({
    "title": "Hello",
    "created_at": db.server_timestamp()
})

# Array union (add unique elements)
db.collection("users").document("user123").update({
    "tags": db.array_union("new_tag", "another_tag")
})

# Array remove
db.collection("users").document("user123").update({
    "tags": db.array_remove("old_tag")
})

# Increment numeric value
db.collection("users").document("user123").update({
    "login_count": db.increment(1),
    "balance": db.increment(-50.0)
})

# Delete a field
db.collection("users").document("user123").update({
    "temporary_field": db.delete_field_value()
})
```

### Batch Writes

```python
batch = db.batch()

# Add multiple operations
batch.set("users", "user1", {"name": "Morty", "age": 14})
batch.update("users", "user2", {"age": 35})
batch.delete("users", "user3")
batch.set("posts", "post1", {"title": "First Post"})

# Commit all operations (max 500)
result = batch.commit()
```

## Realtime Database

### Basic Operations

```python
rtdb = firebase.database()

# Set data
rtdb.child("users").child("user1").set({
    "name": "Morty Smith",
    "age": 14
})

# Push data (auto-generated key)
result = rtdb.child("posts").push({
    "title": "Hello World",
    "content": "My first post"
})
print(result["name"])  # Auto-generated key

# Update specific fields
rtdb.child("users").child("user1").update({
    "age": 15
})

# Get data
user = rtdb.child("users").child("user1").get()
print(user.val())  # OrderedDict with data

# Delete data
rtdb.child("users").child("user1").remove()
```

### Querying

```python
# Order by key
results = rtdb.child("users") \
    .order_by_key() \
    .limit_to_first(10) \
    .get()

# Order by value
results = rtdb.child("scores") \
    .order_by_value() \
    .limit_to_last(5) \
    .get()

# Order by child
results = rtdb.child("users") \
    .order_by_child("age") \
    .start_at(18) \
    .end_at(65) \
    .get()

# Equal to
results = rtdb.child("users") \
    .order_by_child("name") \
    .equal_to("Morty Smith") \
    .get()

# Shallow query (keys only)
keys = rtdb.child("users") \
    .shallow() \
    .get()

# Iterate results
for item in results.each():
    print(item.key(), item.val())
```

### Generate Keys

```python
# Generate a unique key without pushing data
key = rtdb.generate_key()
print(key)  # e.g., "-Mx2sKL9pQrT8YhN3vWb"
```

### Real-time Streaming

```python
def stream_handler(message):
    """Handle real-time updates"""
    event_type = message.get("event")  # "put", "patch", etc.
    data = message.get("data")
    path = message.get("path")
    
    print(f"Event: {event_type}")
    print(f"Path: {path}")
    print(f"Data: {data}")
    print("-" * 50)

# Start streaming
my_stream = rtdb.child("users").stream(stream_handler)

# Keep the program running
import time
time.sleep(60)

# Stop streaming
my_stream.close()
```

## Storage

### Upload Files

```python
storage = firebase.storage()

# Upload from file path
storage.child("images/profile.jpg").put("local_image.jpg")

# Upload from file object
with open("document.pdf", "rb") as f:
    storage.child("documents/report.pdf").put(f)

# Upload with authentication token
storage.child("private/file.txt").put("local_file.txt", token=user_token)
```

### Download Files

```python
# Download file
storage.child("images/profile.jpg").download("downloaded_image.jpg")

# Download with token
storage.child("private/file.txt").download("file.txt", token=user_token)
```

### Get Download URL

```python
# Get public URL
url = storage.child("images/profile.jpg").get_url()
print(url)

# Get authenticated URL
url = storage.child("private/file.txt").get_url(token=user_token)
print(url)
```

### Delete Files

```python
# Delete file (requires service account)
storage.delete("images/old_picture.jpg")
```

### List Files

```python
# List all files (requires service account)
files = storage.list_files()
for file in files:
    print(file.name)
```

## Working with Authentication Tokens

```python
# Sign in and get token
auth = firebase.auth()
user = auth.sign_in_with_email_and_password("user@example.com", "password")
id_token = user["idToken"]

# Use token for authenticated operations
db = firebase.firestore()
user_data = db.collection("protected_collection").get(token=id_token)

# Use token with Realtime Database
rtdb = firebase.database()
data = rtdb.child("protected_path").get(token=id_token)

# Use token with Storage
storage = firebase.storage()
storage.child("private/file.txt").download("file.txt", token=id_token)
```

## Complete Example

```python
from phirebase import initialize_app
import json

# Initialize Firebase
config = {
    "apiKey": "your-api-key",
    "authDomain": "your-project.firebaseapp.com",
    "databaseURL": "https://your-project.firebaseio.com",
    "storageBucket": "your-project.appspot.com",
    "projectId": "your-project-id",
    "serviceAccount": "serviceAccountKey.json"
}

firebase = initialize_app(config)

# Authentication
auth = firebase.auth()
try:
    user = auth.sign_in_with_email_and_password("user@example.com", "password123")
    print("Logged in successfully!")
except:
    print("Login failed!")

# Firestore Operations
db = firebase.firestore()

# Add a document
result = db.collection("posts").add({
    "title": "My First Post",
    "content": "Hello Firebase!",
    "author": "user123",
    "created_at": db.server_timestamp(),
    "tags": ["firebase", "python"],
    "likes": 0,
    "published": True
})
print(f"Post created with ID: {result['id']}")

# Query posts
recent_posts = db.collection("posts") \
    .where("published", "==", True) \
    .order_by("created_at", "DESCENDING") \
    .limit(5) \
    .get()

for post in recent_posts:
    print(f"{post['title']} - {post['likes']} likes")

# Update a post
db.collection("posts").document(result['id']).update({
    "likes": db.increment(1),
    "tags": db.array_union("tutorial")
})

# Real-time Database Operations
rtdb = firebase.database()

# Set up real-time listener
def handle_message(message):
    print(f"Event: {message['event']}")
    print(f"Data: {message['data']}")

stream = rtdb.child("notifications").stream(handle_message)

# Push notification
rtdb.child("notifications").push({
    "message": "Welcome to Phirebase!",
    "timestamp": {"serverTimestamp": {}},
    "read": False
})

# Storage Operations
storage = firebase.storage()

# Upload file
with open("image.jpg", "rb") as f:
    storage.child("images/photo.jpg").put(f)

# Get download URL
url = storage.child("images/photo.jpg").get_url()
print(f"File URL: {url}")

# Clean up
import time
time.sleep(5)
stream.close()
```

## Error Handling

```python
from requests.exceptions import HTTPError

try:
    # Attempt operation
    result = db.collection("users").document("user123").get()
except HTTPError as e:
    print(f"HTTP Error: {e}")
    print(f"Response: {e.response.text}")
except ValueError as e:
    print(f"Value Error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Project Structure

```
phirebase/
├── __init__.py          # Package initialization
├── phirebase.py          # Main Firebase wrapper
├── sseclient.py          # Server-Sent Events client
├── README.md             # Documentation
└── setup.py              # Package setup
```

## API Reference

### Phirebase Class

The main entry point for all Firebase services.

```python
firebase = initialize_app(config)
```

| Method | Returns | Description |
|--------|---------|-------------|
| `auth()` | `Auth` | Authentication service |
| `database()` | `Database` | Realtime Database service |
| `firestore()` | `Firestore` | Firestore service |
| `storage()` | `Storage` | Storage service |

### Auth Class

| Method | Description |
|--------|-------------|
| `create_user_with_email_and_password(email, password)` | Create new user |
| `sign_in_with_email_and_password(email, password)` | Sign in user |
| `create_custom_token(uid, additional_claims)` | Create custom token |
| `sign_in_with_custom_token(token)` | Sign in with custom token |
| `refresh(refresh_token)` | Refresh ID token |
| `get_account_info(id_token)` | Get user account info |
| `send_email_verification(id_token)` | Send verification email |
| `send_password_reset_email(email)` | Send password reset email |
| `verify_password_reset_code(code, new_password)` | Reset password |

### Firestore Class

| Method | Description |
|--------|-------------|
| `collection(name)` | Reference a collection |
| `document(id)` | Reference a document |
| `subcollection(name)` | Reference a subcollection |
| `collection_group(name)` | Collection group query |
| `add(data)` | Add document with auto-ID |
| `set(data, merge=False)` | Set document data |
| `get()` | Get document(s) |
| `get_all()` | Get all documents |
| `get_by_id(id)` | Get document by ID |
| `update(data)` | Update document fields |
| `delete()` | Delete document |
| `where(field, op, value)` | Filter query |
| `order_by(field, direction)` | Order results |
| `limit(count)` | Limit results |
| `offset(count)` | Offset results |
| `batch()` | Create batch write |

### Database Class

| Method | Description |
|--------|-------------|
| `child(*args)` | Reference a path |
| `set(data)` | Set data at path |
| `push(data)` | Push data with auto-key |
| `update(data)` | Update specific fields |
| `get()` | Get data |
| `remove()` | Delete data |
| `generate_key()` | Generate unique key |
| `stream(handler, stream_id)` | Real-time streaming |
| `order_by_key()` | Order by key |
| `order_by_value()` | Order by value |
| `order_by_child(field)` | Order by child field |
| `start_at(value)` | Start query at value |
| `end_at(value)` | End query at value |
| `equal_to(value)` | Filter by equality |
| `limit_to_first(n)` | Limit to first n |
| `limit_to_last(n)` | Limit to last n |
| `shallow()` | Keys only query |

### Storage Class

| Method | Description |
|--------|-------------|
| `child(*args)` | Reference a path |
| `put(file, token)` | Upload file |
| `download(filename, token)` | Download file |
| `get_url(token)` | Get download URL |
| `delete(name)` | Delete file |
| `list_files()` | List all files |

## Limitations

- **Firestore Transactions**: Not yet implemented in this version
- **Batch Writes**: Maximum 500 operations per batch (Firebase limit)
- **Real-time Listeners**: Only supported for Realtime Database
- **Query Results**: Limited to Firebase's default page sizes

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
# Clone the repository
git clone https://github.com/firoziya/phirebase.git
cd phirebase

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install development dependencies
pip install -e ".[dev]"

# Run tests
python -m pytest tests/
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Firebase](https://firebase.google.com/) - Google's mobile platform
- [Pyrebase](https://github.com/thisbejim/Pyrebase) - Original inspiration
- [Firebase REST API](https://firebase.google.com/docs/reference/rest) - API documentation

## Support

- **Issues**: [GitHub Issues](https://github.com/firoziya/phirebase/issues)
- **Email**: ykfiroziya@gmail.com
- **Documentation**: [Wiki](https://github.com/firoziya/phirebase/wiki)

## Changelog

### v0.1.0 (Initial Release)
- Authentication (Email/Password, Custom Tokens)
- Firestore CRUD operations with querying
- Realtime Database with streaming
- Cloud Storage operations
- Service account support
- Batch write operations
- Special field values (timestamps, arrays, increments)

---

**Made with ❤️ by Yash Kumar Firoziya**