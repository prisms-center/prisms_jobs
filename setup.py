from setuptools import setup
import glob
from prisms_jobs import __version__
setup(name='prisms_jobs', \
      version=__version__, \
      description='Job submission and management', \
      author='PRISMS Center and CASM developers',
      author_email='casm-developers@lists.engr.ucsb.edu',
      url='https://prisms-center.github.io/prisms_jobs_docs/', \
      packages=['prisms_jobs', 'prisms_jobs.interface'],
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
