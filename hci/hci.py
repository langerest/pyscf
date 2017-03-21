#!/usr/bin/env python
#
# Author: Qiming Sun <osirpt.sun@gmail.com>
#         Alexander Sokolov <alexander.y.sokolov@gmail.com>
#

'''
Selected CI using Heat-Bath CI algorithm
(JCTC 2016, 12, 3674-3680)

Simple usage::

'''

import numpy
import time
import ctypes
from pyscf import lib
from pyscf import ao2mo
from pyscf.lib import logger
from pyscf.fci import cistring
from pyscf.fci import direct_spin1

libhci = lib.load_library('libhci')

def contract_2e_ctypes(h1_h2, civec, norb, nelec, hdiag=None, **kwargs):
    h1, eri = h1_h2
    strs = civec._strs
    ts = civec._ts
    ndet = len(strs)
    if hdiag is None:
        hdiag = make_hdiag(h1, eri, strs, norb, nelec)
    ci1 = numpy.zeros_like(civec)

    h1 = numpy.asarray(h1, order='C')
    eri = numpy.asarray(eri, order='C')
    strs = numpy.asarray(strs, order='C')
    civec = numpy.asarray(civec, order='C')
    hdiag = numpy.asarray(hdiag, order='C')
    ci1 = numpy.asarray(ci1, order='C')

    libhci.contract_h_c(h1.ctypes.data_as(ctypes.c_void_p), 
                        eri.ctypes.data_as(ctypes.c_void_p), 
                        ctypes.c_int(norb), 
                        ctypes.c_int(nelec[0]), 
                        ctypes.c_int(nelec[1]), 
                        strs.ctypes.data_as(ctypes.c_void_p), 
                        civec.ctypes.data_as(ctypes.c_void_p), 
                        hdiag.ctypes.data_as(ctypes.c_void_p), 
                        ctypes.c_int(ndet), 
                        ci1.ctypes.data_as(ctypes.c_void_p))

    return ci1

#def contract_2e(h1_h2, civec, norb, nelec, hdiag=None, **kwargs):
#    h1, eri = h1_h2
#    strs = civec._strs
#    ts = civec._ts
#    ndet = len(strs)
#    if hdiag is None:
#        hdiag = make_hdiag(h1, eri, strs, norb, nelec)
#    ci1 = numpy.zeros_like(civec)
#
#    eri = eri.reshape([norb]*4)
#
#    for ip in range(ndet):
#        for jp in range(ip):
#            if abs(ts[ip] - ts[jp]).sum() > 2:
#                continue
#            stria, strib = strs[ip].reshape(2,-1)
#            strja, strjb = strs[jp].reshape(2,-1)
#            desa, crea = str_diff(stria, strja)
#            if len(desa) > 2:
#                continue
#            desb, creb = str_diff(strib, strjb)
#            if len(desb) + len(desa) > 2:
#                continue
#            if len(desa) + len(desb) == 1:
## alpha->alpha
#                if len(desb) == 0:
#                    i,a = desa[0], crea[0]
#                    occsa = str2orblst(stria, norb)[0]
#                    occsb = str2orblst(strib, norb)[0]
#                    fai = h1[a,i]
#                    for k in occsa:
#                        fai += eri[k,k,a,i] - eri[k,i,a,k]
#                    for k in occsb:
#                        fai += eri[k,k,a,i]
#                    sign = cre_des_sign(a, i, stria)
#                    ci1[jp] += sign * fai * civec[ip]
#                    ci1[ip] += sign * fai * civec[jp]
## beta ->beta
#                elif len(desa) == 0:
#                    i,a = desb[0], creb[0]
#                    occsa = str2orblst(stria, norb)[0]
#                    occsb = str2orblst(strib, norb)[0]
#                    fai = h1[a,i]
#                    for k in occsb:
#                        fai += eri[k,k,a,i] - eri[k,i,a,k]
#                    for k in occsa:
#                        fai += eri[k,k,a,i]
#                    sign = cre_des_sign(a, i, strib)
#                    ci1[jp] += sign * fai * civec[ip]
#                    ci1[ip] += sign * fai * civec[jp]
#
#            else:
## alpha,alpha->alpha,alpha
#                if len(desb) == 0:
#                    i,j = desa
#                    a,b = crea
## 6 conditions for i,j,a,b
## --++, ++--, -+-+, +-+-, -++-, +--+ 
#                    if a > j or i > b:
## condition --++, ++--
#                        v = eri[a,j,b,i]-eri[a,i,b,j]
#                        sign = cre_des_sign(b, i, stria)
#                        sign*= cre_des_sign(a, j, stria)
#                    else:
## condition -+-+, +-+-, -++-, +--+ 
#                        v = eri[a,i,b,j]-eri[a,j,b,i]
#                        sign = cre_des_sign(b, j, stria)
#                        sign*= cre_des_sign(a, i, stria)
#                    ci1[jp] += sign * v * civec[ip]
#                    ci1[ip] += sign * v * civec[jp]
## beta ,beta ->beta ,beta
#                elif len(desa) == 0:
#                    i,j = desb
#                    a,b = creb
#                    if a > j or i > b:
#                        v = eri[a,j,b,i]-eri[a,i,b,j]
#                        sign = cre_des_sign(b, i, strib)
#                        sign*= cre_des_sign(a, j, strib)
#                    else:
#                        v = eri[a,i,b,j]-eri[a,j,b,i]
#                        sign = cre_des_sign(b, j, strib)
#                        sign*= cre_des_sign(a, i, strib)
#                    ci1[jp] += sign * v * civec[ip]
#                    ci1[ip] += sign * v * civec[jp]
## alpha,beta ->alpha,beta
#                else:
#                    i,a = desa[0], crea[0]
#                    j,b = desb[0], creb[0]
#                    v = eri[a,i,b,j]
#                    sign = cre_des_sign(a, i, stria)
#                    sign*= cre_des_sign(b, j, strib)
#                    ci1[jp] += sign * v * civec[ip]
#                    ci1[ip] += sign * v * civec[jp]
#        ci1[ip] += hdiag[ip] * civec[ip]
#
#    return ci1

