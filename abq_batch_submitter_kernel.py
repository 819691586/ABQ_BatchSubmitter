from abaqus import *
from abaqusConstants import *
import ast
import os


INVALID_JOB_CHARS = set(" $&*~!()[]{}|:;'`\",.?/\\><")


def _clean_job_name(base):
    chars = []
    for char in base.strip():
        if char.isspace() or char in INVALID_JOB_CHARS:
            chars.append('_')
        else:
            chars.append(char)
    name = ''.join(chars)
    while '__' in name:
        name = name.replace('__', '_')
    name = name.strip('_ ')
    if not name:
        name = 'untitled'
    if name.startswith('-'):
        name = 'job_' + name.lstrip('-_ ')
    if name.lower() == 'assembly':
        name = 'job_assembly'
    return name[:80].rstrip('_ ')


def _job_name(base, used):
    name = _clean_job_name(base)
    original = name
    index = 1
    while name.lower() in used:
        suffix = '_%d' % index
        name = original[:80 - len(suffix)].rstrip('_ ') + suffix
        index += 1
    used.add(name.lower())
    return name


def create_jobs(folder, files='[]', cpus=8, userSubroutine='', submitNow=True):
    folder = os.path.abspath(folder.strip().strip('"'))
    if not os.path.isdir(folder):
        raise RuntimeError('Input folder does not exist: %s' % folder)

    userSubroutine = userSubroutine.strip().strip('"')
    if userSubroutine:
        userSubroutine = os.path.abspath(userSubroutine)
        if not os.path.isfile(userSubroutine):
            raise RuntimeError(
                'User subroutine does not exist: %s' % userSubroutine)

    cpus = int(cpus)
    if cpus < 1:
        raise RuntimeError('CPUs per job must be at least 1.')
    submitNow = bool(submitNow)

    inp_files = ast.literal_eval(files)
    if not isinstance(inp_files, (list, tuple)) or not inp_files:
        raise RuntimeError('No .inp files selected.')

    old_cwd = os.getcwd()
    os.chdir(folder)
    try:
        print 'Batch submitter: %d input file(s), cpus/job=%d' % (
            len(inp_files), cpus
        )

        used_names = set(name.lower() for name in mdb.jobs.keys())
        created = []
        failures = []
        for inp_file in inp_files:
            inp_file = os.path.basename(inp_file)
            inp_path = os.path.join(folder, inp_file)
            if not os.path.isfile(inp_path):
                failures.append((inp_file, 'create', 'input file not found'))
                print '[failed:create] %s: input file not found' % inp_file
                continue

            try:
                base = os.path.splitext(inp_file)[0]
                name = _job_name(base, used_names)
                args = {
                    'name': name,
                    'inputFileName': inp_path,
                    'type': ANALYSIS,
                    'multiprocessingMode': DEFAULT,
                    'numCpus': cpus,
                    'numDomains': cpus,
                }
                if userSubroutine:
                    args['userSubroutine'] = userSubroutine

                job = mdb.JobFromInputFile(**args)
                created.append(job)
                print '[created] %s <- %s' % (name, inp_path)
            except Exception as error:
                failures.append((inp_file, 'create', str(error)))
                print '[failed:create] %s: %s' % (inp_file, error)

        submitted = []
        if submitNow:
            for job in created:
                try:
                    job.submit(consistencyChecking=OFF)
                    submitted.append(job)
                    print '[submitted] %s' % job.name
                except Exception as error:
                    failures.append((job.name, 'submit', str(error)))
                    print '[failed:submit] %s: %s' % (job.name, error)
        elif created:
            print (
                'Jobs were created but not submitted. Set the Abaqus work '
                'directory to "%s" before submitting them.' % folder)

        print (
            'Batch submitter finished: %d created, %d submitted, %d failed.'
            % (len(created), len(submitted), len(failures)))
        for item, stage, message in failures:
            print '  - [%s] %s: %s' % (stage, item, message)
        print 'Use Job Manager to monitor, view results, or kill jobs.'
    finally:
        os.chdir(old_cwd)
