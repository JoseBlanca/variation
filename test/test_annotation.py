
import unittest
import numpy

from variation.variations.vars_matrices import VariationsArrays, VariationsH5
from variation import GT_FIELD, MISSING_INT, TRUE_INT, FALSE_INT
from variation.variations.annotation import is_variable, IsVariableAnnotator, \
    ANNOTATED_VARS
from test.test_utils import TEST_DATA_DIR
from os.path import join


class IsVariableTest(unittest.TestCase):

    def test_is_variable_func(self):
        variations = VariationsArrays()
        gts = numpy.array([[[-1, -1], [1, 1], [0, 1], [1, 1], [-1, -1]],
                           [[0, 0], [0, 0], [0, 0], [0, 0], [1, 1]],
                           [[0, 0], [0, 0], [0, 0], [0, 0], [0, 1]],
                           [[0, 0], [0, 0], [0, 1], [0, 0], [0, 0]]])
        variations[GT_FIELD] = gts
        variations.samples = [1, 2, 3, 4, 5]

        expected_variable = [MISSING_INT, TRUE_INT, TRUE_INT, FALSE_INT]
        variable = is_variable(variations, samples=[1, 5])
        assert numpy.all(variable == expected_variable)

    def test_annotator(self):
        annot_id = 'test'
        hdf5 = VariationsH5(join(TEST_DATA_DIR, 'ril.hdf5'), mode='r')
        variations = VariationsArrays()
        variations.put_chunks(hdf5.iterate_chunks())

        annotator = IsVariableAnnotator(annot_id=annot_id, samples=['1_14_1_gbs'])
        result = annotator(variations)
        annotated_variations = result[ANNOTATED_VARS]
        field = '/variations/info/{}'.format(annot_id)
        assert annotated_variations.metadata[field]['Type'] == 'Integer'
        assert annotated_variations.metadata[field]['Number'] == 1

        assert field in annotated_variations.keys()
        assert annotated_variations[field][0] == 0

    def test_annotator_h5(self):
        annot_id = 'test'
        hdf5 = VariationsH5(join(TEST_DATA_DIR, 'ril.hdf5'), mode='r')
        annotator = IsVariableAnnotator(annot_id=annot_id, samples=['1_14_1_gbs',
                                                                    '1_17_1_gbs'])

        result = annotator(hdf5)
        annotated_variations = result[ANNOTATED_VARS]
        field = '/variations/info/{}'.format(annot_id)
        assert annotated_variations.metadata[field]['Type'] == 'Integer'
        assert annotated_variations.metadata[field]['Number'] == 1

        assert field in annotated_variations.keys()
        assert annotated_variations[field][3] == FALSE_INT

    def test_annotator_all_samples(self):
        annot_id = 'test'
        hdf5 = VariationsH5(join(TEST_DATA_DIR, 'ril.hdf5'), mode='r')
        variations = VariationsArrays()
        variations.put_chunks(hdf5.iterate_chunks())

        annotator = IsVariableAnnotator(annot_id=annot_id)
        result = annotator(variations)
        annotated_variations = result[ANNOTATED_VARS]
        field = '/variations/info/{}'.format(annot_id)
        assert annotated_variations.metadata[field]['Type'] == 'Integer'
        assert annotated_variations.metadata[field]['Number'] == 1

        assert field in annotated_variations.keys()
        assert annotated_variations[field][3] == TRUE_INT

if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
