from mrjob.job import  MRJob
from mrjob.protocol import PickleProtocol as protocol

import sys
import ConfigParser
from diarizer import *

class ClusterMRJob(MRJob):

    INPUT_PROTOCOL = protocol
    OUTPUT_PROTOCOL = protocol

    def job_runner_kwargs(self):
        config = super(ClusterMRJob, self).job_runner_kwargs()
        config['hadoop_input_format'] =  "org.apache.hadoop.mapred.lib.NLineInputFormat"
        config['jobconf']['mapred.line.input.format.linespermap'] = 1
        config['cmdenv']['PYTHONPATH'] = ":".join([
            "/n/shokuji/da/penpornk/all"
        ])
        config['cmdenv']['~'] = "/n/shokuji/da/penpornk"
        config['cmdenv']['HOME'] = "/n/shokuji/da/penpornk"
        config['cmdenv']['MPLCONFIGDIR'] = "/n/shokuji/da/penpornk"
        config['cmdenv']['PATH'] = ":".join([
            "/n/shokuji/da/penpornk/env/gmm/bin",
            "/n/shokuji/da/penpornk/local/bin",
            "/usr/local/bin", "/usr/bin", "/bin",
            "/usr/X11/bin",
            "/usr/local64/lang/cuda-3.2/bin/",
            "/n/shokuji/da/penpornk/local/hadoop/bin"
        ])
        config['cmdenv']['LD_LIBRARY_PATH'] = ":".join([
            "/usr/lib64/atlas",
            "/usr/local64/lang/cuda-3.2/lib64",
            "/usr/local64/lang/cuda-3.2/lib",
            "/n/shokuji/da/penpornk/local/lib"
        ])
        config['cmdenv']['BLAS'] = "/usr/lib64/atlas/libptcblas.so"
        config['cmdenv']['LAPACK'] = "/usr/lib64/atlas/liblapack.so"
        config['cmdenv']['ATLAS'] = "/usr/lib64/atlas/libatlas.so"
        config['cmdenv']['C_INCLUDE_PATH'] = "/n/shokuji/da/penpornk/local/include"
        config['cmdenv']['CPLUS_INCLUDE_PATH'] = "/n/shokuji/da/penpornk/local/include"
        config['python_bin'] = "/n/shokuji/da/penpornk/env/gmm/bin/python"
        config['bootstrap_mrjob'] = False
        return config

    def hadoop_job_runner_kwargs(self):
        config = super(ClusterMRJob, self).hadoop_job_runner_kwargs()
        config['hadoop_extra_args'] += [
            "-verbose",
        #    "-mapdebug", "/n/shokuji/da/penpornk/diarizer/debug.sh"
        ]
        return config

    def mapper(self, key, _):
        device_id = 0
        config_file = '/n/shokuji/da/penpornk/all/medium.cfg'
        logfile = '/n/shokuji/da/penpornk/all/output/{0}.log'.format(key)
        log = open(logfile, 'w')
        tmp = sys.stdout
        sys.stdout = log

        try:
            open(config_file)
        except IOError, err:
            print "Error! Config file: '", config_file, "' does not exist"
            sys.exit(2)

        # Parse diarizer config file
        config = ConfigParser.ConfigParser()

        config.read(config_file)

        meeting_name, f, sp, outfile, gmmfile, num_gmms, num_comps, num_em_iters, kl_ntop, num_seg_iters_init, num_seg_iters, seg_length = get_config_params(config)

        #Overwrite with Map parameters
        meeting_name = key
        #f = '/n/shokuji/da/penpornk/full_experiment_sets/AMI/features_ff/{0}_seg.feat.gauss.htk'.format(meeting_name)
        f = '/u/drspeech/data/Aladdin/corpora/trecvid2011/events/E001/{0}.htk'.format(meeting_name)
        sp = False
        outfile = '/n/shokuji/da/penpornk/all/output/{0}.rttm'.format(meeting_name)
        gmmfile = '/n/shokuji/da/penpornk/all/output/{0}.gmm'.format(meeting_name)

        # Create tester object
        diarizer = Diarizer(f, sp)

        # Create the GMM list
        diarizer.new_gmm_list(num_comps, num_gmms, 'diag')

        # Cluster
        most_likely = diarizer.cluster(num_em_iters, kl_ntop, num_seg_iters_init, num_seg_iters, seg_length)

        # Write out RTTM and GMM parameter files
        diarizer.write_to_RTTM(outfile, sp, meeting_name, most_likely, num_gmms, seg_length)
        diarizer.write_to_GMM(gmmfile)

        sys.stdout = tmp
        log.close()
        yield 1, 1

def diarize( infilename ):
        return lambda key: ClusterMRJob.mapper(None, key, None)

def diarize_all( infilenames ):
        mr_args = ['-v', '--strict-protocols',
            '-r', 'hadoop',
            '--input-protocol', 'pickle',
            '--output-protocol','pickle',
            '--protocol','pickle'
        ]
        task_args = [protocol.write(name, None)+"\n" for name in meeting_names]
        job = ClusterMRJob(args=mr_args).sandbox(stdin=task_args)
        runner = job.make_runner()
        runner.run()


if __name__ == '__main__':
    ClusterMRJob.run()
