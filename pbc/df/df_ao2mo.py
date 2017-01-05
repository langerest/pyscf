#!/usr/bin/env python
#
# Author: Qiming Sun <osirpt.sun@gmail.com>
#

import time
import numpy
from pyscf import lib
from pyscf import ao2mo
from pyscf.ao2mo import _ao2mo
from pyscf.ao2mo.incore import iden_coeffs, _conc_mos
from pyscf.pbc import tools
from pyscf.pbc.df.df_jk import zdotNN, zdotCN, zdotNC
from pyscf.pbc.df.fft_ao2mo import _format_kpts


def get_eri(mydf, kpts=None, compact=True):
    if mydf._cderi is None:
        mydf.build()

    cell = mydf.cell
    kptijkl = _format_kpts(kpts)
    kpti, kptj, kptk, kptl = kptijkl
    nao = cell.nao_nr()
    nao_pair = nao * (nao+1) // 2
    max_memory = max(2000, mydf.max_memory-lib.current_memory()[0]-nao**4*8/1e6)

####################
# gamma point, the integral is real and with s4 symmetry
    if abs(kptijkl).sum() < 1e-9:
        eriR = numpy.zeros((nao_pair,nao_pair))
        for LpqR, LpqI in mydf.sr_loop(kptijkl[:2], max_memory, True):
            lib.ddot(LpqR.T, LpqR, 1, eriR, 1)
        if not compact:
            eriR = ao2mo.restore(1, eriR, nao).reshape(nao**2,-1)
        return eriR

    elif (abs(kpti-kptk).sum() < 1e-9) and (abs(kptj-kptl).sum() < 1e-9):
        eriR = numpy.zeros((nao*nao,nao*nao))
        eriI = numpy.zeros((nao*nao,nao*nao))
        for LpqR, LpqI in mydf.sr_loop(kptijkl[:2], max_memory, False):
            zdotNN(LpqR.T, LpqI.T, LpqR, LpqI, 1, eriR, eriI, 1)
        return eriR + eriI*1j

####################
# (kpt) i == j == k == l != 0
#
# (kpt) i == l && j == k && i != j && j != k  =>
# both vbar and ovlp are zero. It corresponds to the exchange integral.
#
# complex integrals, N^4 elements
    elif (abs(kpti-kptl).sum() < 1e-9) and (abs(kptj-kptk).sum() < 1e-9):
        eriR = numpy.zeros((nao*nao,nao*nao))
        eriI = numpy.zeros((nao*nao,nao*nao))
        for LpqR, LpqI in mydf.sr_loop(kptijkl[:2], max_memory, False):
            zdotNC(LpqR.T, LpqI.T, LpqR, LpqI, 1, eriR, eriI, 1)
# transpose(0,1,3,2) because
# j == k && i == l  =>
# (L|ij).transpose(0,2,1).conj() = (L^*|ji) = (L^*|kl)  =>  (M|kl)
        return (eriR.reshape((nao,)*4).transpose(0,1,3,2) +
                eriI.reshape((nao,)*4).transpose(0,1,3,2)*1j).reshape(nao**2,-1)

####################
# aosym = s1, complex integrals
#
# kpti == kptj  =>  kptl == kptk
# If kpti == kptj, (kptl-kptk)*a has to be multiples of 2pi because of the wave
# vector symmetry.  k is a fraction of reciprocal basis, 0 < k/b < 1, by definition.
# So  kptl/b - kptk/b  must be -1 < k/b < 1.
#
    else:
        eriR = numpy.zeros((nao*nao,nao*nao))
        eriI = numpy.zeros((nao*nao,nao*nao))
        for (LpqR, LpqI), (LrsR, LrsI) in \
                lib.izip(mydf.sr_loop(kptijkl[:2], max_memory, False),
                         mydf.sr_loop(kptijkl[2:], max_memory, False)):
            zdotNN(LpqR.T, LpqI.T, LrsR, LrsI, 1, eriR, eriI, 1)
        return eriR + eriI*1j


def general(mydf, mo_coeffs, kpts=None, compact=True):
    if mydf._cderi is None:
        mydf.build()

    cell = mydf.cell
    kptijkl = _format_kpts(kpts)
    kpti, kptj, kptk, kptl = kptijkl
    if isinstance(mo_coeffs, numpy.ndarray) and mo_coeffs.ndim == 2:
        mo_coeffs = (mo_coeffs,) * 4
    all_real = not any(numpy.iscomplexobj(mo) for mo in mo_coeffs)
    max_memory = (mydf.max_memory - lib.current_memory()[0]) * .5

