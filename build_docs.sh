python setup.py build_sphinx
rm -r ../prisms_jobs_docs/*
cp -r doc/build/html/* ../prisms_jobs_docs
cp doc/source/README.md ../prisms_jobs_docs/
cd ../prisms_jobs_docs && git add -u && git commit -m "rebuild" && git push
