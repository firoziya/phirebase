from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name='phirebase',
    version='0.1.1',
    url='https://github.com/firoziya/phirebase',
    description='A simple python wrapper for the Firebase API with Authentication, Firestore, Realtime Database and Storage support',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Yash Kumar Firoziya',
    author_email='ykfiroziya@gmail.com',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
    keywords='Firebase Firestore Authentication Realtime Database Storage Python Wrapper',
    packages=find_packages(exclude=['tests', 'tests.*']),
    install_requires=[
        'requests>=2.20.0',
        'google-auth>=1.6.0',
        'google-auth-httplib2>=0.0.3',
        'google-cloud-storage>=1.30.0',
        'python-jwt>=3.3.0',
        'pycryptodome>=3.9.0',
        'six>=1.12.0',
    ],
    extras_require={
        'test': [
            'pytest>=7.0.0',
            'pytest-cov>=4.0.0',
            'pytest-mock>=3.10.0',
            'responses>=0.23.0',
            'requests-mock>=1.11.0',
            'mock>=5.0.0',
            'coverage>=7.0.0',
            'flake8>=6.0.0',
        ],
    },
    python_requires='>=3.6',
)