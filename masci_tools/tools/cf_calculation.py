# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), Forschungszentrum Jülich GmbH, IAS-1/PGI-1, Germany.         #
#                All rights reserved.                                         #
# This file is part of the Masci-tools package.                               #
# (Material science tools)                                                    #
#                                                                             #
# The code is hosted on GitHub at https://github.com/judftteam/masci-tools.   #
# For further information on the license, see the LICENSE.txt file.           #
# For further information please visit http://judft.de/.                      #
#                                                                             #
###############################################################################
"""This file contains a class to compute the crystalfield
   coefficients from convoluting the charge density with the potential
   which produces the crystalfield. This is both compatible with
   the Yttrium-Analogue approximation and self-consitent calculation of
   the potential

"""
import h5py
import os
import csv
from collections import namedtuple, defaultdict
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
from scipy.interpolate import interp1d
from scipy.special import sph_harm
from masci_tools.util.constants import HTR_TO_KELVIN
from masci_tools.io.common_functions import skipHeader


#This namedtuple is used as the return value for the crystal field calculation to have easy access
#to all the necessary information
CFCoefficient = namedtuple('CFCoefficient', ['l', 'm', 'spin_up', 'spin_down', 'unit', 'convention'])


class CFcalculation:
    r"""Class for calculating Crystal Field coefficients using the procedure
    described in C.E. Patrick, J.B. Staunton: J. Phys.: Condens. Matter 31, 305901 (2019)

    Using the formula:
        .. math::
            B_{lm} = \sqrt{\frac{2l+1}{4\pi}} \int^{R_{MT}}\! dr r^2 V_{lm}(r)n_{4f}(r)

        The read in quantities are interpolated from logarithmic meshes to equidistant meshes

        The function constructs an equidistant mesh between the muffin tin radius
        defined in general['refRMT'] and with general['nsize'] points

    Parameters for constructor:
        general (dict): Defines the general parameters of the calculation

            valid keys:
                nsize (int): number of radial points in the interpolated mesh
                refRMT (str): Either 'pot' or 'cdn'. Defines which muffin-tin radius
                              is used for the equidistant mesh.
                IMPORTANT: If txt files are used the muffin-tin radius has to be provided explicitly
                cutoff (float): Defines minimum value that has to appear in potentials to not be omitted
                                (Only HDF)
                onlyM0 (bool): Ignores coefficients with m!=0 if True

    Attributes:
        cdn (dict): Contains the data for the normed charge density (rmesh,data). cdn is expected as r^2n(r)
        general (dict): General Configuration Parameters
        int (dict): Contains the interpolated data
        interpolated (bool): Switch which tells the program if the interpolation was performed
        plotDetails (dict): Dictionary to define parameters for the plots
        vlm (dict): Contains the data for the potentials (rmesh, and keys for (l,m) combinations)

   """

    __version__ = '0.1.0'

    _general_default = {
        'nsize': 4000,  #Number of grid points in the interpolated mesh
        'refRMT': 'pot',  #Which Muffin-Tin radius is used as reference for interpolation
        'cutoff': 1e-3,  #Under this potentials are dismissed
        'onlyM0': False,
        'quiet': False,
    }

    #prefactor for converting Blm to Alm<r^l>
    _alphalm = {
        (0, 0): 1.0,
        (2, 0): 0.5,
        (2, 2): np.sqrt(6.0) / 2.0,
        (4, 0): 1.0 / 8.0,
        (4, 2): np.sqrt(10.0) / 4.0,
        (4, 3): -np.sqrt(35.0) / 2.0,
        (4, 4): np.sqrt(70.0) / 8.0,
        (6, 0): 1.0 / 16.0,
        (6, 2): np.sqrt(105.0) / 16.0,
        (6, 3): -np.sqrt(105.0) / 8.0,
        (6, 4): 3.0 * np.sqrt(14.0) / 16.0,
        (6, 6): np.sqrt(231.0) / 16.0,
    }

    def __init__(self, general=None):
        """Initialize the CFcalculation object
        and overwrite the default general dict with the given argument

        """

        self.vlm = {}
        self.cdn = {}

        self.denNorm = None
        self.phi = None
        self.theta = None

        self.interpolated = False
        self.int = {}
        self.bravaisMat = {}

        self.general = {}
        self.general.update(self._general_default)
        if general:
            #Verify that there are no unknown keys
            if general.keys().difference(self._general_default.keys()):
                raise KeyError(f'Unknown Keys: {general.keys().difference(self._general_default.keys())}')
            self.general.update(general)

    def prefactor(self, l, m):
        """Gives the lm dependent prefactor for conversion between
        Blm and Alm coefficients

        Args:
            l (int): orbital quantum number
            m (int): magnetic quantum number

        Returns:
            float: Prefactor for conversion to Steven's Coefficients
        """
        if (l, abs(m)) in self._alphalm:
            return self._alphalm[(l, abs(m))]
        else:
            return 0.0

    def readPot(self, *args, lm=[], **kwargs):
        """Reads in the potentials for the CF coefficient calculation
        If hdf files are given also the muffin tin radius is read in

        Parameters:
            *args: Expects string filenames for the potentials to read in
                   The function expects either HDF files or txt files with the
                   format (rmesh,vlmup,vlmdn)
            lm (list of tuples): Defines the l and m indices for the given txt files
            **kwargs:
                    atomType (int): Defines the atomType to read in (only for HDF files)
                    header (int):   Define how many lines to skip in the beginning of txt file
                    complexData (bool): Define if the data in the text file is complex

        Raises:
            ValueError: lm indices list length has to match number of files read in

        """

        if 'atomType' in kwargs:
            atomType = kwargs['atomType']
        else:
            atomType = 1

        if 'header' in kwargs:
            header = kwargs['header']
        else:
            header = 0

        if 'complexData' in kwargs:
            complexData = kwargs['complexData']
        else:
            complexData = True

        #Reads in the filenames given in args as potentials
        for index, file in enumerate(args):
            if isinstance(file, str):
                basename, extension = os.path.splitext(file)
                if extension == '.hdf':
                    with h5py.File(file, 'r') as hdffile:
                        self.__readpotHDF(hdffile, atomType)
                else:
                    if index >= len(lm):
                        raise ValueError('Not enough lm indices for the given files')
                    self.__readpottxt(file, lm[index], header=header, complexData=complexData)
            else:
                self.__readpotHDF(file, atomType)

    def readCDN(self, file, **kwargs):
        """Reads in the normed charge density for the CF coefficient calculation
        If hdf files are given also the muffin tin radius is read in

        Parameters:
            file: Expects string filename for the charge density to read in
                  The function expects either HDF files or txt files with the
                  format (rmesh,cdn).
                  The charge density should be given as r^2n(r) and normed to 1
            **kwargs:
                atomType (int):  Defines the atomType to read in (only for HDF files)
                header (int):    Define how many lines to skip in the beginning of txt file

        """

        if 'atomType' in kwargs:
            atomType = kwargs['atomType']
        else:
            atomType = 1

        if 'header' in kwargs:
            header = kwargs['header']
        else:
            header = 0

        if isinstance(file, str):
            basename, extension = os.path.splitext(file)
            if extension == '.hdf':
                with h5py.File(file, 'r') as hdffile:
                    self.__readcdnHDF(hdffile, atomType)
            else:
                self.__readcdntxt(file, header=header)
        else:
            self.__readcdnHDF(file, atomType)

    def __readpotHDF(self, hdffile, atomType):
        """Read in the potential from a HDF file

        """

        info = hdffile.get('general')
        numPOT = info.attrs.__getitem__('numPOT')[0]
        if 'bravaisMatrix' in info:
            self.bravaisMat['pot'] = np.array(info.get('bravaisMatrix'))

        if numPOT == 0:
            raise IOError('No potentials found in {}'.format(hdffile))

        if 'pot-{}'.format(atomType) in hdffile:
            _pot = hdffile.get('pot-{}'.format(atomType))

            self.vlm['RMT'] = _pot.attrs.__getitem__('RMT')[0]
            for key in _pot.keys():

                if key == 'rmesh':
                    _rmesh = _pot.get(key)
                    self.vlm['rmesh'] = np.array(_rmesh)
                else:
                    _vlm = _pot.get(key)
                    l = _vlm.attrs.__getitem__('l')[0]
                    m = _vlm.attrs.__getitem__('m')[0]

                    _data = _vlm.get('vlm')
                    _data = np.array(_data[:, :, 0] + 1j * _data[:, :, 1])
                    if abs(_data).max() >= self.general['cutoff']:
                        self.vlm[(l, m)] = _data

        else:
            raise IOError('No potential for atomType {} found in {}'.format(atomType, hdffile))

        if not self.general['quiet']:
            print('readPOTHDF: Generated the following information: {}'.format(self.vlm.keys()))

    def __readpottxt(self, file, index, header=0, complexData=True):
        """Read in the potential for the (l,m) tuple 'index' from a txt file
        The muffin-tin radius is infered from the biggest argument in the rmesh
        """

        with open(file, newline='') as csvfile:
            reader = csv.reader(csvfile, delimiter=' ', quotechar='|')

            if index not in self.vlm:
                self.vlm[index] = []
                self.vlm[index].append([])
                self.vlm[index].append([])
            else:
                raise KeyError('Multiple definitions for potential {}'.format(index))

            self.vlm['rmesh'] = []

            for line in skipHeader(reader, header):
                while ('' in line):
                    line.remove('')
                self.vlm['rmesh'].append(float(line[0]))
                if complexData:
                    self.vlm[index][0].append(float(line[1]) + 1j * float(line[2]))
                    self.vlm[index][1].append(float(line[3]) + 1j * float(line[4]))
                else:
                    self.vlm[index][0].append(float(line[1]))
                    self.vlm[index][1].append(float(line[2]))

            self.vlm[index] = np.array(self.vlm[index])
            self.vlm['rmesh'] = np.array(self.vlm['rmesh'])
            self.vlm['RMT'] = max(self.vlm['rmesh'])

    def __readcdnHDF(self, hdffile, atomType):
        """Read in the charge density from a HDF file

        """

        info = hdffile.get('general')
        numCDN = info.attrs.__getitem__('numCDN')[0]
        if 'bravaisMatrix' in info:
            self.bravaisMat['cdn'] = np.array(info.get('bravaisMatrix'))

        if numCDN == 0:
            raise IOError('No charge densities found in {}'.format(hdffile))

        if 'cdn-{}'.format(atomType) in hdffile:
            _cdn = hdffile.get('cdn-{}'.format(atomType))
            self.cdn['RMT'] = _cdn.attrs.__getitem__('RMT')[0]
            _rmesh = _cdn.get('rmesh')
            self.cdn['rmesh'] = np.array(_rmesh)
            _data = _cdn.get('cdn')
            self.cdn['data'] = np.array(_data)

        else:
            raise IOError('No charge density for atomType {} found in {}'.format(atomType, hdffile))

        if not self.general['quiet']:
            print('readcdnHDF: Generated the following information: {}'.format(self.cdn.keys()))

    def __readcdntxt(self, file, header=0):
        """Read in the charge density from a txt file
        The muffin-tin radius is infered from the biggest argument in the rmesh
        """

        with open(file, newline='') as csvfile:
            reader = csv.reader(csvfile, delimiter=' ', quotechar='|')

            if 'data' not in self.cdn:
                self.cdn['data'] = []
            else:
                raise KeyError('Charge density already read in')

            self.cdn['rmesh'] = []

            for line in skipHeader(reader, header):
                while ('' in line):
                    line.remove('')

                self.cdn['rmesh'].append(float(line[0]))
                self.cdn['data'].append(float(line[1]))

            self.cdn['data'] = np.array(self.cdn['data'])
            self.cdn['rmesh'] = np.array(self.cdn['rmesh'])
            self.cdn['RMT'] = max(self.cdn['rmesh'])

    def _validateInput(self):
        """Validate that the object can be used to execute the calculation
        Checks that the given bravais matrices are equal if given
        """

        if 'data' not in self.cdn or 'rmesh' not in self.cdn:
            raise ValueError('Charge density input incomplete')

        if 'rmesh' not in self.vlm or len(self.vlm.items()) <= 2:
            raise ValueError('Potential input incomplete')

        if 'cdn' in self.bravaisMat and 'pot' in self.bravaisMat:
            diffBravais = self.bravaisMat['cdn'] - self.bravaisMat['pot']
            if np.any(np.abs(diffBravais) > 1e-12):
                pass
                #raise ValueError('Differing definitions of potentials and charge density bravais matrix')

    def _interpolate(self):
        """Interpolate all quantities to a common equidistant radial mesh

        """

        if self.general['refRMT'] == 'pot':
            refRMT = self.vlm['RMT']
        elif self.general['refRMT'] == 'cdn':
            refRMT = self.cdn['RMT']

        self.int = defaultdict(dict)

        self.int['rmesh'] = np.arange(0.0, refRMT, refRMT / self.general['nsize'])
        self.int['cdn'] = interp1d(self.cdn['rmesh'], self.cdn['data'], fill_value='extrapolate')

        for key, value in self.vlm.items():
            if key != 'RMT' and key != 'rmesh':
                self.int[key]['spin-up'] = interp1d(self.vlm['rmesh'], self.vlm[key][0, :], fill_value='extrapolate')
                self.int[key]['spin-down'] = interp1d(self.vlm['rmesh'],
                                                         self.vlm[key][1, :],
                                                         fill_value='extrapolate')
        self.interpolated = True

    def performIntegration(self, convert=True):
        """Performs the integration to obtain the crystal field coefficients
        If the data was not already interpolated, the interpolation will
        be performed beforehand

        Parameters:
            convert (bool): converts to Steven's coefficients (if True)

        Returns:
            dict: CF coeffients given as keys (l,m,'up') or (l,m,'dn') for different
                  spin directions in K

        """

        self._validateInput()

        if 'cdn' in self.bravaisMat and 'pot' in self.bravaisMat:
            a_vector = self.bravaisMat['pot'][0, :]
            c_vector = self.bravaisMat['pot'][2, :]

            self.theta = np.arccos(c_vector[2] / (np.linalg.norm(c_vector)))
            self.phi = np.arccos(a_vector[0] / (np.linalg.norm(a_vector)))

            if not self.general['quiet']:
                print(fr'Angle between lattice vector c and z-axis: {self.theta/np.pi:5.3f} $\pi$')
                print(fr'Angle between lattice vector a and x-axis: {self.phi/np.pi:5.3f} $\pi$')

        if not self.interpolated:
            self._interpolate()

        self.denNorm = np.trapz(self.int['cdn'](self.int['rmesh']), self.int['rmesh'])
        if not self.general['quiet']:
            print(f'Density normalization = {self.denNorm}')

        result = []
        for lmkey, vlm in [(key,val) for key, val in self.int.items() if isinstance(key, tuple)]:
            l, m = lmkey
            if not self.general['onlyM0'] or m == 0:
                integral = {}
                for key, pot in vlm.items():
                    integral[key] = np.trapz(pot(self.int['rmesh']) * self.int['cdn'](self.int['rmesh']), self.int['rmesh'])
                    integral[key] *= np.sqrt((2.0 * l + 1.0) / (4.0 * np.pi)) * HTR_TO_KELVIN

                if convert:
                    integral = {key: val.real * self.prefactor(l, m) for key,val in integral.items()}
                    coeff = CFCoefficient(l=l, m=m, spin_up=integral['spin-up'], spin_down=integral['spin-down'], unit='K',convention='Stevens')
                else:
                    coeff = CFCoefficient(l=l, m=m, spin_up=integral['spin-up'], spin_down=integral['spin-down'], unit='K',convention='Wybourne')

                result.append(coeff)

        result.sort(key=lambda item: (item.l, abs(item.m)))

        if not self.general['quiet']:

            print(f'\nThe following results were obtained with the {result[0].convention} convention:')

            if any([isinstance(coeff.spin_up, complex) for coeff in result]):
                print('l  m', '       $C^{up}_{lm}$ [K]              ', '       $C^{dn}_{lm}$ [K]')
            else:
                print('l  m', '       $C^{up}_{lm}$ [K]', '       $C^{dn}_{lm}$ [K]')
            for coeff in result:
                if isinstance(coeff.spin_up, complex):
                    print(f'{coeff.l:d}{coeff.m:>-3d}{coeff.spin_up.real:>+25.8f}{coeff.spin_up.imag:>+11.8f} i {coeff.spin_down.real:>+25.8f}{coeff.spin_down.imag:>+11.8f} i ')
                else:
                    print(f'{coeff.l:d}{coeff.m:>-3d}{coeff.spin_up:>+25.8f}{coeff.spin_down:>+25.8f}')

        return result