def make_hdiag(h1e, eri, strs, norb, nelec):
    eri = ao2mo.restore(1, eri, norb)
    diagj = numpy.einsum('iijj->ij',eri)
    diagk = numpy.einsum('ijji->ij',eri)

    ndet = len(strs)
    hdiag = numpy.zeros(ndet)
    for idet, (stra, strb) in enumerate(strs.reshape(ndet,2,-1)):
        aocc = str2orblst(stra, norb)[0]
        bocc = str2orblst(strb, norb)[0]
        e1 = h1e[aocc,aocc].sum() + h1e[bocc,bocc].sum()
        e2 = diagj[aocc][:,aocc].sum() + diagj[aocc][:,bocc].sum() \
           + diagj[bocc][:,aocc].sum() + diagj[bocc][:,bocc].sum() \
           - diagk[aocc][:,aocc].sum() - diagk[bocc][:,bocc].sum()
        hdiag[idet] = e1 + e2*.5
    return hdiag

def cre_des_sign(p, q, string):
    nset = len(string)
    pg, pb = p//64, p%64
    qg, qb = q//64, q%64

    if pg > qg:
        n1 = 0
        for i in range(nset-pg, nset-qg-1):
            n1 += bin(string[i]).count('1')
        n1 += bin(string[-1-pg] & numpy.uint64((1<<pb) - 1)).count('1')
        n1 += string[-1-qg] >> numpy.uint64(qb+1)
    elif pg < qg:
        n1 = 0
        for i in range(nset-qg, nset-pg-1):
            n1 += bin(string[i]).count('1')
        n1 += bin(string[-1-qg] & numpy.uint64((1<<qb) - 1)).count('1')
        n1 += string[-1-pg] >> numpy.uint64(pb+1)
    else:
        if p > q:
            mask = numpy.uint64((1 << pb) - (1 << (qb+1)))
        else:
            mask = numpy.uint64((1 << qb) - (1 << (pb+1)))
        n1 = bin(string[pg]&mask).count('1')

    if n1 % 2:
        return -1
    else:
        return 1

def argunique(strs):
    def order(x, y):
        for i in range(y.size):
            if x[i] > y[i]:
                return 1
            elif y[i] > x[i]:
                return -1
        return 0
    def qsort_idx(idx):
        nstrs = len(idx)
        if nstrs <= 1:
            return idx
        else:
            ref = idx[-1]
            group_lt = []
            group_gt = []
            for i in idx[:-1]:
                c = order(strs[i], strs[ref])
                if c == -1:
                    group_lt.append(i)
                elif c == 1:
                    group_gt.append(i)
            return qsort_idx(group_lt) + [ref] + qsort_idx(group_gt)
    return qsort_idx(range(len(strs)))

