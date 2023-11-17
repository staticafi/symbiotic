id=$(docker create symbiotic)
docker cp $id:/opt/symbiotic/install .
docker rm -v $id

rm -rf symbiotic_build
mv install symbiotic_build
zip -r symbiotic symbiotic_build
