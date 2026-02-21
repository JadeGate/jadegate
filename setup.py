"""
Project JADE - Deterministic Security Protocol for AI Agents
The Package Manager and Immunity Network for AI Agents.
"""

from setuptools import setup, find_packages

setup(
    name="jade-protocol",
    version="1.0.0",
    description="Project JADE: Deterministic Security Protocol for AI Agents",
    long_description=open("README.md", encoding="utf-8").read() if __import__("os").path.exists("README.md") else "",
    long_description_content_type="text/markdown",
    author="Project JADE",
    url="https://github.com/project-jade/jade-protocol",
    license="MIT",
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
            "jade-validate=jade_core.validator:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Security",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
)
