from setuptools import setup
import glob
from pbs import __version__
setup(name='casm-pbs', \
      version=__version__, \
      description='Cluster job submission and management', \
      author='CASM developers',
      author_email='casm-developers@lists.engr.ucsb.edu',
      url='https://github.com/prisms-center/pbs', \
      packages=['pbs', 'pbs.interface'],
      install_requires=['argparse'],
      scripts=glob.glob('scripts/*'),
      license='LGPL2.1+',
      classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: GNU Lesser General Public License v2 or later (LGPLv2+)',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Topic :: Scientific/Engineering',
        'Topic :: System :: Distributed Computing'
      ])
