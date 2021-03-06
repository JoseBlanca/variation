
# Method could be a function
# pylint: disable=R0201
# Too many public methods
# pylint: disable=R0904
# Missing docstring
# pylint: disable=C0111

import unittest
from os.path import join

import numpy

from variation.variations.pipeline import Pipeline
from variation.variations.filters import (MinCalledGTsFilter, MafFilter,
                                          MacFilter, ObsHetFilter, FLT_VARS,
                                          LowDPGTsToMissingSetter,
                                          SNPQualFilter, NonBiallelicFilter,
                                          SampleFilter, FieldFilter,
                                          Chi2GtFreqs2SampleSetsFilter, N_KEPT,
                                          FLT_STATS, TOT, N_FILTERED_OUT,
                                          FieldValueFilter)
from variation.variations.vars_matrices import VariationsH5, VariationsArrays
from variation import GT_FIELD
from test.test_utils import TEST_DATA_DIR
from variation.variations.annotation import IsVariableAnnotator


class PipelineTest(unittest.TestCase):
    def test_pipeline(self):
        pipeline = Pipeline()
        hdf5 = VariationsH5(join(TEST_DATA_DIR, 'ril.hdf5'), mode='r')

        flt = MinCalledGTsFilter(min_called=0.1, range_=(0, 1))
        pipeline.append(flt, id_='filter1')

        vars_out = VariationsArrays()
        result = pipeline.run(hdf5, vars_out)

        # check same result with no pipeline
        result2 = flt(hdf5)
        assert numpy.allclose(result['filter1']['counts'], result2['counts'])
        assert numpy.allclose(result['filter1']['edges'], result2['edges'])
        assert numpy.allclose(vars_out['/calls/GT'],
                              result2[FLT_VARS]['/calls/GT'])
        assert (result['filter1'][FLT_STATS][N_KEPT] ==
                result2[FLT_STATS][N_KEPT])
        assert result['filter1'][FLT_STATS][TOT] == result2[FLT_STATS][TOT]
        assert (result['filter1'][FLT_STATS][N_FILTERED_OUT] ==
                result2[FLT_STATS][N_FILTERED_OUT])

        # check with no range set
        pipeline = Pipeline()
        flt = MinCalledGTsFilter(min_called=0.1, do_histogram=True)
        pipeline.append(flt, id_='filter1')

        vars_out = VariationsArrays()
        result = pipeline.run(hdf5, vars_out)

        result2 = flt(hdf5)
        assert numpy.allclose(result['filter1']['counts'], result2['counts'])
        assert numpy.allclose(result['filter1']['edges'], result2['edges'])
        assert numpy.allclose(vars_out['/calls/GT'],
                              result2[FLT_VARS]['/calls/GT'])

        # With rates False
        pipeline = Pipeline()
        flt = MinCalledGTsFilter(min_called=20, rates=False, do_histogram=True)
        pipeline.append(flt, id_='filter1')

        vars_out = VariationsArrays()
        result = pipeline.run(hdf5, vars_out)

        result2 = flt(hdf5)
        assert result['filter1']['order'] == 0
        assert numpy.allclose(result['filter1']['counts'], result2['counts'])
        assert numpy.allclose(result['filter1']['edges'], result2['edges'])
        assert numpy.allclose(vars_out['/calls/GT'],
                              result2[FLT_VARS]['/calls/GT'])

    def test_min_maf(self):
        pipeline = Pipeline()
        hdf5 = VariationsH5(join(TEST_DATA_DIR, 'ril.hdf5'), mode='r')

        flt = MafFilter(min_maf=0.1, max_maf=0.9, do_histogram=True)
        pipeline.append(flt, id_='filter1')

        vars_out = VariationsArrays()
        result = pipeline.run(hdf5, vars_out)

        # check same result with no pipeline
        result2 = flt(hdf5)
        assert numpy.allclose(result['filter1']['counts'], result2['counts'])
        assert numpy.allclose(result['filter1']['edges'], result2['edges'])
        assert numpy.allclose(vars_out['/calls/GT'],
                              result2[FLT_VARS]['/calls/GT'])

    def test_no_filtering(self):
        pipeline = Pipeline()
        hdf5 = VariationsH5(join(TEST_DATA_DIR, 'ril.hdf5'), mode='r')

        flt = MafFilter(min_maf=0.1, max_maf=0.9, do_histogram=True,
                        do_filtering=False)
        pipeline.append(flt, id_='filter1')

        vars_out = None
        result = pipeline.run(hdf5, vars_out)

        # check same result with no pipeline
        result2 = flt(hdf5)
        assert numpy.allclose(result['filter1']['counts'], result2['counts'])
        assert numpy.allclose(result['filter1']['edges'], result2['edges'])

    def test_min_mac(self):
        pipeline = Pipeline()
        hdf5 = VariationsH5(join(TEST_DATA_DIR, 'ril.hdf5'), mode='r')

        flt = MacFilter(min_mac=10, max_mac=30, do_histogram=True)
        pipeline.append(flt, id_='filter1')

        vars_out = VariationsArrays()
        result = pipeline.run(hdf5, vars_out)

        # check same result with no pipeline
        result2 = flt(hdf5)
        assert numpy.allclose(result['filter1']['counts'], result2['counts'])
        assert numpy.allclose(result['filter1']['edges'], result2['edges'])
        assert not vars_out.keys()

        assert result2[FLT_VARS]['/calls/GT'].shape[0] == 0

    def test_het(self):
        pipeline = Pipeline()
        hdf5 = VariationsH5(join(TEST_DATA_DIR, 'ril.hdf5'), mode='r')

        samples = hdf5.samples[:20]
        flt = ObsHetFilter(min_het=0.02, max_het=0.5, samples=samples,
                           do_histogram=True)
        pipeline.append(flt)

        vars_out = VariationsArrays()
        result = pipeline.run(hdf5, vars_out)

        # check same result with no pipeline
        result2 = flt(hdf5)
        assert numpy.allclose(result['0']['counts'], result2['counts'])
        assert numpy.allclose(result['0']['edges'], result2['edges'])
        assert numpy.allclose(vars_out['/calls/GT'],
                              result2[FLT_VARS]['/calls/GT'])

    def test_snp_qual(self):
        pipeline = Pipeline()
        hdf5 = VariationsH5(join(TEST_DATA_DIR, 'ril.hdf5'), mode='r')

        flt = SNPQualFilter(min_qual=100, max_qual=50000, do_histogram=True)
        pipeline.append(flt)

        vars_out = VariationsArrays()
        result = pipeline.run(hdf5, vars_out)

        # check same result with no pipeline
        result2 = flt(hdf5)
        assert numpy.allclose(result['0']['counts'], result2['counts'])
        assert numpy.allclose(result['0']['edges'], result2['edges'])
        assert numpy.allclose(vars_out['/calls/GT'],
                              result2[FLT_VARS]['/calls/GT'])

    def test_low_dp_gt(self):
        pipeline = Pipeline()
        hdf5 = VariationsH5(join(TEST_DATA_DIR, 'ril.hdf5'), mode='r')

        flt = LowDPGTsToMissingSetter(min_dp=5)
        pipeline.append(flt)

        vars_out = VariationsArrays()
        pipeline.run(hdf5, vars_out)

        # check same result with no pipeline
        result2 = flt(hdf5)
        assert numpy.allclose(vars_out['/calls/GT'],
                              result2[FLT_VARS]['/calls/GT'])

    def test_biallelic(self):
        pipeline = Pipeline()
        hdf5 = VariationsH5(join(TEST_DATA_DIR, 'ril.hdf5'), mode='r')

        flt = NonBiallelicFilter()
        pipeline.append(flt)

        vars_out = VariationsArrays()
        pipeline.run(hdf5, vars_out)

        # check same result with no pipeline
        result2 = flt(hdf5)
        assert numpy.allclose(vars_out['/calls/GT'],
                              result2[FLT_VARS]['/calls/GT'])

    def test_filter_chi2_gt_sample_sets(self):
        pipeline = Pipeline()
        hdf5 = VariationsH5(join(TEST_DATA_DIR, 'ril.hdf5'), mode='r')

        samples1 = hdf5.samples[:20]
        samples2 = hdf5.samples[20:]
        flt = Chi2GtFreqs2SampleSetsFilter(samples1, samples2, min_pval=0.05,
                                           do_histogram=True)
        pipeline.append(flt)

        vars_out = VariationsArrays()
        result = pipeline.run(hdf5, vars_out)

        # check same result with no pipeline
        result2 = flt(hdf5)
        assert numpy.allclose(result['0']['counts'], result2['counts'])
        assert numpy.allclose(result['0']['edges'], result2['edges'])
        assert numpy.allclose(vars_out['/calls/GT'],
                              result2[FLT_VARS]['/calls/GT'])

    def test_field_filter(self):
        pipeline = Pipeline()
        hdf5 = VariationsH5(join(TEST_DATA_DIR, 'ril.hdf5'), mode='r')

        flt = FieldFilter(kept_fields=[GT_FIELD])
        pipeline.append(flt)

        vars_out = VariationsArrays()
        pipeline.run(hdf5, vars_out)

        # check same result with no pipeline
        result2 = flt(hdf5)
        assert numpy.allclose(vars_out['/calls/GT'],
                              result2[FLT_VARS]['/calls/GT'])
        assert list(vars_out.keys()) == [GT_FIELD]
        assert list(result2[FLT_VARS].keys()) == [GT_FIELD]

    def test_filter_samples(self):
        pipeline = Pipeline()
        hdf5 = VariationsH5(join(TEST_DATA_DIR, 'ril.hdf5'), mode='r')

        samples = hdf5.samples[:20]
        flt = SampleFilter(samples)
        pipeline.append(flt)

        vars_out = VariationsArrays()
        pipeline.run(hdf5, vars_out)

        # check same result with no pipeline
        result2 = flt(hdf5)
        assert numpy.allclose(vars_out['/calls/GT'],
                              result2[FLT_VARS]['/calls/GT'])

    def test_fieldpath(self):
        pipeline = Pipeline()
        annot_id = 'test'
        hdf5 = VariationsH5(join(TEST_DATA_DIR, 'ril.hdf5'), mode='r')
        field = '/variations/info/{}'.format(annot_id)
        annotator = IsVariableAnnotator(annot_id=annot_id, samples=['1_14_1_gbs',
                                                                    '1_17_1_gbs'])
        pipeline.append(annotator)
        annotator = FieldValueFilter(field_path=field, value=0)
        pipeline.append(annotator)

        vars_out = VariationsArrays()
        pipeline.run(hdf5, vars_out)
        assert vars_out.num_variations == 484

if __name__ == "__main__":
    # import sys;sys.argv = ['', 'PipelineTest.test_snp_qual']
    unittest.main()
