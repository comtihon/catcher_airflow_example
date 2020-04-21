import datetime
from tempfile import NamedTemporaryFile

import logging
from airflow.hooks.S3_hook import S3Hook
from airflow.hooks.mysql_hook import MySqlHook
from airflow.hooks.postgres_hook import PostgresHook
from airflow.models import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from pandas import DataFrame

postgres_conn_id = 'psql_conf'
mysql_conn_id = 'mysql_conf'
aws_conn_id = 's3_config'
mysql_tbl_name = 'my_table'
psql_tbl_name = 'psql_tbl'
bucket_name = 'my_awesome_bucket'
key_str = 'file_path_s3'


def mysql_to_s3(**context):
    mysql_hook = MySqlHook(mysql_conn_id=mysql_conn_id)
    s3_hook = S3Hook(aws_conn_id=aws_conn_id)
    sql = f'Select * from {mysql_tbl_name} order by email'
    df: DataFrame = mysql_hook.get_pandas_df(sql=sql)
    logging.info(df.head(n=1))
    cols: [str] = df.columns.values.tolist()
    with NamedTemporaryFile(newline='', mode='w+') as f:
        key_file = f"data/{mysql_tbl_name}/year={datetime.date.today().year}/" \
                   f"month={datetime.date.today().strftime('%m')}/" \
                   f"day={datetime.date.today().strftime('%d')}/" \
                   f"{mysql_tbl_name}.csv"
        df.to_csv(path_or_buf=f,
                  sep=",",
                  columns=cols,
                  index=False
                  )
        f.flush()
        s3_hook.load_file(filename=f.name,
                          key=key_file,
                          bucket_name=bucket_name)
        context["ti"].xcom_push(key=key_str, value=key_file)
        f.close()


def s3_to_psql(**context):
    ti = context["ti"]
    key_file = ti.xcom_pull(dag_id='simple_example_pipeline',
                            task_ids='mysql_to_s3',
                            key=key_str)
    psql_hook = PostgresHook(postgres_conn_id=postgres_conn_id)
    s3_hook = S3Hook(aws_conn_id=aws_conn_id)
    lines = s3_hook.read_key(key=key_file, bucket_name=bucket_name).split("\n")
    logging.info(f"lines length {len(lines)}")
    lines = [tuple(line.split(',')) for line in lines if line != '']
    df = DataFrame.from_records(data=lines[1:], columns=lines[0])
    df.to_sql(name=psql_tbl_name,
              con=psql_hook.get_sqlalchemy_engine(),
              if_exists="replace",
              index=False
              )

    logging.info(f"+++ content from file +++")


dag = DAG(
    dag_id='simple_example_pipeline',
    catchup=False,
    schedule_interval=None,
    max_active_runs=1,
    start_date=datetime.datetime(2019, 3, 10)
)

start = DummyOperator(
    task_id='start',
    dag=dag
)

mysql_to_s3 = PythonOperator(
    task_id='mysql_to_s3',
    python_callable=mysql_to_s3,
    retries=0,
    dag=dag,
    provide_context=True
)

s3_to_psql = PythonOperator(
    task_id='s3_to_psql',
    python_callable=s3_to_psql,
    retries=0,
    dag=dag,
    provide_context=True
)

end = DummyOperator(
    task_id='end',
    dag=dag
)

start >> mysql_to_s3 >> s3_to_psql >> end
