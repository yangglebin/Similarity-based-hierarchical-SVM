from unittest import TestCase
import numpy
import random
from treesvm import SimBinarySVM
from treesvm.dataset import Dataset
import pytest

class TestSimBinarySVM(TestCase):
    training_file = '/Users/phizaz/Dropbox/waseda-internship/svm-implementations/simbinarysvm/satimage/sat-train-s.csv'
    training_set = Dataset.load(training_file)
    training_classes = Dataset.split(training_set)
    class_cnt = len(training_classes.keys())
    gamma = 1e-6
    C = 0.01
    svm = SimBinarySVM(gamma=gamma, C=C)

    # def test_MakeRBFKernel(self):
    #     self.fail()

    def test_find_separability(self):
        # svm = SimBinarySVM(Kernel)
        (self.svm.separability, self.svm.label_to_int, self.svm.int_to_label) = self.svm._find_separability(self.training_classes)
        # print('similarity', similarity)
        assert self.svm.separability.size == self.class_cnt * self.class_cnt
        assert self.svm.separability[0].size == self.class_cnt

        # print('labelToINt:', labelToInt)
        assert len(self.svm.label_to_int.keys()) == 6

        # print('intToLabel', intToLabel)
        for idx, val in enumerate(self.svm.int_to_label):
            assert self.svm.label_to_int[val] == idx

    @pytest.mark.run(after='test_find_separability')
    def test_construct_mst_graph(self):
        (self.svm.mst_graph, self.svm.mst_list) = self.svm._construct_mst_graph(self.training_classes, self.svm.separability)
        assert len(self.svm.mst_list) == self.class_cnt - 1
        assert len(self.svm.mst_graph.connected_with(0)) == self.class_cnt

        cnt = 0
        for i, row in enumerate(self.svm.mst_graph.connection):
            for j, dist in enumerate(row):
                if dist != float('inf'):
                    cnt += 1

        # the graph bidirectional
        assert cnt == (self.class_cnt - 1) * 2

    @pytest.mark.run(after='test_construct_mst_graph')
    def test_construct_tree(self):
        self.svm.tree = self.svm._construct_tree(self.svm.mst_graph, self.svm.mst_list)

        def runner(current):
            if current.left is None and current.right is None:
                return

            assert len(current.val) == len(current.left.val) + len(current.right.val)

            assert set(current.val) == set(current.left.val + current.right.val)

            runner(current.left)
            runner(current.right)

        runner(self.svm.tree.root)

    @pytest.mark.run(after='test_construct_tree')
    def test_train(self):
        self.svm.train(self.training_classes)

        def runner(current):
            if current.left is None and current.right is None:
                return

            assert current.svm
            runner(current.left)
            runner(current.right)

        runner(self.svm.tree.root)

    @pytest.mark.run(after='test_train')
    def test_predict(self):
        errors = 0
        total = 0
        for class_name, class_samples in self.training_classes.items():
            for sample in class_samples:
                total += 1
                if self.svm.predict(sample) != class_name:
                    # wrong prediction
                    errors += 1
        # just to see the idea
        print('errors:', errors, ' total:', total)
        assert errors == 0

    @pytest.mark.run(after='test_predict')
    def test_cross_validate(self):
        # 10 folds validation
        res = self.svm.cross_validate(10, self.training_classes)
        # this just to get the idea
        assert res == 0

    def test_make_gram_matrix(self):
        gamma = 0.1
        vectors = []
        training_classes_with_idx = {}
        idx = 0
        for name, points in self.training_classes.items():
            this_class = training_classes_with_idx[name] = []
            for point in points:
                # give it an index
                vector = point.tolist()
                vector_with_idx = [idx] + vector
                idx += 1
                vectors.append(vector)
                this_class.append(vector_with_idx)
            training_classes_with_idx[name] = numpy.array(this_class)

        vectors = numpy.array(vectors)
        kernel = self.svm.make_gram_matrix(vectors, gamma)

        def original_kernel(a, b):
            import numpy
            return numpy.exp(-gamma * numpy.linalg.norm(a - b) ** 2)

        for class_name, samples in training_classes_with_idx.items():
            a = samples
            b = a[:].tolist()
            random.shuffle(b)
            b = numpy.array(b)

            for i in range(a.shape[0]):
                assert abs(kernel(a[i], b[i]) - original_kernel(a[i][1:], b[i][1:])) < 1e-5