####################
# gamma point, the integral is real and with s4 symmetry
    if abs(kptijkl).sum() < 1e-9 and all_real:
        ijmosym, nij_pair, moij, ijslice = _conc_mos(mo_coeffs[0], mo_coeffs[1], compact)
        klmosym, nkl_pair, mokl, klslice = _conc_mos(mo_coeffs[2], mo_coeffs[3], compact)
        eri_mo = numpy.zeros((nij_pair,nkl_pair))
        sym = (iden_coeffs(mo_coeffs[0], mo_coeffs[2]) and
               iden_coeffs(mo_coeffs[1], mo_coeffs[3]))
        ijR = klR = None
        for LpqR, LpqI in mydf.sr_loop(kptijkl[:2], max_memory, True):
            ijR = _ao2mo.nr_e2(LpqR, moij, ijslice, aosym='s2', mosym=ijmosym, out=ijR)
            if sym:
                klR = ijR
            else:
                klR = _ao2mo.nr_e2(LpqR, mokl, klslice, aosym='s2', mosym=klmosym, out=klR)
            lib.ddot(ijR.T, klR, 1, eri_mo, 1)
        return eri_mo

    elif (abs(kpti-kptk).sum() < 1e-9) and (abs(kptj-kptl).sum() < 1e-9):
        mo_coeffs = _mo_as_complex(mo_coeffs)
        nij_pair, moij, ijslice = _conc_mos(mo_coeffs[0], mo_coeffs[1])[1:]
        nkl_pair, mokl, klslice = _conc_mos(mo_coeffs[2], mo_coeffs[3])[1:]
        eri_mo = numpy.zeros((nij_pair,nkl_pair), dtype=numpy.complex)
        sym = (iden_coeffs(mo_coeffs[0], mo_coeffs[2]) and
               iden_coeffs(mo_coeffs[1], mo_coeffs[3]))

        zij = zkl = None
        for LpqR, LpqI in mydf.sr_loop(kptijkl[:2], max_memory, False):
            buf = LpqR+LpqI*1j
            zij, zkl = _ztrans(buf, zij, moij, ijslice,
                               buf, zkl, mokl, klslice, sym)
            buf = None
            lib.dot(zij.T, zkl, 1, eri_mo, 1)
        return eri_mo

####################
# (kpt) i == j == k == l != 0
# (kpt) i == l && j == k && i != j && j != k  =>
#
    elif (abs(kpti-kptl).sum() < 1e-9) and (abs(kptj-kptk).sum() < 1e-9):
        mo_coeffs = _mo_as_complex(mo_coeffs)
        nij_pair, moij, ijslice = _conc_mos(mo_coeffs[0], mo_coeffs[1])[1:]
        nlk_pair, molk, lkslice = _conc_mos(mo_coeffs[3], mo_coeffs[2])[1:]
        eri_mo = numpy.zeros((nij_pair,nlk_pair), dtype=numpy.complex)
        sym = (iden_coeffs(mo_coeffs[0], mo_coeffs[3]) and
               iden_coeffs(mo_coeffs[1], mo_coeffs[2]))

        zij = zlk = None
        for LpqR, LpqI in mydf.sr_loop(kptijkl[:2], max_memory, False):
            buf = LpqR+LpqI*1j
            zij, zlk = _ztrans(buf, zij, moij, ijslice,
                               buf, zlk, molk, lkslice, sym)
            buf = None
            lib.dot(zij.T, zlk.conj(), 1, eri_mo, 1)
        nmok = mo_coeffs[2].shape[1]
        nmol = mo_coeffs[3].shape[1]
        eri_mo = lib.transpose(eri_mo.reshape(-1,nmol,nmok), axes=(0,2,1))
        return eri_mo.reshape(nij_pair,nlk_pair)

####################
# aosym = s1, complex integrals
#
# If kpti == kptj, (kptl-kptk)*a has to be multiples of 2pi because of the wave
# vector symmetry.  k is a fraction of reciprocal basis, 0 < k/b < 1, by definition.
# So  kptl/b - kptk/b  must be -1 < k/b < 1.  =>  kptl == kptk
#
    else:
        mo_coeffs = _mo_as_complex(mo_coeffs)
        nij_pair, moij, ijslice = _conc_mos(mo_coeffs[0], mo_coeffs[1])[1:]
        nkl_pair, mokl, klslice = _conc_mos(mo_coeffs[2], mo_coeffs[3])[1:]
        eri_mo = numpy.zeros((nij_pair,nkl_pair), dtype=numpy.complex)

        zij = zkl = None
        for (LpqR, LpqI), (LrsR, LrsI) in \
                lib.izip(mydf.sr_loop(kptijkl[:2], max_memory, False),
                         mydf.sr_loop(kptijkl[2:], max_memory, False)):
            zij, zkl = _ztrans(LpqR+LpqI*1j, zij, moij, ijslice,
                               LrsR+LrsI*1j, zkl, mokl, klslice, False)
            lib.dot(zij.T, zkl, 1, eri_mo, 1)
        return eri_mo


def _mo_as_complex(mo_coeffs):
    mos = []
    for c in mo_coeffs:
        if c.dtype == numpy.float64:
            mos.append(c+0j)
        else:
            mos.append(c)
    return mos

