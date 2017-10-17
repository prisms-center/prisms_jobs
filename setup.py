import glob
import os
from setuptools import setup, find_packages
from prisms_jobs import __version__

# get console_scripts
def script_str(file):
    name = os.path.splitext(os.path.split(file)[1])[0]
    return name + '=prisms_jobs.scripts.' + name + ':main'
console_scripts = [script_str(x) for x in glob.glob('prisms_jobs/scripts/*') if x != 'prisms_jobs/scripts/__init__.py']

setup(name='prisms_jobs', \
      version=__version__, \
      description='Job submission and management', \
      author='PRISMS Center and CASM developers',
      author_email='casm-developers@lists.engr.ucsb.edu',
      url='https://prisms-center.github.io/prisms_jobs_docs/', \
      packages=find_packages(),
      entry_points={
          'console_scripts': console_scripts
      },
      python_requires='>=2.7',
      install_requires=['future', 'six'],
      license='LGPL2.1+',
      classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: GNU Lesser General Public License v2 or later (LGPLv2+)',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Topic :: Scientific/Engineering',
        'Topic :: System :: Distributed Computing'
      ],
      data_files = [('', ['LICENSE', 'requirements.txt'])])
