from os.path import realpath, dirname, join
from setuptools import setup, find_packages

PROJECT_ROOT = dirname(realpath(__file__))

REQUIREMENTS_FILE = join(PROJECT_ROOT, 'requirements.txt')

with open(REQUIREMENTS_FILE) as f:
    install_reqs = f.read().splitlines()

install_reqs.append('setuptools')

VERSION = '3.0.1'

setup(name='artem',
      version=VERSION,
      description='Chat bot engine for the VK communities',
      author='Pavel Karpovich',
      author_email='Chesh397@mail.ru',
      url='https://github.com/Tgjmjgj/artem',
      download_url = ('https://github.com/Tgjmjgj/artem/archive/' + 
            VERSION + '.tar.gz'),
      packages=find_packages(),
      include_package_data=True,
      install_requires=install_reqs,
      extras_require={},
      license='Apache 2.0',
      platforms='any',
      keywords=['vk','chat bot', 'bot core', 'bot', 'bot engine', 'vk bot'],
      classifiers=[
            'License :: OSI Approved :: Apache Software License',
            'Development Status :: 3 - Alpha',
            'Environment :: Console',
            'Intended Audience :: Developers',
            'Operating System :: Microsoft :: Windows',
            'Operating System :: Unix',
            'Programming Language :: Python :: 3 :: Only',
            'Programming Language :: Python :: 3.7',
            'Topic :: Scientific/Engineering :: Artificial Intelligence',
            'Topic :: Communications :: Chat'
      ],
      long_description="""
Simple core for creating chat bots in VK.com groups
=============
eMail: Chesh397@mail.ru
This project is hosted at https://github.com/Tgjmjgj/artem
""",
    long_description_content_type="text/markdown",
)