def plot_crystal_field_calculation(cfcalc, filename='crystal_field_calc', pot_title='Potential', cdn_title='Density', xlabel='$R$ (Bohr)',pot_ylabel='$Vpot$ (Hartree)',cdn_ylabel='Density', fontsize=12, labelsize=12, pot_colors=None):
        """Plot the given potentials and charge densities

        Parameters:
            :param filename: str, Define the filename to save the figure
            :param pot_title: Title for the potential subplot
            :param cdn_title: Title for the charge density subplot
            :param xlabel: label for the x axis of both subplots
            :param pot_ylabel: label for the y axis of the potential subplot
            :param cdn_ylabel: label for the y axis f the charge density subplot
            :param fontsize: fontsize for titles and labels on the axis
            :param labelsize: fontsize for the ticks on the axis,

        """

        cfcalc._validateInput()

        if not cfcalc.interpolated:
            cfcalc._interpolate()

        if pot_colors is None:
            pot_colors = ['black', 'red', 'blue', 'orange', 'green', 'purple']

        color_iter = iter(pot_colors)

        fig, axs = plt.subplots(1, 2)
        ax = axs[0]


        for lmkey, vlm in [(key,val) for key, val in cfcalc.int.items() if isinstance(key, tuple)]:
            l, m = lmkey
            if not cfcalc.general['onlyM0'] or m == 0:
                try:
                    color = next(color_iter)
                except StopIteration:
                    color = None
                line, = ax.plot(cfcalc.int['rmesh'],
                        vlm['spin-up'](cfcalc.int['rmesh']).real,
                        '-',
                        color=color,
                        label=rf'$V_{{{l}{m}}}$')
                ax.plot(cfcalc.int['rmesh'], vlm['spin-down'](cfcalc.int['rmesh']).real, '--', color=line.get_color())
        ax.set_xlabel(xlabel, fontsize=fontsize)
        ax.set_ylabel(pot_ylabel, fontsize=fontsize)
        ax.legend(loc=2, ncol=1, borderaxespad=0.0, fontsize=fontsize)
        ax.tick_params(labelsize=labelsize)
        ax.set_title(pot_title, fontsize=fontsize)

        ax = axs[1]
        ax.plot(cfcalc.cdn['rmesh'], cfcalc.cdn['data'], '-', color='black', label=r'$n(r)$')
        ax.plot(cfcalc.int['rmesh'], cfcalc.int['cdn'](cfcalc.int['rmesh']), '--', color='blue')
        ax.set_xlabel(xlabel, fontsize=fontsize)
        ax.set_ylabel(cdn_ylabel, fontsize=fontsize)
        ax.legend(loc=2, ncol=1, borderaxespad=0.0, fontsize=fontsize)
        ax.tick_params(labelsize=labelsize)
        ax.set_title(cdn_title, fontsize=fontsize)

        fig.set_size_inches(14.0, 10.0)
        fig.subplots_adjust(left=0.10, bottom=0.2, right=0.90, wspace=0.4, hspace=0.4)
        plt.savefig(filename, format='png')
        plt.show()


