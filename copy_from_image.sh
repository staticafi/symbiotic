id=$(docker create symbiotic)
docker cp $id:/opt/symbiotic/install .
docker rm -v $id
