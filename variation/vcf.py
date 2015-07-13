from itertools import chain, islice
import re
import subprocess

from variation import (MISSING_INT, MISSING_GT, MISSING_FLOAT, MISSING_STR,
                       FILLING_INT, FILLING_FLOAT, FILLING_STR)
from variation.utils.compressed_queue import CCache

# Missing docstring
# pylint: disable=C0111


def _missing_val(dtype_str):
    if 'int' in dtype_str:
        missing_val = MISSING_INT
    elif 'float' in dtype_str:
        missing_val = MISSING_FLOAT
    elif 'str' in dtype_str:
        missing_val = MISSING_STR
    return missing_val


def _filling_val(dtype_str):
    if 'int' in dtype_str:
        missing_val = FILLING_INT
    elif 'float' in dtype_str:
        missing_val = FILLING_FLOAT
    elif 'str' in dtype_str:
        missing_val = FILLING_STR
    return missing_val


def read_gzip_file(fpath, pgiz=False):
    if pgiz:
        cmd = ['pigz', '-dc']
    else:
        cmd = ['zcat']

    cmd.append(fpath)
    gz_process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    for line in gz_process.stdout:
        yield line


def _do_nothing(value):
    return value


def _to_int(string):
    if string in ('', '.', None, b'.'):
        return MISSING_INT
    return int(string)


def _to_float(string):
    if string in ('', '.', None):
        return MISSING_FLOAT
    return float(string)


def _gt_data_to_list(mapper_function, sample_gt):
    if sample_gt is None:
        # we cannot now at this point how many items compose a gt for a sample
        # so we cannot return [missing_data]
        return None

    sample_gt = sample_gt.split(b',')
    sample_gt = [mapper_function(item) for item in sample_gt]
    return sample_gt





