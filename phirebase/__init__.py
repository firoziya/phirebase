from .phirebase import Phirebase, initialize_app

__version__ = '0.1.1'

__doc__ = """Phirebase is a simple python wrapper for the Firebase API with Authentication, Firestore, Realtime Database and Storage support. It provides an easy-to-use interface for interacting with Firebase services, allowing developers to easily integrate Firebase into their Python applications. With Phirebase, you can authenticate users, manage Firestore databases, interact with the Realtime Database, and handle file storage with ease. Whether you're building a web application, a mobile app, or a server-side application, Phirebase provides the tools you need to work with Firebase services in Python."""

__license__ = 'MIT'

__all__ = ['Phirebase', 'initialize_app']