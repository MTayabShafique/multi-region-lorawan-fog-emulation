###############################################
# Management Commands                        #
###############################################
start-all: start-environment start-sensiot
stop-all: stop-sensiot stop-environment

help:
	@echo 'Management commands for the SENSIOT Framework'
	@echo
	@echo 'Usage:'
	@echo '	start-all			Initializes required infrastructure and runs the framework'
	@echo '	stop-all			Stops the framework and required infrastructure'
	@echo
	@echo '	start-environment		Initializes required infrastructure'
	@echo '	stop-environment		Stops required infrastructure'
	@echo '	create-directories		Creates required directories to store data permanently on host'
	@echo '	create-networks			Creates required networks'
	@echo '	create-secrets			Creates required secrets'
	@echo '	create-infrastructure		Starts infrastructure services'
	@echo '	remove-directories		Removes directories for permanently data storage'
	@echo '	remove-networks			Removes networks'
	@echo '	remove-secrets			Removes secrets'
	@echo '	remove-infrastructure		Stops infrastructure services'
	@echo
	@echo '	start-sensiot			Starts SENSIOT services'
	@echo '	stop-sensiot			Stops SENSIOT services'
	@echo
	@echo '	adapt-hosts-file		Updates hostfile to browse SENSIOT services (for testing purposes)'
	@echo '	restore-hosts-file		Restores the hosts file'
	@echo

###############################################
# Configuration                               #
###############################################
DOCKER_USER?=r3r57
DOMAIN?=sensiot.de
IMAGE?=unibaub/sensiot
NETWORK_OPTIONS?=--opt encrypted --attachable --driver overlay
DIRECTORIES?=influxdb chronograf grafana prometheus memcached

###############################################
# Utility Functions                           #
###############################################
define start_service
	$(eval STACK_NAME=${1})
	$(eval COMPOSE_FILE=${2})
	@sed -e "s|{DOMAIN}|${DOMAIN}|g" templates/${COMPOSE_FILE} > ${COMPOSE_FILE}
	@sed -i -e "s|{IMAGE}|${IMAGE}|g" ${COMPOSE_FILE}
	@docker stack rm ${STACK_NAME} 2> /dev/null || true
	@docker stack deploy --with-registry-auth --prune --resolve-image never --compose-file ${COMPOSE_FILE} ${STACK_NAME}
	@rm ${COMPOSE_FILE}
endef

define stop_service
	$(eval STACK_NAME=${1})
	@echo ${STACK_NAME}
	@docker stack rm ${STACK_NAME} 2> /dev/null
endef

###############################################
# Start/Stop Environment                      #
###############################################
start-environment: create-directories create-networks create-secrets create-infrastructure
stop-environment: remove-infrastructure remove-secrets remove-networks

create-directories:
	$(foreach dir, ${DIRECTORIES}, mkdir -pv data/${dir};)
	-@echo Changing permissions... this might be a potential issue!
	-chmod 757 data/prometheus

create-networks:
	-@docker network create ${NETWORK_OPTIONS} traefik-net
	-@docker network create ${NETWORK_OPTIONS} memcache-net
	-@docker network create ${NETWORK_OPTIONS} influxdb-net
	-@docker network create ${NETWORK_OPTIONS} prometheus-net
	-@docker network ls -f scope=swarm

create-secrets:
	-@docker secret create sensiot.json config/sensiot.json
	-@docker secret create prometheus.yml config/prometheus/prometheus.yml
	-@docker secret create grafana.ini config/grafana/grafana.ini
	-@docker secret ls

create-infrastructure:
	$(call start_service,infrastructure,infrastructure.yml)

remove-directories:
	-@rm -rf data

remove-networks:
	-@docker network rm traefik-net
	-@docker network rm memcache-net
	-@docker network rm influxdb-net
	-@docker network rm prometheus-net

remove-secrets:
	-@docker secret rm sensiot.json
	-@docker secret rm prometheus.yml
	-@docker secret rm grafana.ini

remove-infrastructure:
	$(call stop_service,infrastructure)


###############################################
# Start/Stop SENSIOT                         #
###############################################
start-sensiot:
	-@echo Starting independent services...
	@#memcached
	$(call start_service,memcached,memcached.yml)
	@#influxdb
	$(call start_service,influxdb,influxdb.yml)
	@#prometheus
	$(call start_service,prometheus,prometheus.yml)

	-@echo Waiting 15 seconds for services to start...
	-@sleep 15

	-@echo Starting dependent services...
	@#chronograf
	$(call start_service,chronograf,chronograf.yml)
	@#grafana
	$(call start_service,grafana,grafana.yml)
	@#sensor data memcache writer
	$(call start_service,sensor-data-memcache-writer,sensor-data-memcache-writer.yml)
	@#influxdb writer
	$(call start_service,influxdb-writer,influxdb-writer.yml)
	@#prometheus writer
	$(call start_service,prometheus-writer,prometheus-writer.yml)
	@#web
	$(call start_service,web,web.yml)
	@#local manager
	$(call start_service,local-manager,local-manager.yml)

stop-sensiot:
	-@echo Shutting down dependent services...
	@#local manager
	$(call stop_service,local-manager)
	@#chronograf
	$(call stop_service,chronograf)
	@#grafana
	$(call stop_service,grafana)
	@#sensor data memcache writer
	$(call stop_service,sensor-data-memcache-writer)
	@#influxdb writer
	$(call stop_service,influxdb-writer)
	@#prometheus writer
	$(call stop_service,prometheus-writer)
	@#web
	$(call stop_service,web)

	-@echo Waiting 15 seconds for threads to finish...
	-@sleep 15

	-@echo Shutting down independent services...
	@#memcached
	$(call stop_service,memcached)
	@#influxdb
	$(call stop_service,influxdb)
	@#prometheus
	$(call stop_service,prometheus)

###############################################
# For Testing Purposes                        #
###############################################
adapt-hosts-file:
	$(eval LOCAL_IP=$(shell hostname -i))
	printf "\
	${LOCAL_IP} ${DOMAIN}\n\
	${LOCAL_IP} traefik.${DOMAIN}\n\
	${LOCAL_IP} grafana.${DOMAIN}\n\
	${LOCAL_IP} prometheus.${DOMAIN}\n\
	${LOCAL_IP} chronograf.${DOMAIN}\n\
	${LOCAL_IP} web.${DOMAIN}"\
	| sudo tee --append /etc/hosts

restore-hosts-file:
	sudo sed -i '/${DOMAIN}/d' /etc/hosts
