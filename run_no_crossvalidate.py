import multiprocessing
import concurrent.futures
import time
import gc
import numpy
import json
import random
from treesvm import SimBinarySVM
from treesvm.oaasvm import OAASVM
from treesvm.oaosvm import OAOSVM
from treesvm.dataset import Dataset
from treesvm.simbinarysvm_ori import SimBinarySVMORI
from treesvm.simmultisvm import SimMultiSVM

print('creating svm and testing with supplied test data')

num_workers = multiprocessing.cpu_count()
num_workers = 2
print('workers: ', num_workers)

training_files = [
    # ('pendigits', 'datasets/pendigits/pendigits.tra', 'datasets/pendigits/pendigits.tes', lambda row: (row[:-1], row[-1])),
    ('satimage', 'datasets/satimage/sat-train.csv', 'datasets/satimage/sat-test.csv', lambda row: (row[:-1], row[-1])),
    # ('letter', 'datasets/letter/letter-train.txt', 'datasets/letter/letter-test.txt', lambda row: (row[1:], row[0])),
]

for training in training_files:
    project_name = training[0]
    print('working on project: ', project_name)

    # load dataset
    given_adapter = None
    if len(training) > 3:
        given_adapter = training[3]

    training_file = training[1]
    print('train: ', training_file)
    training_set = Dataset.load(training_file, adapter=given_adapter)
    training_classes = Dataset.split(training_set)

    testing_file = training[2]
    print('test:  ', testing_file)
    testing_set = Dataset.load(testing_file, adapter=given_adapter)
    testing_classes = Dataset.split(testing_set)

    best = {}
    time_used = {}

    for each in (
            ('OAA', OAASVM),
            ('OAO', OAOSVM),
            ('SimBinarySVM_ORI', SimBinarySVMORI),
            ('SimBinarySVM', SimBinarySVM),
            ('SimMultiSVM', SimMultiSVM),
    ):

        svm_type = each[0]
        SVM = each[1]
        print('with: ', svm_type)

        best[svm_type] = {
            'gamma': None,
            'C': None,
            'accuracy': 0
        }

        time_used[svm_type] = 0

        start_time = time.process_time()

        # normally it's 9 steps each
        # gammas = numpy.logspace(-6, 2, 9)
        gammas = numpy.logspace(-6, 0, 7)
        print('gammas: ', gammas)
        # it's 9 steps
        # Cs = numpy.logspace(-2, 6, 9)
        Cs = numpy.logspace(-2, 4, 7)
        print('Cs: ', Cs)

        instance_cnt = gammas.size * Cs.size

        def instance(SVM, gamma, C):
            # force calling garbage collection (solves memory leaks)
            gc.collect()
            start_time = time.process_time()
            print('started gamma: ', gamma, ' C: ', C)
            svm = SVM(gamma=gamma, C=C)

            # start_time = time.process_time()
            svm.train(training_classes)
            # print('gamma: ', gamma, ' C: ', C, ' training time: %f' % (time.process_time() - start_time))

            # start_time = time.process_time()
            result = svm.test(testing_classes)
            testing_cnt = 0
            for name, points in testing_classes.items():
                testing_cnt += points.shape[0]
            # print('gamma: ', gamma, ' C: ', C, ' testing time: %f' % (time.process_time() - start_time))

            total = result[0]
            errors = result[1]
            total_itr = result[2]
            avg_itr = total_itr / testing_cnt
            accuracy = (total - errors) / total
            time_elapsed = time.process_time() - start_time

            print('finished! gamma: ', gamma, ' C:', C, ' accuracy: ', accuracy, ' avg_itr: ', avg_itr)
            print('time used: ', time_elapsed)
            return accuracy, total, errors, time_elapsed, avg_itr

        results = {}
        with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
            jobs = {}
            for gamma in gammas:
                for C in Cs:
                    jobs[executor.submit(instance, SVM, gamma, C)] = gamma, C
            # gamma, C
            for job in concurrent.futures.as_completed(jobs):
                gamma, C = jobs[job]
                accuracy, total, errors, time_elapsed, avg_itr = job.result()
                # store the result
                results[gamma] = {}
                results[gamma][C] = accuracy, total, errors, avg_itr
                time_used[svm_type] += time_elapsed / instance_cnt

                if accuracy > best[svm_type]['accuracy']:
                    tmp = best[svm_type]
                    tmp['accuracy'] = accuracy
                    tmp['C'] = C
                    tmp['gamma'] = gamma
                    tmp['avg_itr'] = avg_itr

        # show report after each svm type
        print('time elapsed: ', time.process_time() - start_time)
        print('results:')
        print('best of ', svm_type, ' with ', project_name)
        print('accuracy: ', best[svm_type]['accuracy'])
        print('best C: ', best[svm_type]['C'])
        print('best gamma: ', best[svm_type]['gamma'])
        print('best avg_itr: ', best[svm_type]['avg_itr'])
        print('time avg: ', time_used[svm_type])

        # save results into a file
        json.dump(results, open('results/' + project_name + '-' + svm_type + '.txt', 'w'))

    # sum up all the reports again
    for svm_type, each in best.items():
        print('best of ', svm_type, ' with ', project_name)
        print('accuracy: ', each['accuracy'])
        print('C": ', each['C'])
        print('gamma: ', each['gamma'])
        print('avg_itr: ', each['avg_itr'])
        print('time avg: ', time_used[svm_type])
    # save all the reports back to a file
    json.dump(best, open('results/' + project_name + '-best.txt', 'w'))
    json.dump(time_used, open('results/' + project_name + '-time.txt', 'w'))