def _ztrans(Lpq, zij, moij, ijslice, Lrs, zkl, mokl, klslice, sym):
    tao = []
    ao_loc = None
    zij = _ao2mo.r_e2(Lpq, moij, ijslice, tao, ao_loc, out=zij)
    if sym:
        zkl = zij
    else:
        zkl = _ao2mo.r_e2(Lrs, mokl, klslice, tao, ao_loc, out=zkl)
    return zij, zkl


if __name__ == '__main__':
    import pyscf.pbc.gto as pgto
    from pyscf.pbc import df

    L = 5.
    n = 5
    cell = pgto.Cell()
    cell.a = numpy.diag([L,L,L])
    cell.gs = numpy.array([n,n,n])

    cell.atom = '''He    3.    2.       3.
                   He    1.    1.       1.'''
    #cell.basis = {'He': [[0, (1.0, 1.0)]]}
    #cell.basis = '631g'
    #cell.basis = {'He': [[0, (2.4, 1)], [1, (1.1, 1)]]}
    cell.basis = 'ccpvdz'
    cell.verbose = 0
    cell.build(0,0)

    nao = cell.nao_nr()
    numpy.random.seed(1)
    kpts = numpy.random.random((4,3))*.5
    kpts[3] = -numpy.einsum('ij->j', kpts[:3])
    with_df = df.DF(cell)
    with_df.kpts = kpts
    mo =(numpy.random.random((nao,nao)) +
         numpy.random.random((nao,nao))*1j)
    eri = with_df.get_eri(kpts).reshape((nao,)*4)
    eri0 = numpy.einsum('pjkl,pi->ijkl', eri , mo.conj())
    eri0 = numpy.einsum('ipkl,pj->ijkl', eri0, mo       )
    eri0 = numpy.einsum('ijpl,pk->ijkl', eri0, mo.conj())
    eri0 = numpy.einsum('ijkp,pl->ijkl', eri0, mo       ).reshape(nao**2,-1)
    eri1 = with_df.ao2mo(mo, kpts)
    print abs(eri1-eri0).sum()

    kpts[2] = kpts[0]
    kpts[3] = kpts[1]
    with_df = df.DF(cell)
    with_df.kpts = kpts
    mo = numpy.eye(nao)
    eri = with_df.get_eri(kpts).reshape((nao,)*4)
    eri0 = numpy.einsum('pjkl,pi->ijkl', eri , mo.conj())
    eri0 = numpy.einsum('ipkl,pj->ijkl', eri0, mo       )
    eri0 = numpy.einsum('ijpl,pk->ijkl', eri0, mo.conj())
    eri0 = numpy.einsum('ijkp,pl->ijkl', eri0, mo       ).reshape(nao**2,-1)
    eri1 = with_df.ao2mo(mo, kpts)
    print abs(eri1-eri0).sum()

    kpts[3] = kpts[0]
    kpts[2] = kpts[1]
    with_df = df.DF(cell)
    with_df.kpts = kpts
    mo = numpy.eye(nao)
    eri = with_df.get_eri(kpts).reshape((nao,)*4)
    eri0 = numpy.einsum('pjkl,pi->ijkl', eri , mo.conj())
    eri0 = numpy.einsum('ipkl,pj->ijkl', eri0, mo       )
    eri0 = numpy.einsum('ijpl,pk->ijkl', eri0, mo.conj())
    eri0 = numpy.einsum('ijkp,pl->ijkl', eri0, mo       ).reshape(nao**2,-1)
    eri1 = with_df.ao2mo(mo, kpts)
    print abs(eri1-eri0).sum()

    with_df = df.DF(cell)
    eri = ao2mo.restore(1, with_df.get_eri(with_df.kpts), nao)
    eri0 = numpy.einsum('pjkl,pi->ijkl', eri , mo.conj())
    eri0 = numpy.einsum('ipkl,pj->ijkl', eri0, mo       )
    eri0 = numpy.einsum('ijpl,pk->ijkl', eri0, mo.conj())
    eri0 = numpy.einsum('ijkp,pl->ijkl', eri0, mo       )
    eri1 = with_df.ao2mo(mo, with_df.kpts, compact=False)
    print abs(eri1.reshape(eri0.shape)-eri0).sum()

    with_df = df.DF(cell)
    mo = mo.real
    eri0 = numpy.einsum('pjkl,pi->ijkl', eri , mo.conj())
    eri0 = numpy.einsum('ipkl,pj->ijkl', eri0, mo       )
    eri0 = numpy.einsum('ijpl,pk->ijkl', eri0, mo.conj())
    eri0 = numpy.einsum('ijkp,pl->ijkl', eri0, mo       )
    eri1 = with_df.ao2mo(mo, with_df.kpts, compact=False)
    print abs(eri1.reshape(eri0.shape)-eri0).sum()
