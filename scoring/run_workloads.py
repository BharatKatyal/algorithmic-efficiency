"""
Example Usage:
python run_all_workloads.py --framework jax \
--experiment_basename my_first_experiment \
--docker_image_url <url_for_docker_image> \
--tag <some_docker_tag> \
--run_percentage 10 \
--submission_path <path_to_submission_py_file> \
--tuning_search_space <path_to_tuning_search_space_json> 
"""

from absl import flags
from absl import app
import os
import docker
import time 


flags.DEFINE_string('tag', None, 'Optional Docker image tag')
flags.DEFINE_string('docker_image_url', 'us-central1-docker.pkg.dev/training-algorithms-external/mlcommons-docker-repo/algoperf_jax_dev', 'URL to docker image') 
flags.DEFINE_integer('run_percentage', 100, 'Percentage of max num steps to run for.')
flags.DEFINE_string('experiment_basename', 'my_experiment', 'Name of top sub directory in experiment dir.')
flags.DEFINE_boolean('rsync_data', True, 'Whether or not to transfer the data from GCP w rsync.')
flags.DEFINE_boolean('local', False, 'Mount local algorithmic-efficiency repo.')
flags.DEFINE_string('submission_path',
                    'prize_qualification_baselines/external_tuning/jax_nadamw_full_budget.py',
                    'Path to reference submission.')
flags.DEFINE_string('tuning_search_space',
                    'prize_qualification_baselines/external_tuning/tuning_search_space.json',
                    'Path to tuning search space.')
flags.DEFINE_string('framework',
                    None,
                    'Can be either PyTorch or JAX.')
flags.DEFINE_boolean('dry_run', False, 'Whether or not to actually run the command')


FLAGS = flags.FLAGS


DATASETS = ['imagenet',
            'fastmri',
            'ogbg',
            'wmt',
            'librispeech',
            'criteo1tb']

WORKLOADS = {
             'imagenet_resnet': {'max_steps': 186_666,
                                 'dataset': 'imagenet'},
             'imagenet_vit': {'max_steps': 186_666,
                              'dataset': 'imagenet'},
             'fastmri': {'max_steps': 36_189,
                         'dataset': 'fastmri'},
             'ogbg': {'max_steps': 80_000,
                      'dataset': 'ogbg'},
             'wmt': {'max_steps': 133_333,
                     'dataset': 'wmt'},
             'librispeech_deepspeech': {'max_steps': 48_000,
                                        'dataset': 'librispeech'},
             'criteo1tb': {'max_steps': 10_666,
                           'dataset': 'criteo1tb'},
             'librispeech_conformer': {'max_steps': 80_000,
                                       'dataset': 'librispeech'},
             }

def container_running():
    docker_client = docker.from_env()
    containers = docker_client.containers.list()
    if len(containers) == 0:
        return False
    else:
        return True

def wait_until_container_not_running(sleep_interval=5*60):
    while container_running():
        time.sleep(sleep_interval)
    return 
    
def main(_):
    framework = FLAGS.framework
    algorithm = FLAGS.algorithm
    tag = f':{FLAGS.tag}' if FLAGS.tag is not None else ''
    run_fraction = FLAGS.run_percentage/100.
    experiment_basename=FLAGS.experiment_basename
    rsync_data = 'true' if FLAGS.rsync_data else 'false'
    docker_image_url = FLAGS.docker_image_url
    submission_path = FLAGS.submisison_path
    tuning_search_space = FLAGS.tuning_search_space

    # For each runnable workload check if there are any containers running and if not launch next container command
    for workload in WORKLOADS.keys():
        wait_until_container_not_running()
        os.system("sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'") # clear caches
        print('='*100)
        dataset = WORKLOADS[workload]['dataset']
        max_steps = int(WORKLOADS[workload]['max_steps'] * run_fraction)
        experiment_name = f'{experiment_basename}/{algorithm}'
        mount_repo_flag = ''
        if FLAGS.local:
            mount_repo_flag = '-v $HOME/algorithmic-efficiency:/algorithmic-efficiency '
        command = ('docker run -t -d -v $HOME/data/:/data/ '
                   '-v $HOME/experiment_runs/:/experiment_runs '
                   '-v $HOME/experiment_runs/logs:/logs '
                   f'{mount_repo_flag}'
                   '--gpus all --ipc=host '
                   f'{docker_image_url}{tag} '
                   f'-d {dataset} '
                   f'-f {framework} '
                   f'-s {submission_path} '
                   f'-w {workload} '
                   f'-t {tuning_search_space} '
                   f'-e {experiment_name} '
                   f'-m {max_steps} '
                   '-c false '
                   '-o true ' 
                   f'-r {rsync_data} '
                   '-i true ')
        if not FLAGS.dry_run:
            print('Running docker container command')
            print('Container ID: ')
            return_code = os.system(command)
        else:
            return_code = 0
        if return_code == 0:
            print(f'SUCCESS: container for {framework} {workload} {algorithm} launched successfully')
            print(f'Command: {command}')
            print(f'Results will be logged to {experiment_name}')
        else:
            print(f'Failed: container for {framework} {workload} {algorithm} failed with exit code {return_code}.')
            print(f'Command: {command}')
        wait_until_container_not_running()
        os.system("sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'") # clear caches

        print('='*100)


if __name__ == '__main__':
    flags.mark_flag_as_required('framework')
    flags.mark_flag_as_required()

    app.run(main)