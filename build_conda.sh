# begin
anaconda login
conda config --set anaconda_upload yes

# build, get location of result, upload
conda build conda-recipes/prisms_jobs > conda-recipes/tmp.out
LOCATION=$(grep 'conda upload' conda-recipes/tmp.out | cut -f3 -d ' ')
if [ -z $LOCATION ]; then
    LOCATION=$(grep 'Nothing to test for' conda-recipes/tmp.out | cut -f5 -d ' ')
fi
anaconda upload --user prisms-center $LOCATION

# if on linux, convert to osx
conda convert --platform osx-64 $LOCATION -o conda-recipes
anaconda upload --user prisms-center conda-recipes/osx-64/prisms-jobs*

# if on osx, convert to linux
conda convert --platform linux-64 $LOCATION -o conda-recipes
anaconda upload --user prisms-center conda-recipes/linux-64/prisms-jobs*

# finish
conda config --set anaconda_upload no
anaconda logout
