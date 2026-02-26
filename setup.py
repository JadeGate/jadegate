"""
JadeGate — AI Tool Call Security Protocol
The TLS of AI tool calls.

pip install jadegate  ← 装完就生效，不需要任何配置
"""

from setuptools import setup, find_packages
from setuptools.command.install import install
from setuptools.command.develop import develop
import os


class PostInstall(install):
    """Post-install: auto-inject jadegate into all MCP clients."""
    def run(self):
        install.run(self)
        try:
            from jadegate.post_install import post_install
            post_install()
        except Exception:
            pass  # Never break pip install


class PostDevelop(develop):
    """Post-develop: same as install."""
    def run(self):
        develop.run(self)
        try:
            from jadegate.post_install import post_install
            post_install()
        except Exception:
            pass


setup(
    name="jadegate",
    version="2.0.0",
    description="JadeGate: AI Tool Call Security Protocol — The TLS of AI tool calls",
    long_description=open("README.md", encoding="utf-8").read() if os.path.exists("README.md") else "",
    long_description_content_type="text/markdown",
    author="Project JADE",
    url="https://github.com/JadeGate/jade-core",
    license="MIT",
    packages=find_packages(exclude=["tests", "tests.*"]),
    package_data={
        "jade_schema": ["*.json"],
        "jade_skills": ["*.json"],
        "jade_registry": ["*.json"],
        "jadegate": ["policy/*.json"],
    },
    include_package_data=True,
    python_requires=">=3.8",
    install_requires=[],
    extras_require={
        "dev": ["pytest>=7.0", "pytest-cov"],
    },
    entry_points={
        "console_scripts": [
            "jadegate=jadegate.cli:main",
            "jade-validate=jade_core.validator:main",
        ],
    },
    cmdclass={
        "install": PostInstall,
        "develop": PostDevelop,
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Security",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
)
