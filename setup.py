from setuptools import setup, find_packages

with open("README.md") as rd:
    readme_file = rd.read()


setup(
    name="zsh2xonsh",
    version="0.1.0-beta.1",
    python_requires=">=3.8",
    description="A highly-compatible translator from zsh -> xonsh",
    maintainer="Techcable",
    license="MIT",
    url="https://github.com/Techcable/zsh2xonsh",
    long_description=readme_file,
    long_description_content_type="text/markdown",
    install_requires=[
        "click",  # For argument processing
    ],
    package_dir={"": "src"},
    packages=find_packages("src", include=["zsh2xonsh*"]),
    entry_points={"console_scripts": {"zsh2xonsh = zsh2xonsh.__main__:zsh2xonsh"}},
    options={"bdist_wheel": {"universal": "1"}},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License",
        "Topic :: System :: Shells",
        "Topic :: System :: System Shells",
    ],
    keywords="shell xonsh zsh cli translate compat",
)
