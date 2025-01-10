# Copyright 2013-2023 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

# ----------------------------------------------------------------------------
# If you submit this package back to Spack as a pull request,
# please first remove this boilerplate and all FIXME comments.
#
# This is a template package file for Spack.  We've put "FIXME"
# next to all the things you'll want to change. Once you've handled
# them, you can save this file and test your package like this:
#
#     spack install p2r-tests
#
# You can edit this file again by typing:
#
#     spack edit p2r-tests
#
# See the Spack documentation for more information on packaging.
# ----------------------------------------------------------------------------

from spack.package import *


class P2rTests(CMakePackage):
    """ propagate-2-r: mini-app for benchmarking performance portability technologies"""

    homepage = "https://github.com/kakwok/p2r-tests"
    url      = "https://github.com/kakwok/p2r-tests/archive/refs/heads/main.zip"
    git      = "https://github.com/kakwok/p2r-tests.git"

    version('main', branch='spack')
    version('kokkos', branch='spack', submodules=True)

    # Single-valued variant 'impl' to select backends
    variant('impl', default="cuda",
            values=('tbb', 'cuda', 'alpaka', 'hip', 'kokkos', 'stdpar', 'sycl'),
            multi = False,
            description = 'Select the p2r-implementation.')

    # Single-valued variant 'backend' for specifying the hardware platform
    variant('backend', default='nvidia',
                values=('cpu', 'nvidia', 'amd', 'intel'),multi=False,
                description='Select the backend hardware platform (only one is allowed).')

    # Variant 'cuda-arch' to specify the Nvidia architecture, only valid for 'nvidia' backend
    variant('cuda-arch',default="80",when="backend=nvidia",
                values=("80","70"),
                description="Specify the CUDA architecture (only valid when backend=nvidia)")

    ## Variant 'hip-arch' to specify the AMD architecture, only valid for 'amd' backend
    variant('hip-arch',default="gfx908",when="backend=amd",
                values=("gfx908","gfx906"),
                description="Specify the AMD architecture (only valid when backend=amd)")

    variant('sycl_path',default="./",when="impl=sycl",
                description="Specify the CUDA path for clang (only valid when backend=nvidia)")

    variant('sycl_cuda_path',default="/home/kkwok/sycl_workspace/llvm/build/bin/",when="impl=sycl",
                description="Specify the SYCL path for clang")

    # p2r options 
    variant('niter', default="5"   ,description = 'Number of iterations (NITER) to be run.')
    variant('bsize', default="32"  ,description = 'Number of tracks in each SoA (bsize).')
    variant('ntrks', default="8192",description = 'Number of tracks in each event (dividible by bsize).')
    variant('nevts', default="100" ,description = 'Number of events (nevts).')
    variant('nthreads', default="96" ,description = 'Number of events CPU threads used in TBB impl only.')

    # Define dependencies based on the selected impl and backend
    depends_on('cmake@3.22.1:', type='build')
    #depends_on('kokkos', when='impl=kokkos')                             ## not using the official spack-kokkos
    depends_on('kokkos-nvcc-wrapper', when='impl=kokkos backend=nvidia')  ## using the spack nvcc wrapper
    depends_on('alpaka@1.2.0:', when='impl=alpaka')
    depends_on('cuda@11.6.2:', when='backend=nvidia')
    depends_on('nvhpc@22.7:', when='impl=stdpar')
    depends_on('hip@5.6.1:', when='backend=amd')
    depends_on('intel-tbb@2021.12.0:', when='impl=tbb', type=('build', 'link', 'run'))
    depends_on('intel-tbb@2021.12.0:', when='impl=alpaka backend=cpu', type='build')

    # See https://spdx.org/licenses/ for a list.
    license("Apache-2.0")

    maintainers("kakwok")

    def cmake_args(self):

           #from : https://kokkos.org/kokkos-core-wiki/keywords.html#nvidia-gpus
           kokkos_cuda_arch = {
              "90": "Kokkos_ARCH_HOPPER90",
              "89": "Kokkos_ARCH_ADA89",
              "86": "Kokkos_ARCH_AMPERE86",
              "80": "Kokkos_ARCH_AMPERE80",
              "75": "Kokkos_ARCH_TURING75",
              "70": "Kokkos_ARCH_VOLTA70",
           }
           #from : https://kokkos.org/kokkos-core-wiki/keywords.html#nvidia-gpus
           kokkos_amd_arch = {
              "gfx906": "Kokkos_ARCH_VEGA906",
              "gfx908": "Kokkos_ARCH_VEGA908",
           }

           args = []
    
           # Extract the selected values of impl and backend
           impl = self.spec.variants['impl'].value
           backend = self.spec.variants['backend'].value
           niter = self.spec.variants['niter'].value
           bsize = self.spec.variants['bsize'].value
           ntrks = self.spec.variants['ntrks'].value
           nevts = self.spec.variants['nevts'].value
           nthreads = self.spec.variants['nthreads'].value
    
           args.append(f"-DBUILD_TARGET={impl}")
           args.append(f"-DNITER={niter}")
           args.append(f"-Dbsize={bsize}")
           args.append(f"-Dntrks={ntrks}")
           args.append(f"-Dnevts={nevts}")

           # Handling CUDA
           if impl == 'cuda':
               if backend == 'nvidia':
                   args.append('-DCUDA_ARCH={0}'.format(self.spec.variants['cuda-arch'].value))
               else:
                   raise InstallError("CUDA is only supported with NVIDIA backend")

           # Handling HIP
           if impl == 'hip':
               if backend == 'amd':
                   args.append('-DENABLE_HIP=ON')
               else:
                   raise InstallError("HIP is only supported with AMD backend")
    
           # Handling Kokkos
           if impl == 'kokkos':
               # Kokkos backend specific handling
               if backend == 'nvidia':
                   args.append('-DKokkos_ENABLE_CUDA=ON')
                   args.append('-D{0}=ON'.format(kokkos_cuda_arch[self.spec.variants['cuda-arch'].value]))  
                   args.append('-DKokkos_ENABLE_CUDA_CONSTEXPR=On')  
                   args.append('-DKokkos_ENABLE_CUDA_LAMBDA=On')  
                   args.append('-DCMAKE_CXX_FLAGS="-lineinfo"')  
                   args.append('-DCMAKE_CXX_COMPILER={0}'.format(self.spec["kokkos-nvcc-wrapper"].kokkos_cxx))  
                   #args.append('-DCMAKE_CXX_COMPILER={0}/kokkos/bin/nvcc_wrapper'.format(self.stage.source_path))  
               elif backend == 'amd':
                   args.append('-DKokkos_ENABLE_HIP=ON')
                   args.append('-DCMAKE_CXX_STANDARD=17')
                   args.append('-DCMAKE_CXX_COMPILER=hipcc')
                   args.append('-D{0}=ON'.format(kokkos_amd_arch[self.spec.variants['hip-arch'].value]))  
               elif backend == 'cpu':
                   args.append('-DKokkos_ENABLE_OPENMP=ON')
                   args.append('-DCMAKE_CXX_STANDARD=17')
                   args.append('-DCMAKE_CXX_COMPILER=g++')
                   args.append(f'-Dkokkos-threads={bsize}')
               else:
                   raise InstallError(f"Kokkos implementation is only supported for backend = navidia, amd and cpu, but got backend = {backend}")
           # Handling Alpaka
           if impl == 'alpaka':
               args.append('-DENABLE_ALPAKA=ON')
               args.append('-DCMAKE_BUILD_TYPE=Release')
               args.append('CMAKE_FIND_DEBUG_MODE=ON')
               if backend == 'nvidia':
                   args.append('-Dalpaka_ACC_GPU_CUDA_ENABLE=ON')
                   args.append('-DCMAKE_CXX_COMPILER=g++')
                   args.append('-DCMAKE_C_COMPILER=gcc')
                   args.append('-DCMAKE_CUDA_COMPILER=nvcc')
                   args.append('-DCMAKE_CUDA_ARCHITECTURES={0}'.format(self.spec.variants['cuda-arch'].value))
               #elif backend == 'amd':
                   #WIP
                   #args.append('-Dalpaka_ACC_GPU_HIP_ENABLE=ON')
                   #args.append('-DCMAKE_CXX_COMPILER=hipcc')
                   #args.append('-DCMAKE_HIP_ARCHITECTURES={0}'.format(self.spec.variants['hip-arch'].value))
               elif backend == 'cpu':
                   args.append('-Dalpaka_ACC_CPU_B_TBB_T_SEQ_ENABLE=ON')
                   args.append('-DCMAKE_CXX_STANDARD=17')
                   args.append('-DCMAKE_CXX_COMPILER=g++')
               else:
                   raise InstallError(f"Alpaka implementation is only supported for backend = navidia, amd and cpu, but got backend = {backend}")
           # Handling TBB
           if impl == 'tbb':
               if backend == 'cpu':
                   args.append('-DCMAKE_CXX_COMPILER=g++')
                   args.append('-DCMAKE_C_COMPILER=gcc')
                   args.append(f"-Dnthreads={nthreads}")
               else:
                   raise InstallError("TBB is only supported with CPU backend")
    
           # Handling stdpar
           if impl == 'stdpar':
               args.append('-DENABLE_STDPAR=ON')
               if backend == 'nvidia':
                   args.append('-DCUDA_ARCH={0}'.format(self.spec.variants['cuda-arch'].value))
               elif backend == 'cpu':
                   args.append('-DBACKEND=cpu')
               else:
                   raise InstallError(f"stdpar implementation is only supported for backend = navidia and cpu, but got backend = {backend}")
    
           # Handling SYCL
           if impl == 'sycl':
               if backend =='nvidia':
                   args.append('-DCUDA_PATH={0}'.format(self.spec.variants["sycl_cuda_path"].value))  
                   args.append('-DSYCL_PATH={0}'.format(self.spec.variants["sycl_path"].value))  
               else:
                   raise InstallError(f"sycl implementation is only supported for backend = navidia and cpu, but got backend = {backend}")
    
           return args
