# function to allow passing conda build command line arguments
build_conda () {
  # build, get location of result, upload
  conda build $1 conda-recipes/prisms_jobs > conda-recipes/tmp.out
  LOCATION=$(grep 'conda upload' conda-recipes/tmp.out | cut -f3 -d ' ')
  if [ -z $LOCATION ]; then
      LOCATION=$(grep 'Nothing to test for' conda-recipes/tmp.out | cut -f5 -d ' ')
  fi
  anaconda upload --user prisms-center $LOCATION

  if [[ "$OSTYPE" == "linux-gnu" ]]; then
      OTHER=osx-64
  elif [[ "$OSTYPE" == "darwin"* ]]; then
      OTHER=linux-64
  fi
  
  # if on linux, convert to osx
  conda convert --platform $OTHER $LOCATION -o conda-recipes
  
  FILE=$(basename $LOCATION)
  anaconda upload --user prisms-center conda-recipes/$OTHER/$FILE
  
}

# begin
anaconda login

build_conda "--python 2.7"
build_conda "--python 3.6"

# finish
anaconda logout