class VCFParser():
    def __init__(self, fhand, pre_read_max_size=None,
                 ignored_fields=None, kept_fields=None,
                 max_field_lens=None, max_n_vars=None):
        if kept_fields is not None and ignored_fields is not None:
            msg = 'kept_fields and ignored_fields can not be set at the same'
            msg += ' time'
            raise ValueError(msg)
        self._fhand = fhand
        self.max_n_vars = max_n_vars
        self.metadata = None
        self.vcf_format = None
        self.ploidy = None

        # We remove the unwanted fields
        if ignored_fields is None:
            ignored_fields = []
        ignored_fields = [field.encode('utf-8') for field in ignored_fields]
        if kept_fields is None:
            kept_fields = []
        kept_fields = [field.encode('utf-8') for field in kept_fields]
        self.ignored_fields = ignored_fields
        self.kept_fields = kept_fields
        self._determine_ploidy()

        self._empty_gt = [MISSING_GT] * self.ploidy
        self._parse_header()

        if max_field_lens is None:
            user_max_field_lens = {}
        else:
            user_max_field_lens = max_field_lens
        max_field_lens = {'alt': 0, 'FILTER': 0, 'INFO': {}, 'FORMAT': {}}
        max_field_lens.update(user_max_field_lens)
        self.max_field_lens = max_field_lens

        self.max_field_str_lens = {'FILTER': 0, 'INFO': {}, 'chrom': 0,
                                   'alt': 0}
        self._init_max_field_lens()

        self._parsed_gt_fmts = {}
        self._parsed_gt = {}

        self.pre_read_max_size = pre_read_max_size
        self._variations_cache = CCache()
        self._read_snps_in_compressed_cache()


    def _init_max_field_lens(self):
        meta = self.metadata
        for section in ('INFO', 'FORMAT'):
            for field, meta_field in meta[section].items():
                if isinstance(meta_field['Number'], int):
                    continue
                self.max_field_lens[section][field] = 0
                if 'str' in meta_field['dtype']:
                    self.max_field_str_lens[section][field] = 0


    def _read_snps_in_compressed_cache(self):
        if not self.pre_read_max_size:
            return
        self._variations_cache.put_iterable(self._variations(),
                                            max_size=self.pre_read_max_size)

    def _determine_ploidy(self):
        read_lines = []
        ploidy = None
        for line in self._fhand:
            read_lines.append(line)
            if line.startswith(b'#'):
                continue
            gts = line.split(b'\t')[9:]
            for gt in gts:
                if gt is b'.':
                    continue
                gt = gt.split(b':')[0]
                alleles = gt.split(b'/') if b'/' in gt else gt.split(b'|')
                ploidy = len(alleles)
                break
            if ploidy is not None:
                break
        self.ploidy = ploidy
        # we have to restore the read lines to the iterator
        self._fhand = chain(read_lines, self._fhand)

    def _parse_header(self):
        # read the header lines
        header_lines = []
        for line in self._fhand:
            if line.startswith(b'#CHROM'):
                self.samples = line.strip().split(b'\t')[9:]
                break
            header_lines.append(line)

        metadata = {'FORMAT': {}, 'FILTER': {}, 'INFO': {}, 'OTHER': {}}
        metadata['VARIATIONS'] = {'chrom': {'dtype': 'str',
                                            'type': _do_nothing},
                                  'pos': {'dtype': 'int32',
                                          'type': _to_int},
                                  'id': {'dtype': 'str',
                                         'type': _do_nothing},
                                  'ref': {'dtype': 'str',
                                          'type': _do_nothing},
                                  'qual': {'dtype': 'float16',
                                          'type': _to_float},
                                  'alt': {'dtype': 'str',
                                         'type': _do_nothing},}
        for line in header_lines:
            if line[2:7] in (b'FORMA', b'INFO=', b'FILTE'):
                line = line[2:]
                meta = {}
                if line.startswith(b'FORMAT='):
                    meta_kind = 'FORMAT'
                    line = line[8:-2]
                elif line.startswith(b'FILTER='):
                    meta_kind = 'FILTER'
                    line = line[8:-2]
                elif line.startswith(b'INFO='):
                    meta_kind = 'INFO'
                    line = line[6:-2]
                else:
                    msg = 'Unsuported VCF: ' + line.decode("utf-8")
                    raise RuntimeError(msg)

                line = line.decode("utf-8")
                items = re.findall(r'(?:[^,"]|"(?:\\.|[^"])*")+',
                                   line)
                id_ = None
                for item in items:
                    key, val = item.split('=', 1)
                    if key == 'ID':
                        id_ = val.strip()
                    else:
                        if key == 'Type':
                            if val == 'Integer':
                                val = _to_int
                                val2 = 'int16'
                            elif val == 'Float':
                                val = _to_float
                                val2 = 'float16'
                            else:
                                val = _do_nothing
                                val2 = 'str'
                            meta['dtype'] = val2
                        meta[key] = val
                if id_ is None:
                    raise RuntimeError('Header line has no ID: ' + line)
                # The fields with a variable number of items
                if 'Number' in meta and meta['Number'].isdigit():
                    meta['Number'] = int(meta['Number'])
            else:
                id_, meta = line[2:].decode('utf-8').split('=', 1)
                if id_ == 'fileformat':
                    self.vcf_format = meta
                    continue
                meta_kind = 'OTHER'
            id_ = id_.encode('utf-8')
            metadata[meta_kind][id_] = meta
        self.metadata = metadata

    def _parse_info(self, info):
        infos = info.split(b';')
        parsed_infos = {}
        ignored_fields = self.ignored_fields
        for info in infos:
            if b'=' in info:
                key, val = info.split(b'=', 1)
            else:
                key, val = info, True
            if key in ignored_fields:
                continue
            try:
                meta = self.metadata['INFO'][key]
            except KeyError:
                msg = 'INFO metadata was not defined in header: '
                msg += key.decode('utf-8')
                raise RuntimeError(msg)

            type_ = meta['Type']
            if isinstance(val, bool):
                pass
            elif b',' in val:
                val = [type_(val) for val in val.split(b',')]
                val_to_check_len = val
            else:
                val = type_(val)
                val_to_check_len = [val]
            if not isinstance(meta['Number'], int):
                if self.max_field_lens['INFO'][key] < len(val_to_check_len):
                    self.max_field_lens['INFO'][key] = len(val_to_check_len)
                if 'str' in meta['dtype']:
                    max_str = max([len(val_) for val_ in val_to_check_len])
                    if self.max_field_str_lens['INFO'][key] < max_str:
                        self.max_field_str_lens['INFO'][key] = max_str

            parsed_infos[key] = val
        return parsed_infos

    def _parse_gt_fmt(self, fmt):
        orig_fmt = fmt
        try:
            return self._parsed_gt_fmts[fmt]
        except KeyError:
            pass

        meta = self.metadata['FORMAT']
        format_ = []
        for fmt in fmt.split(b':'):
            try:
                fmt_meta = meta[fmt]
            except KeyError:
                msg = 'FORMAT metadata was not defined in header: '
                msg += fmt.decode('utf-8')
                raise RuntimeError(msg)
            format_.append((fmt, fmt_meta['Type'],
                            fmt_meta['Number'] != 1,  # Is list
                            fmt_meta,
                            _missing_val(fmt_meta['dtype'])))
        self._parsed_gt_fmts[orig_fmt] = format_
        return format_

    def _parse_gt(self, gt):
        gt_str = gt
        try:
            return self._parsed_gt[gt]
        except KeyError:
            pass

        if gt is None:
            gt = self._empty_gt
        elif b'|' in gt:
            is_phased = True
            gt = gt.split(b'|')
        else:
            is_phased = False
            gt = gt.split(b'/')
        if gt is not None:
            gt = [MISSING_GT if allele == b'.' else int(allele) for allele in gt]
        self._parsed_gt[gt_str] = gt
        return gt

    def _parse_gts(self, fmt, gts):
        fmt = self._parse_gt_fmt(fmt)
        empty_gt = [None] * len(fmt)

        gts = [empty_gt if gt == b'.' else gt.split(b':') for gt in gts]
        gts = zip(*gts)

        parsed_gts = []
        ignored_fields = self.ignored_fields
        kept_fields = self.kept_fields
        for fmt, gt_data in zip(fmt, gts):
            if fmt[0] in ignored_fields:
                continue
            if kept_fields and fmt[0] not in kept_fields:
                continue
            if fmt[0] == b'GT':
                gt_data = [self._parse_gt(sample_gt) for sample_gt in gt_data]
            else:
                if fmt[2]:  # the info for a sample in this field is or should
                            # be a list
                    gt_data = [_gt_data_to_list(fmt[1], sample_gt) for sample_gt in gt_data]
                else:
                    gt_data = [fmt[1](sample_gt) for sample_gt in gt_data]

            meta = fmt[3]
            if not isinstance(meta['Number'], int):
                max_len = max([0 if data is None else len(data) for data in gt_data])
                if self.max_field_lens['FORMAT'][fmt[0]] < max_len:
                    self.max_field_lens['FORMAT'][fmt[0]] = max_len
                if 'str' in meta['dtype'] and fmt[0] != b'GT':
                    # if your file has variable length str fields you
                    # should check and fix the following part of the code
                    raise NotImplementedError('Fixme')
                    max_len = max([len(val) for smpl_data in gt_data for val in smpl_data])
                    max_str = max([len(val) for val_ in val])
                    if self.max_field_str_lens['FORMAT'][key] < max_str:
                        self.max_field_str_lens['FORMAT'][key] = max_str

            parsed_gts.append((fmt[0], gt_data))

        return parsed_gts

    @property
    def variations(self):
        snps =  chain(self._variations_cache.items, self._variations())
        if self.max_n_vars:
            snps = islice(snps, self.max_n_vars)
        return snps

    def _variations(self):
        for line in self._fhand:
            line = line[:-1]
            items = line.split(b'\t')
            chrom, pos, id_, ref, alt, qual, flt, info, fmt = items[:9]

            if self.max_field_str_lens['chrom'] < len(chrom):
                self.max_field_str_lens['chrom'] = len(chrom)

            gts = items[9:]
            pos = int(pos)
            if id_ == b'.':
                id_ = None

            alt = alt.split(b',')
            if self.max_field_lens['alt'] < len(alt):
                self.max_field_lens['alt'] = len(alt)
            max_alt_str_len = max(len(allele) for allele in alt)
            if self.max_field_str_lens['alt'] < max_alt_str_len:
                self.max_field_str_lens['alt'] = max_alt_str_len

            qual = float(qual) if qual != b'.' else None

            if flt == b'PASS':
                flt = []
                flt_len = 0
            elif flt == b'.':
                flt = None
                flt_len = 0
            else:
                flt = flt.split(b';')
                flt_len = len(flt)
            if self.max_field_lens['FILTER'] < flt_len:
                self.max_field_lens['FILTER'] = flt_len
            qual = float(qual) if qual != b'.' else None

            info = self._parse_info(info)
            gts = self._parse_gts(fmt, gts)
            yield chrom, pos, id_, ref, alt, qual, flt, info, gts


