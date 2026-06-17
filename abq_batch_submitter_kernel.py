from abaqus import *
from abaqusConstants import *
import ast
import os


def _job_name(base, used):
    name = base.strip()
    if not name:
        name = 'untitled'
    name = name[:70]
    original = name
    index = 1
    while name in used:
        suffix = '_%d' % index
        name = original[:70 - len(suffix)] + suffix
        index += 1
    used.add(name)
    return name


def create_jobs(folder, files='[]', cpus=8, userSubroutine='', submitNow=True):
    folder = os.path.abspath(folder.strip().strip('"'))
    userSubroutine = userSubroutine.strip().strip('"')
    if userSubroutine:
        userSubroutine = os.path.abspath(userSubroutine)
    cpus = max(1, int(cpus))
    submitNow = bool(submitNow)

    inp_files = ast.literal_eval(files)
    if not inp_files:
        raise RuntimeError('No .inp files selected.')

    old_cwd = os.getcwd()
    os.chdir(folder)
    try:
        print 'Batch submitter: %d input file(s), cpus/job=%d' % (
            len(inp_files), cpus
        )

        used_names = set(mdb.jobs.keys())
        created = []
        for inp_file in inp_files:
            inp_file = os.path.basename(inp_file)
            inp_path = os.path.join(folder, inp_file)
            if not os.path.isfile(inp_path):
                raise RuntimeError('Input file does not exist: %s' % inp_path)

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

        if submitNow:
            for job in created:
                job.submit(consistencyChecking=OFF)
                print '[submitted] %s' % job.name

        print 'Batch submitter finished: %d job(s) created.' % len(created)
        print 'Use Job Manager to monitor, view results, or kill jobs.'
    finally:
        os.chdir(old_cwd)
