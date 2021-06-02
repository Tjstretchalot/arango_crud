import setuptools   # pragma: no cover

with open("../README.md", "r") as fh:   # pragma: no cover
    long_description = fh.read()   # pragma: no cover

setuptools.setup(   # pragma: no cover
    name="arango_crud",
    version="1.0.5",
    author="Timothy Moore",
    author_email="mtimothy984+pypi@gmail.com",
    description="A wrapper around ArangoDB CRUD HTTP API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/tjstretchalot/arango_crud",
    packages=['arango_crud'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        'certifi',
        'chardet',
        'idna',
        'pytypeutils',
        'requests',
        'urllib3'
    ],
    python_requires='>=3.7',
)
