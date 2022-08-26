from setuptools import setup, find_packages

requires = [
    'python-telegram-bot; python_version >= "3.7"',
    'python-telegram-bot <= 13.7 ; python_version < "3.7"'
    'pyyaml',
    'python-i18n[YAML]'
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
    entry_points={'console_scripts': [
        'mutex_bot = mutex_bot.bot:main',
    ]},
)