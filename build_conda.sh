# begin
anaconda login

# build, get location of result, upload
conda build conda-recipes/prisms_jobs > conda-recipes/tmp.out
LOCATION=$(grep 'conda upload' conda-recipes/tmp.out | cut -f3 -d ' ')
if [ -z $LOCATION ]; then
    LOCATION=$(grep 'Nothing to test for' conda-recipes/tmp.out | cut -f5 -d ' ')
fi
anaconda upload --user prisms-center $LOCATION

VERSION=`echo $LOCATION | perl -ne '/prisms-jobs-(.*)-/ && print $1'`

if [[ "$OSTYPE" == "linux-gnu" ]]; then
    # if on linux, convert to osx
    conda convert --platform osx-64 $LOCATION -o conda-recipes
    anaconda upload --user prisms-center conda-recipes/osx-64/prisms-jobs-$VERSION*
elif [[ "$OSTYPE" == "darwin"* ]]; then
    # if on osx, convert to linux
    conda convert --platform linux-64 $LOCATION -o conda-recipes
    anaconda upload --user prisms-center conda-recipes/linux-64/prisms-jobs-$VERSION*
fi

# finish
anaconda logout
