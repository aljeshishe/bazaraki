.PHONY: crawl sync docker_build docker_run docker_stop docker_logs fast syncback sync_force

# Existing commands
crawl:
	@echo "Running crawl task..."
	scrapy crawl property_spider -a  urls=https://www.bazaraki.com/real-estate-to-rent,https://www.bazaraki.com/real-estate-for-sale

sync:
	@echo "Running sync task..."
	aws s3 sync  output s3://ab-users/grachev/bazaraki/output

sync_force:
	@echo "Running sync task..."
	aws s3 sync  --delete output s3://ab-users/grachev/bazaraki/output

fast:
	scrapy crawl property_spider -a fast=1 -a urls=https://www.bazaraki.com/real-estate-to-rent,https://www.bazaraki.com/real-estate-for-sale

syncback:
	aws s3 sync s3://ab-users/grachev/bazaraki/output output

run_scheduled:
	schedule -s "0 0 */3 * *" "make crawl sync"

# Docker commands without Docker Compose
DOCKER_IMAGE_NAME=bazaraki
DOCKER_CONTAINER_NAME=bazaraki

docker_build:
	docker build -t $(DOCKER_IMAGE_NAME) .

docker_run: docker_build
	docker rm -f bazaraki && \
	docker run -d --name $(DOCKER_CONTAINER_NAME) --restart always -v $(PWD):/app $(DOCKER_IMAGE_NAME)

docker_stop:
	docker stop $(DOCKER_CONTAINER_NAME) || true
	docker rm $(DOCKER_CONTAINER_NAME) || true

docker_logs:
	docker logs -f $(DOCKER_CONTAINER_NAME)

docker_restart: docker_stop docker_run

