from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable
from airflow.utils.dates import days_ago
from airflow.utils.task_group import TaskGroup

def print_hello():
    print('hello')
    return 

### DAG DE TEST ###

with DAG(
    dag_id='hello',
    schedule_interval=None,
    default_args={
        'owner': 'airflow',
        'start_date': days_ago(1)
    },
    tags=['training', 'regression', 'models'],
    catchup=False,
) as dag_1:
    
    hello_task = PythonOperator(
        task_id='say_hello',
        python_callable=print_hello,
    )