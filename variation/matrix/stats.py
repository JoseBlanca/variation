# Missing docstring
# pylint: disable=C0111

from functools import reduce, partial
import operator

import numpy




def _row_value_counter(mat, value, ratio=False):
    ndims = len(mat.shape)
    if ndims == 1:
        raise ValueError('The matrix has to have at least 2 dimensions')
    elif ndims == 2:
        axes = 1
    else:
        axes = tuple([i +1 for i in range(ndims - 1)])
    result = (mat == value).sum(axis=axes)
    if ratio:
        num_items_per_row = reduce(operator.mul, mat.shape[1:], 1)
        result = result / num_items_per_row
    return result

def row_value_counter_fact(value, ratio=False):
    return partial(_row_value_counter, value=value, ratio=ratio)


def counts_by_row(mat, missing_value=None):

    alleles = (numpy.unique(mat))
    allele_counts = None
    # This algorithm is suboptimal, it would be better to go row per row
    # the problem is a for snp in gts is very slow because the for in
    # python is slow
    for allele in alleles:
        if allele == missing_value:
            continue
        allele_counter = row_value_counter_fact(allele)
        counts = allele_counter(mat)
        if allele_counts is None:
            allele_counts = counts
        else:
            allele_counts = numpy.column_stack((allele_counts, counts))
    return allele_counts