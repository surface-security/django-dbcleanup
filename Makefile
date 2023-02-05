# test setup based on https://github.com/fopina/django-bulk-update-or-create/blob/master/Makefile
TEST_CONTAINER := django-dbcleanup-test

.PHONY: style
style:
	black --target-version=py36 \
	      --line-length=120 \
		  --skip-string-normalization \
		  dbcleanup testapp setup.py

.PHONY: style_check
style_check:
	black --target-version=py36 \
	      --line-length=120 \
		  --skip-string-normalization \
		  --check \
		  dbcleanup testapp setup.py

.PHONY: startmysql
startmysql:
	@docker inspect ${TEST_CONTAINER}-mysql | grep -q '"Running": true' || \
		docker run --name ${TEST_CONTAINER}-mysql \
		           -e MYSQL_ROOT_PASSWORD=root \
		           --rm -p 8877:3306 -d \
				   --health-cmd "mysqladmin ping" \
				   --health-interval 10s \
				   --health-timeout 5s \
				   --health-retries=5 \
				   mysql:8
	until [ "`docker inspect -f {{.State.Health.Status}} ${TEST_CONTAINER}-mysql`" == "healthy" ]; do sleep 0.1; done;

startpg:
	@docker inspect ${TEST_CONTAINER}-pg | grep -q '"Running": true' || \
		docker run --name ${TEST_CONTAINER}-pg \
		           -e POSTGRES_USER=postgres \
          		   -e POSTGRES_PASSWORD=postgres \
				   -e POSTGRES_DB=postgres \
		           --rm -p 8878:5432 -d \
				   --health-cmd pg_isready \
				   --health-interval 10s \
				   --health-timeout 5s \
				   --health-retries 5 \
				   postgres:11-alpine
	until [ "`docker inspect -f {{.State.Health.Status}} ${TEST_CONTAINER}-pg`" == "healthy" ]; do sleep 0.1; done;

testpg: startpg
	DJANGO_SETTINGS_MODULE="testapp.settings_postgresql" \
		testapp/manage.py test $${TEST_ARGS:-tests}

test: startmysql
	testapp/manage.py test $${TEST_ARGS:-tests}

coverage:
	PYTHONPATH="testapp" \
		python -b -W always -m coverage run testapp/manage.py test $${TEST_ARGS:-tests}
	coverage report