def argunique_ctypes(strs):
    nstrs, nset = strs.shape

    sort_idx = numpy.empty(nstrs, dtype=numpy.uint64)

    strs = numpy.asarray(strs, order='C')
    sort_idx = numpy.asarray(sort_idx, order='C')

    nstrs_ = numpy.array([nstrs])

    libhci.argunique(strs.ctypes.data_as(ctypes.c_void_p), 
                     sort_idx.ctypes.data_as(ctypes.c_void_p), 
                     nstrs_.ctypes.data_as(ctypes.c_void_p), 
                     ctypes.c_int(nset))

    sort_idx = sort_idx[:nstrs_[0]]

    return sort_idx.tolist()

def argunique_with_t(strs, ts):
    if len(strs) == 0:
        return []
    else:
        strs = numpy.asarray(strs)
        ts = numpy.asarray(ts, dtype=numpy.int32)
        t_ab = ts.view(numpy.int64).ravel()
        idxs = []
        for ti in numpy.unique(t_ab):
            idx = numpy.where(t_ab == ti)[0]
#            idxs.append(idx[argunique(strs[idx])])
            idxs.append(idx[argunique_ctypes(strs[idx])])
        return numpy.hstack(idxs)

def str_diff(string0, string1):
    des_string0 = []
    cre_string0 = []
    nset = len(string0)
    off = 0
    for i in reversed(range(nset)):
        df = string0[i] ^ string1[i]
        des_string0.extend([x+off for x in find1(df & string0[i])])
        cre_string0.extend([x+off for x in find1(df & string1[i])])
        off += 64
    return des_string0, cre_string0

def excitation_level(string, nelec=None):
    nset = len(string)
    if nelec is None:
        nelec = 0
        for i in range(nset):
            nelec += bin(string[i]).count('1')

    g, b = nelec//64, nelec%64
    tn = nelec - bin(string[-1-g])[-b:].count('1')
    for s in string[nset-g:]:
        tn -= bin(s).count('1')
    return tn

def find1(s):
    return [i for i,x in enumerate(bin(s)[2:][::-1]) if x is '1']

def toggle_bit(s, place):
    nset = len(s)
    g, b = place//64, place%64
    s[-1-g] ^= numpy.uint64(1<<b)
    return s

def select_strs_ctypes(myci, civec, h1, eri, jk, eri_sorted, jk_sorted, norb, nelec):
    strs = civec._strs
    ndet = strs.shape[0]
    ndet, nset = strs.shape
    nset = nset // 2
    neleca, nelecb = nelec

    str_add = numpy.empty((4*ndet*neleca*nelecb*(norb-neleca)*(norb-nelecb), strs.shape[1]), dtype=numpy.uint64)
    n_str_add = numpy.array([str_add.shape[0]])

    h1 = numpy.asarray(h1, order='C')  
    eri = numpy.asarray(eri, order='C')
    jk = numpy.asarray(jk, order='C')
    civec = numpy.asarray(civec, order='C')
    strs = numpy.asarray(strs, order='C')
    str_add = numpy.asarray(str_add, order='C')
    eri_sorted = numpy.asarray(eri_sorted, order='C')
    jk_sorted = numpy.asarray(jk_sorted, order='C')

    libhci.select_strs(h1.ctypes.data_as(ctypes.c_void_p), 
                       eri.ctypes.data_as(ctypes.c_void_p), 
                       jk.ctypes.data_as(ctypes.c_void_p), 
                       eri_sorted.ctypes.data_as(ctypes.c_void_p), 
                       jk_sorted.ctypes.data_as(ctypes.c_void_p), 
                       ctypes.c_int(norb), 
                       ctypes.c_int(neleca), 
                       ctypes.c_int(nelecb), 
                       strs.ctypes.data_as(ctypes.c_void_p), 
                       civec.ctypes.data_as(ctypes.c_void_p), 
                       ctypes.c_int(ndet), 
                       ctypes.c_double(myci.select_cutoff),
                       str_add.ctypes.data_as(ctypes.c_void_p),
                       n_str_add.ctypes.data_as(ctypes.c_void_p))

    n_str_add = n_str_add[0]
    str_add = str_add[:n_str_add]

    if len(str_add) > 0:
        str_add = numpy.asarray(str_add)
        strsa = str_add.reshape(-1,2,nset)[:,0]
        strsb = str_add.reshape(-1,2,nset)[:,1]
        ta = [excitation_level(s, neleca) for s in strsa]
        tb = [excitation_level(s, nelecb) for s in strsb]
        ts = numpy.vstack((ta, tb)).T.copy('C')
