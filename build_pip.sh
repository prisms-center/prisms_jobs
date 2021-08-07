rm -r build dist
python setup.py bdist_wheel --universal
twine upload dist/* -r testpypi
