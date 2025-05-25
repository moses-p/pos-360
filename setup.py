from setuptools import setup, find_packages

setup(
    name="modern_pos",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "customtkinter==5.2.1",
        "pillow==10.2.0",
        "python-barcode==0.15.1",
        "reportlab==4.1.0",
        "pywin32==306",
        "tksheet==6.0.4"
    ],
    entry_points={
        'console_scripts': [
            'modern_pos=pos_system:main',
        ],
    },
    author="Ssemwanga Haruna Moses",
    author_email="arisegeniusug@gmail.com",
    description="A modern Point of Sale system with role-based access control",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    keywords="pos, point of sale, retail, inventory",
    url="https://github.com/yourusername/modern_pos",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
) 