#        idx = argunique_with_t(str_add, ts)
#        return str_add[idx], ts[idx]
        return str_add, ts
    else:
        return (numpy.zeros([0,2,nset], dtype=civec._strs.dtype),
                numpy.zeros([0,2], dtype=civec._ts.dtype))

#def select_strs(myci, civec, h1, eri, norb, nelec):
#    eri = eri.reshape([norb]*4)
#    neleca, nelecb = nelec
#    vja = numpy.einsum('iipq->pq', eri[:neleca,:neleca])
#    vjb = numpy.einsum('iipq->pq', eri[:nelecb,:nelecb])
#    vka = numpy.einsum('piiq->pq', eri[:,:neleca,:neleca])
#    vkb = numpy.einsum('piiq->pq', eri[:,:nelecb,:nelecb])
#    focka = h1 + vja+vjb - vka
#    fockb = h1 + vja+vjb - vkb
#
#    eri = eri.ravel()
#    eri_sorted = abs(eri).argsort()[::-1]
#    jk = eri.reshape([norb]*4)
#    jk = jk - jk.transpose(2,1,0,3)
#    jkf = jk.ravel()
#    jk_sorted = abs(jkf).argsort()[::-1]
#
#    ndet, nset = civec._strs.shape
#    str_add = []
#    for idet, (stra, strb) in enumerate(civec._strs.reshape(ndet,2,nset//2)):
#        occsa, virsa = str2orblst(stra, norb)
#        occsb, virsb = str2orblst(strb, norb)
#        tol = myci.select_cutoff / abs(civec[idet])
#
#        holes_a = [i for i in virsa if i < neleca]
#        particles_a = [i for i in occsa if i >= neleca]
#        holes_b = [i for i in virsb if i < nelecb]
#        particles_b = [i for i in occsb if i >= nelecb]
## alpha->alpha
#        for i in occsa:
#            for a in virsa:
#                fai = focka[a,i]
#                for k in particles_a:
#                    fai += jk[k,k,a,i]
#                for k in holes_a:
#                    fai -= jk[k,k,a,i]
#                for k in particles_b:
#                    fai += eri[k * norb * norb * norb + k * norb * norb + a * norb + i]
#                for k in holes_b:
#                    fai -= eri[k * norb * norb * norb + k * norb * norb + a * norb + i]
#                if abs(fai) > tol:
#                    newa = toggle_bit(toggle_bit(stra.copy(), a), i)
#                    str_add.append(numpy.hstack((newa,strb)))
## beta ->beta
#        for i in occsb:
#            for a in virsb:
#                fai = fockb[a,i]
#                for k in particles_b:
#                    fai += jk[k,k,a,i]
#                for k in holes_b:
#                    fai -= jk[k,k,a,i]
#                for k in particles_a:
#                    fai += eri[k * norb * norb * norb + k * norb * norb + a * norb + i]
#                for k in holes_a:
#                    fai -= eri[k * norb * norb * norb + k * norb * norb + a * norb + i]
#                if abs(fai) > tol:
#                    newb = toggle_bit(toggle_bit(strb.copy(), a), i)
#                    str_add.append(numpy.hstack((stra,newb)))
#
#        for ih in jk_sorted:
#            if abs(jkf[ih]) < tol:
#                break
#            ij, lp = ih//norb, ih%norb
#            ij, kp = ij//norb, ij%norb
#            ip, jp = ij//norb, ij%norb
## alpha,alpha->alpha,alpha
#            if jp in occsa and ip in virsa and lp in occsa and kp in virsa:
#                newa = toggle_bit(toggle_bit(toggle_bit(toggle_bit(stra.copy(), jp), ip), lp), kp)
#                str_add.append(numpy.hstack((newa,strb)))
## beta ,beta ->beta ,beta
#            if jp in occsb and ip in virsb and lp in occsb and kp in virsb:
#                newb = toggle_bit(toggle_bit(toggle_bit(toggle_bit(strb.copy(), jp), ip), lp), kp)
#                str_add.append(numpy.hstack((stra,newb)))
#
#        for ih in eri_sorted:
#            if abs(eri[ih]) < tol:
#                break
#            ij, lp = ih//norb, ih%norb
#            ij, kp = ij//norb, ij%norb
#            ip, jp = ij//norb, ij%norb
## alpha,beta ->alpha,beta
#            if jp in occsa and ip in virsa and lp in occsb and kp in virsb:
#                newa = toggle_bit(toggle_bit(stra.copy(), jp), ip)
#                newb = toggle_bit(toggle_bit(strb.copy(), lp), kp)
#                str_add.append(numpy.hstack((newa,newb)))
#
#    if len(str_add) > 0:
#        str_add = numpy.asarray(str_add)
#        strsa = str_add.reshape(-1,2,nset//2)[:,0]
#        strsb = str_add.reshape(-1,2,nset//2)[:,1]
#        ta = [excitation_level(s, neleca) for s in strsa]
#        tb = [excitation_level(s, nelecb) for s in strsb]
#        ts = numpy.vstack((ta, tb)).T.copy('C')
#        idx = argunique_with_t(str_add, ts)
#        return str_add[idx], ts[idx]
#    else:
#        return (numpy.zeros([0,2,nset//2], dtype=civec._strs.dtype),
#                numpy.zeros([0,2], dtype=civec._ts.dtype))

