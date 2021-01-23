from setuptools import setup, find_packages

requires = [
    'python-telegram-bot',
    'pyyaml'
]

setup(
    name='mutex bot',
    version='0.1',
    description='telegram bot to simplify group use of exclusive resources',
    classifiers=[
        'Programming Language :: Python',
    ],
    author='atronah',
    author_email='atronah.ds@gmail.com',
    keywords='python telegram bot helper',
    packages=find_packages(),
    install_requires=requires,
)