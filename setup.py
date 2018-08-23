from distutils.core import setup

setup(
    name='nginx-guard',
    version='0.1',
    #packages=['nginx-guard',],
    license='Creative Commons Attribution-Noncommercial-Share Alike license',
    long_description=open('README.md').read(),
    install_requires=[
        'requests',
        'pyyaml'
    ]
)