def enlarge_space(myci, civec, h1, eri, jk, eri_sorted, jk_sorted, norb, nelec):
    if not isinstance(civec, (tuple, list)):
        civec = [civec]

    strs = civec[0]._strs
    ts = civec[0]._ts

    nroots = len(civec)

    cidx = abs(civec[0]) > myci.ci_coeff_cutoff
    for p in range(1,nroots):
        cidx += abs(civec[p]) > myci.ci_coeff_cutoff

    strs = strs[cidx]
    ts = ts[cidx]

    ci_coeff = [as_SCIvector(c[cidx], strs, ts) for c in civec]
 
    strs_new = strs.copy()
    ts_new = ts.copy()

    for p in range(nroots):
        str_add, ts_add = select_strs_ctypes(myci, ci_coeff[p], h1, eri, jk, eri_sorted, jk_sorted, norb, nelec)
        strs_new = numpy.vstack((strs, str_add))
        ts_new = numpy.vstack((ts_new, ts_add))

    # Add strings together and remove duplicate strings
    tmp = numpy.ascontiguousarray(strs_new).view(numpy.dtype((numpy.void, strs_new.dtype.itemsize * strs_new.shape[1])))
    _, tmpidx = numpy.unique(tmp, return_index=True)

    new_ci = []
    for p in range(nroots):
        c = numpy.zeros(strs_new.shape[0])
        c[:ci_coeff[p].shape[0]] = ci_coeff[p]
        new_ci.append(c[tmpidx])

    strs_new = strs_new[tmpidx]
    ts_new = ts_new[tmpidx]

    return [as_SCIvector(ci, strs_new, ts_new) for ci in new_ci]

def str2orblst(string, norb):
    occ = []
    vir = []
    nset = len(string)
    off = 0
    for k in reversed(range(nset)):
        s = string[k]
        occ.extend([x+off for x in find1(s)])
        for i in range(0, min(64, norb-off)): 
            if not (s & numpy.uint64(1<<i)):
                vir.append(i+off)
        off += 64
    return occ, vir

def orblst2str(lst, norb):
    nset = (norb+63) // 64
    string = numpy.zeros(nset, dtype=numpy.uint64)
    for i in lst:
        toggle_bit(string, i)
    return string

