#! /bin/sh

basearch=$(uname -m)

if [[ -f openEuler-docker."${basearch}".tar.xz ]];then
	rm -rf openEuler-docker."${basearch}".tar.xz
fi

# install openeuler-22.03-lts
wget https://repo.openeuler.org/openEuler-22.03-LTS/docker_img/"${basearch}"/openEuler-docker."${basearch}".tar.xz &&
	docker load < openEuler-docker."${basearch}".tar.xz


rm -rf openEuler-docker."${basearch}".tar.xz
