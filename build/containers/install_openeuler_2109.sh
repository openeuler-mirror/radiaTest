#! /bin/sh

basearch=$(uname -m)

# install openeuler-21.09
wget https://repo.openeuler.org/openEuler-21.09/docker_img/"${basearch}"/openEuler-docker."${basearch}".tar.xz &&
	docker load < openEuler-docker."${basearch}".tar.xz

rm -rf openEuler-docker."${basearch}".tar.xz