def kernel_float_space(myci, h1e, eri, norb, nelec, ci0=None,
                       tol=None, lindep=None, max_cycle=None, max_space=None,
                       nroots=None, davidson_only=None,
                       max_memory=None, verbose=None, ecore=0, **kwargs):
    if verbose is None:
        log = logger.Logger(myci.stdout, myci.verbose)
    elif isinstance(verbose, logger.Logger):
        log = verbose
    else:
        log = logger.Logger(myci.stdout, verbose)
    if tol is None: tol = myci.conv_tol
    if lindep is None: lindep = myci.lindep
    if max_cycle is None: max_cycle = myci.max_cycle
    if max_space is None: max_space = myci.max_space
    if max_memory is None: max_memory = myci.max_memory
    if nroots is None: nroots = myci.nroots
    if myci.verbose >= logger.WARN:
        myci.check_sanity()

    log.info('Starting heat-bath CI algorithm...')
    log.info('Selection threshold:   %8.5f', myci.select_cutoff)
    log.info('CI coefficient cutoff: %8.5f', myci.ci_coeff_cutoff)
    log.info('Number of roots:       %2d',   nroots)

    nelec = direct_spin1._unpack_nelec(nelec, myci.spin)
    eri = ao2mo.restore(1, eri, norb)

    # Avoid resorting the integrals by storing them in memory
    eri = eri.ravel()
    eri_sorted = abs(eri).argsort()[::-1]
    jk = eri.reshape([norb]*4)
    jk = jk - jk.transpose(2,1,0,3)
    jk = jk.ravel()
    jk_sorted = abs(jk).argsort()[::-1]

# TODO: initial guess from CISD
    if ci0 is None:
        hf_str = numpy.hstack([orblst2str(range(nelec[0]), norb), orblst2str(range(nelec[1]), norb)]).reshape(1,-1)
        ci0 = [as_SCIvector(numpy.ones(1), hf_str, numpy.array([[0,0]]))]
    else:
        assert(nroots == len(ci0))

    ci0 = myci.enlarge_space(ci0, h1e, eri, jk, eri_sorted, jk_sorted, norb, nelec)

    def hop(c):
        #hc = myci.contract_2e((h1e, eri), as_SCIvector(c, ci_strs, ci_ts), norb, nelec, hdiag)
        hc = myci.contract_2e_ctypes((h1e, eri), as_SCIvector(c, ci_strs, ci_ts), norb, nelec, hdiag)
        return hc.ravel()
    precond = lambda x, e, *args: x/(hdiag-e+myci.level_shift)

    e_last = 0
    float_tol = 3e-4
    conv = False
    for icycle in range(norb):
        ci_strs, ci_ts = ci0[0]._strs, ci0[0]._ts
        float_tol = max(float_tol*.3, tol*1e2)
        log.info('\nMacroiteration %d', icycle)
        log.info('Number of CI configurations: %d', ci_strs.shape[0])
        hdiag = myci.make_hdiag(h1e, eri, ci_strs, norb, nelec)
        #e, ci0 = lib.davidson(hop, ci0.reshape(-1), precond, tol=float_tol)
        t_start = time.time()
        e, ci0 = myci.eig(hop, ci0, precond, tol=float_tol, lindep=lindep,
                          max_cycle=max_cycle, max_space=max_space, nroots=nroots,
                          max_memory=max_memory, verbose=log, **kwargs)
        if not isinstance(ci0, (tuple, list)):
            ci0 = [ci0]
            e = [e]
        t_current = time.time() - t_start
        log.debug('Timing for solving the eigenvalue problem: %10.3f', t_current)
        ci0 = [as_SCIvector(c, ci_strs, ci_ts) for c in ci0]
        de, e_last = min(e)-e_last, min(e)
        log.info('Cycle %d  E = %s  dE = %.8g', icycle, numpy.array(e)+ecore, de)

        if abs(de) < tol*1e3:
            conv = True
            break

        last_ci0_size = float(len(ci_strs))
        t_start = time.time()
        ci0 = myci.enlarge_space(ci0, h1e, eri, jk, eri_sorted, jk_sorted, norb, nelec)
        t_current = time.time() - t_start
        log.debug('Timing for selecting configurations: %10.3f', t_current)
        if ((.99 < len(ci0[0]._strs)/last_ci0_size < 1.01)):
            conv = True
            break

    ci_strs, ci_ts = ci0[0]._strs, ci0[0]._ts
    log.info('\nExtra CI in the final selected space')
    log.info('Number of CI configurations: %d', ci_strs.shape[0])
    hdiag = myci.make_hdiag(h1e, eri, ci_strs, norb, nelec)
    e, c = myci.eig(hop, ci0, precond, tol=tol, lindep=lindep,
                    max_cycle=max_cycle, max_space=max_space, nroots=nroots,
                    max_memory=max_memory, verbose=log, **kwargs)
    if not isinstance(c, (tuple, list)):
        c = [c]
        e = [e]
    log.info('\nSelected CI  E = %s', numpy.array(e)+ecore)

    return (numpy.array(e)+ecore), [as_SCIvector(ci, ci_strs, ci_ts) for ci in c]


