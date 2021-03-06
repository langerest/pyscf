# Copyright 2014-2018 The PySCF Developers. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function, division
import os,unittest,numpy as np
from pyscf.nao.chi0_matvec import chi0_matvec
from pyscf import gto, scf, tddft
from pyscf.data.nist import HARTREE2EV

class KnowValues(unittest.TestCase):

  def test_131_h2b_uhf_nonin_pb(self):
    """ This  """
    mol = gto.M(verbose=1,atom='B 0 0 0; H 0 0.489 1.074; H 0 0.489 -1.074',basis='cc-pvdz',spin=3)
    gto_mf = scf.UHF(mol)
    gto_mf.kernel()
    nao_mf = chi0_matvec(gto=mol, mf=gto_mf, tol_loc=1e-5, tol_biloc=1e-7)
    comega = np.arange(0.0, 2.0, 0.01) + 1j*0.03
    pnonin = -nao_mf.comp_polariz_nonin_ave(comega, verbosity=1).imag
    data = np.array([comega.real*HARTREE2EV, pnonin])
    np.savetxt('test_131_h2b_uhf_nonin_pb.txt', data.T, fmt=['%f','%f'])
    data_ref = np.loadtxt('test_131_h2b_uhf_nonin_pb.txt-ref').T
    self.assertTrue(np.allclose(data_ref, data, atol=1e-6, rtol=1e-3))
    
if __name__ == "__main__": unittest.main()
