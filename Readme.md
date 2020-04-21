# Catcher for data pipelines testing
This is an example repo with [Airflow](https://airflow.apache.org/) pipeline and [Catcher](https://github.com/comtihon/catcher) test script. 
It shows how data pipelines can be easily tested. 

## Start dependencies
Start the dependencies with `docker-compose up -d`. It will run [docker-airflow](https://github.com/puckel/docker-airflow)
with local executor and mount `requirements.txt` and `dags` folder to the container. Airflow will install all
dependencies automatically and will discover the pipeline out of the box.

## Run the test
Test should be run in docker within the same network as the dependencies, as it [creates](https://catcher-modules.readthedocs.io/en/latest/source/airflow.html) 
Airflow's connections based on Catcher's inventory file. Catcher already has ready-to-use docker [image](https://hub.docker.com/repository/docker/comtihon/catcher)
which you can customize by mounting your own directories:
```
docker run --volume=$(pwd)/test:/opt/catcher/test \
           --volume=$(pwd)/resources:/opt/catcher/resources \
           --volume=$(pwd)/inventory:/opt/catcher/inventory \
           --network catcherairflowexample_default \
           catcher -i inventory/docker.yml test
```

## The pipeline
The pipeline is simple and artificial. It takes data from `Mysql`, pushes to `S3`, takes from `S3` 
and saves to `Postgres`: `Mysql` -> `S3` -> `Postgres`.  
Do not use it in real production.

## The test
1. The test creates and populates mysql table, which is being used as a data source for a pipeline.
2. Then in fills airflow connections with data from inventory and triggers the pipeline.
3. After pipeline is finished successfully it downloads file from S3 and checks if it matches the expected data.
4. The last test's step is to check if data, exported to postgres, is the correct one.
After all steps pass (or fail) it does the clean up by dropping tables and removing S3 file.

And the whole test is 72 lines length