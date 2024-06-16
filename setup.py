# setup.py

from setuptools import setup, find_packages

# 读取 README.md 文件内容，并使用 UTF-8 编码
with open('README.md', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='yunji', 
    version='0.1',
    author="Yun Song",
    author_email="ysp@cug.edu.cn",
    description="A PyQt5-based text editor",
    long_description=long_description,
    long_description_content_type='text/markdown',
    url="https://github.com/YSP0Github/yunji.git",
    packages=find_packages(),
    install_requires=[
        'PyQt5',
    ],
    entry_points={
        'console_scripts': [
            'yunji=yunji.editor:cli_editor',
        ],
    },
    package_data={
        'yunji': ['images/*.png'],  # 包含 images 文件夹下的所有 png 文件
    },
    include_package_data=True,  # 确保在安装包中包含非代码文件
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
