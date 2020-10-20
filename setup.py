import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="callback-decorator-and-fs", # Replace with your own username
    version="0.0.5",
    author="Andre Fritzsche-Schwalbe",
    author_email="social@fritzsche-schwalbe.de",
    description="Callback decorator",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/and-fs/callback-decorator",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules"
    ],
    python_requires='>=3.8',
    tests_require=['unittest']
)