def to_fci(civec, norb, nelec):
    assert(norb <= 64)
    neleca, nelecb = nelec
    strsa = cistring.gen_strings4orblist(range(norb), neleca)
    stradic = dict(zip(strsa,range(strsa.__len__())))
    strsb = cistring.gen_strings4orblist(range(norb), nelecb)
    strbdic = dict(zip(strsb,range(strsb.__len__())))
    na = len(stradic)
    nb = len(strbdic)
    ndet = len(civec)
    fcivec = numpy.zeros((na,nb))
    for idet, (stra, strb) in enumerate(civec._strs.reshape(ndet,2,-1)):
        ka = stradic[stra[0]]
        kb = strbdic[strb[0]]
        fcivec[ka,kb] = civec[idet]
    return fcivec

def from_fci(fcivec, ci_strs, norb, nelec):
    neleca, nelecb = nelec
    strsa = cistring.gen_strings4orblist(range(norb), neleca)
    stradic = dict(zip(strsa,range(strsa.__len__())))
    strsb = cistring.gen_strings4orblist(range(norb), nelecb)
    strbdic = dict(zip(strsb,range(strsb.__len__())))
    na = len(stradic)
    nb = len(strbdic)
    fcivec = fcivec.reshape(na,nb)
    ta = [excitation_level(s, neleca) for s in strsa.reshape(-1,1)]
    tb = [excitation_level(s, nelecb) for s in strsb.reshape(-1,1)]
    ndet = len(ci_strs)
    civec = numpy.zeros(ndet)
    ts = numpy.zeros((ndet,2), dtype=numpy.int32)
    for idet, (stra, strb) in enumerate(ci_strs.reshape(ndet,2,-1)):
        ka = stradic[stra[0]]
        kb = strbdic[strb[0]]
        civec[idet] = fcivec[ka,kb]
        ts[idet,0] = ta[ka]
        ts[idet,1] = tb[kb]
    return as_SCIvector(civec, ci_strs, ts)

class SelectedCI(direct_spin1.FCISolver):
    def __init__(self, mol=None):
        direct_spin1.FCISolver.__init__(self, mol)
        self.ci_coeff_cutoff = .5e-3
        self.select_cutoff = .5e-3
        self.conv_tol = 1e-9
        self.nroots = 1

##################################################
# don't modify the following attributes, they are not input options
        #self.converged = False
        #self.ci = None
        self._strs = None
        self._keys = set(self.__dict__.keys())

    def dump_flags(self, verbose=None):
        direct_spin1.FCISolver.dump_flags(self, verbose)
        logger.info(self, 'ci_coeff_cutoff %g', self.ci_coeff_cutoff)
        logger.info(self, 'select_cutoff   %g', self.select_cutoff)

    # define absorb_h1e for compatibility to other FCI solver
    def absorb_h1e(h1, eri, *args, **kwargs):
        return (h1, eri)

    def contract_2e(self, h1_h2, civec, norb, nelec, hdiag=None, **kwargs):

        if hasattr(civec, '_strs'):
            self._strs = civec._strs
            self._ts = civec._ts
        else:
            assert(civec.size == len(self._strs))
            civec = as_SCIvector(civec, self._strs, self._ts)
        return contract_2e(h1_h2, civec, norb, nelec, hdiag, **kwargs)

    def contract_2e_ctypes(self, h1_h2, civec, norb, nelec, hdiag=None, **kwargs):
        if hasattr(civec, '_strs'):
            self._strs = civec._strs
            self._ts = civec._ts
        else:
            assert(civec.size == len(self._strs))
            civec = as_SCIvector(civec, self._strs, self._ts)
        return contract_2e_ctypes(h1_h2, civec, norb, nelec, hdiag, **kwargs)

    def make_hdiag(self, h1e, eri, strs, norb, nelec):
        return make_hdiag(h1e, eri, strs, norb, nelec)
 
    def to_fci(self, civec, norb, nelec):

        if hasattr(civec, '_strs'):
            self._strs = civec._strs
            self._ts = civec._ts
        else:
            assert(civec.size == len(self._strs))
            civec = as_SCIvector(civec, self._strs, self._ts)

        return to_fci(civec, norb, nelec)

    enlarge_space = enlarge_space
    kernel = kernel_float_space