def plot_crystal_field_potential(cfcoeffs, filename='crystal_field_potential_areaplot', spin='avg', phi=0.0):
        """Plots the angular dependence of the calculated CF potential as well
        as a plane defined by phi.

        Parameters:
            :param filename: str, defines the filename to save the figure
            :param spin: str; Either 'up', 'dn' or 'avg'. Which spin direction to plot
                         ('avg'-> ('up'+'dn')/2.0)
            :param phi: float, defines the phi angle of the plane

        :raises AssertionError: When coefficients are provided as wrong types or in the wrong convention

        """

        assert all([isinstance(coeff, CFCoefficient) for coeff in cfcoeffs]), \
               'Only provide a list of CFCoefficients to plot_crystal_field_potential'

        #generate the thetha phi meshgrid
        theta_grid = np.linspace(0, np.pi, 181)
        phi_grid = np.linspace(0.0, 2.0 * np.pi, 361)
        xv, yv = np.meshgrid(phi_grid, theta_grid)
        cf_grid = np.zeros((181, 361), dtype='complex')


        for coeff in cfcoeffs:
            assert coeff.convention == 'Wybourne', 'Wrong convention for plotting in spherical harmonics basis'
            if spin == 'avg':
                value = 0.5 * (coeff.spin_up + coeff.spin_down)
            elif spin == 'up':
                value = coeff.spin_up
            elif spin == 'down':
                value = coeff.spin_down
            else:
                raise ValueError(f"Invalid Argument for spin: '{spin}'")
            if coeff.m>=0:
                cf_grid += value * sph_harm(coeff.m, coeff.l, xv, yv)

        #Plot the angular dependence
        maxv = max(cf_grid.real.max(), abs(cf_grid.real.min()))
        tickFontsize = 14
        labelFontsize = 20
        #Angular dependence plot
        fig = plt.figure(figsize=(15, 5))
        gs = mpl.gridspec.GridSpec(1, 2, width_ratios=[2.0, 1.5])
        ax = plt.subplot(gs[0])
        plt.sca(ax)
        plt.imshow(cf_grid.real, origin='upper', cmap='coolwarm', vmin=-maxv, vmax=maxv, aspect='auto')
        ax.set_title('Angular Dependence', fontsize=labelFontsize)
        ax.set_xlabel(r'$\phi$', fontsize=labelFontsize)
        ax.set_xticks([0.0, 90.0, 180.0, 270.0, 360.0])
        ax.set_xticklabels([r'0', r'$\pi/2$', r'$\pi$', r'$3\pi/2$', r'$2\pi$'], fontsize=tickFontsize)
        ax.set_ylabel(r'$\theta$', fontsize=labelFontsize)
        ax.set_yticks([0.0, 45.0, 90.0, 135.0, 180.0])
        ax.set_yticklabels([r'$\pi/2$', r'$\pi/4$', r'$0.0$', r'$-\pi/4$', r'$-\pi/2$'], fontsize=tickFontsize)

        if np.abs(phi_grid - phi).min() > 1e-5:
            raise ValueError(f'Angle {phi} not found in grid')
        else:
            phi_ind = np.abs(phi_grid - phi).argmin()

        theta_grid_pm = list(-1.0 * theta_grid)
        theta_cf = list(cf_grid[:, phi_ind])
        for index, theta in enumerate(theta_grid):
            theta_grid_pm.append(theta)
            theta_cf.append(theta_cf[index])

        theta_grid = np.array(theta_grid)
        theta_cf = np.array(theta_cf)

        #interpolate
        theta_cf = interp1d(theta_grid_pm, theta_cf.real, fill_value='extrapolate')

        nx = 200
        ny = 200
        #Define the cartesian grid between -1 and 1
        x = np.linspace(-1, 1, nx)
        y = np.linspace(-1, 1, ny)
        xv, yv = np.meshgrid(x, y)

        z = theta_cf(np.arctan(xv / yv))

        phi_fract = phi / np.pi

        labelFontsize = 14
        tickFontsize = 14

        ax = plt.subplot(gs[1])
        plt.sca(ax)
        plt.imshow(z, origin='upper', cmap='coolwarm', vmin=-maxv, vmax=maxv, aspect='auto')
        cbar = plt.colorbar(shrink=0.8)
        cbar.set_label(r'$V_{{CF}}$ [K]', fontsize=labelFontsize)
        cbar.ax.tick_params(labelsize=14)
        ax.set_title(r'Crystal Field potential for $\phi={{{:.2f}}}\pi$'.format(phi_fract), fontsize=labelFontsize)
        ax.set_xlabel(r'x [Bohr]', fontsize=labelFontsize)
        ax.set_xticks([0, nx / 4.0, nx / 2.0, 3.0 * nx / 4.0, nx - 1])
        ax.set_xticklabels([r'-1.0', r'-0.5', r'0.0', r'0.5', r'1.0'], fontsize=tickFontsize)
        ax.set_ylabel(r'y [Bohr]', fontsize=labelFontsize)
        ax.set_yticks([0, ny / 4.0, ny / 2.0, 3.0 * ny / 4.0, ny - 1])
        ax.set_yticklabels([r'1.0', r'0.5', r'0.0', r'-0.5', r'-1.0'], fontsize=tickFontsize)
        fig.set_constrained_layout_pads(w_pad=0., h_pad=0.0, hspace=0., wspace=0.)

        plt.savefig(filename, format='png')
        plt.show()
