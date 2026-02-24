from setuptools import setup, find_packages

setup(
    name="jadegate",
    version="1.3.1",
    description="Deterministic Security for AI Agent Skills — 151 verified skills with Ed25519 signature chain",
    long_description=open("README.md", encoding="utf-8").read() if __import__("os").path.exists("README.md") else "",
    long_description_content_type="text/markdown",
    author="JadeGate",
    author_email="jadegate@users.noreply.github.com",
    url="https://github.com/JadeGate/jade-core",
    license="BSL-1.1",
    packages=find_packages(exclude=["tests", "tests.*"]),
    package_data={
        "jade_schema": ["*.json"],
        "jade_skills": ["*.json"],
        "jade_registry": ["*.json"],
    },
    include_package_data=True,
    python_requires=">=3.8",
    install_requires=[],
    extras_require={
        "dev": ["pytest>=7.0", "pytest-cov"],
    },
    entry_points={
        "console_scripts": [
            "jade=jade_core.cli:main",
            "jade-validate=jade_core.validator:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: Other/Proprietary License",
        "Programming Language :: Python :: 3",
        "Topic :: Security",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
)