class _SCIvector(numpy.ndarray):
    def __array_finalize__(self, obj):
        self._ts = getattr(obj, '_ts', None)
        self._strs = getattr(obj, '_strs', None)

def as_SCIvector(civec, ci_strs, ci_ts):
    civec = civec.view(_SCIvector)
    civec._strs = ci_strs
    civec._ts = ci_ts
    return civec

def as_SCIvector_if_not(civec, ci_strs, ci_ts):
    if not hasattr(civec, '_strs'):
        civec = as_SCIvector(civec, ci_strs, ci_ts)
    return civec


if __name__ == '__main__':
    numpy.random.seed(3)
    strs = (numpy.random.random((14,3)) * 4).astype(numpy.uint64)
    print strs
    print argunique(strs)
    ts = numpy.ones((len(strs),2), dtype=numpy.int64)
    ts[10:,1] = 2
    print argunique_with_t(strs, ts)

    norb = 6
    nelec = 3,3
    hf_str = numpy.hstack([orblst2str(range(nelec[0]), norb),
                           orblst2str(range(nelec[1]), norb)]).reshape(1,-1)
    numpy.random.seed(3)
    h1 = numpy.random.random([norb]*2)**4 * 1e-2
    h1 = h1 + h1.T
    eri = numpy.random.random([norb]*4)**4 * 1e-2
    eri = eri + eri.transpose(0,1,3,2)
    eri = eri + eri.transpose(1,0,2,3)
    eri = eri + eri.transpose(2,3,0,1)
    eri_sorted = abs(eri).argsort()[::-1]
    jk = eri.reshape([norb]*4)
    jk = jk - jk.transpose(2,1,0,3)
    jk = jk.ravel()
    jk_sorted = abs(jk).argsort()[::-1]
    ts = numpy.zeros((1,2), dtype=numpy.int32)
    ci1 = as_SCIvector(numpy.ones(1), hf_str, ts)

    myci = SelectedCI()
    myci.select_cutoff = .001
    myci.ci_coeff_cutoff = .001

    ci2 = enlarge_space(myci, ci1, h1, eri, jk, eri_sorted, jk_sorted, norb, nelec)
    ci2 = ci2[0]
    print len(ci2)
    print numpy.unique(ci2._ts.view(numpy.int64)).view(numpy.int32).reshape(-1,2)

    ci2 = enlarge_space(myci, ci1, h1, eri, jk, eri_sorted, jk_sorted, norb, nelec)
    ci2 = ci2[0]
    numpy.random.seed(1)
    ci2[:] = numpy.random.random(ci2.size)
    ci2 *= 1./numpy.linalg.norm(ci2)
    ci2 = enlarge_space(myci, ci2, h1, eri, jk, eri_sorted, jk_sorted, norb, nelec)
    ci2 = ci2[0]
    print len(ci2)
    print numpy.unique(ci2._ts.view(numpy.int64)).view(numpy.int32).reshape(-1,2)

    efci = direct_spin1.kernel(h1, eri, norb, nelec, verbose=5)[0]

    ci3 = contract_2e_ctypes((h1, eri), ci2, norb, nelec)

    fci2 = to_fci(ci2, norb, nelec)
    h2e = direct_spin1.absorb_h1e(h1, eri, norb, nelec, .5)
    fci3 = direct_spin1.contract_2e(h2e, fci2, norb, nelec)
    fci3 = from_fci(fci3, ci2._strs, norb, nelec)
    #H = direct_spin1.pspace(h1, eri, norb, nelec)[1]
    #neleca, nelecb = nelec
    #strsa = cistring.gen_strings4orblist(range(norb), neleca)
    #stradic = dict(zip(strsa,range(strsa.__len__())))
    #strsb = cistring.gen_strings4orblist(range(norb), nelecb)
    #strbdic = dict(zip(strsb,range(strsb.__len__())))
    #nb = len(strbdic)
    #ndet = len(ci2)
    #idx = []
    #for idet, (stra, strb) in enumerate(ci2._strs.reshape(ndet,2,-1)):
    #    ka = stradic[stra[0]]
    #    kb = strbdic[strb[0]]
    #    idx.append(ka*nb+kb)
    #H = H[idx][:,idx]
    #print H
    print abs(ci3-fci3).sum()

    e = myci.kernel(h1, eri, norb, nelec, verbose=5)[0]
    print e, efci
