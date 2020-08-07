echo -- Get schain image --
version="1.46-develop.45"
RELEASE=${version}
docker pull skalenetwork/schain:$RELEASE
echo -- Get skale daemon from image --
docker create --name temp_container skalenetwork/schain:$RELEASE
docker cp temp_container:/skaled/skaled  ./jobs/runtime/skaled
docker rm temp_container
chmod +x ./jobs/runtime/skaled

python3 -m venv ./jobs/venv
. ./jobs/venv/bin/activate
pip install -r ./requirements.txt

. ./jobs/venv/bin/activate
SKTEST_EXE=./jobs/runtime/skaled NUM_NODES=2 pytest -vs sktest_long.py
