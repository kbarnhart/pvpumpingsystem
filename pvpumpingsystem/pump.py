# -*- coding: utf-8 -*-
"""
Module defining class and functions for modeling the pump.

@author: Tanguy Lunel, Sergio Gualteros

"""

import numpy as np
import pandas as pd
from itertools import count
from matplotlib.pyplot import plot
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # needed for plotting in 3d
import scipy.optimize as opt
import warnings
import re

# pvpumpingsystem modules:
from pvpumpingsystem import inverse
from pvpumpingsystem import errors
from pvpumpingsystem import function_models

# FIXME: doc states lpm, tdh, current, because they can be used for creating
# object with __init__(), but not available anymore then as attribute.
# What is the proper way to document it.


class Pump:
    """
    Class representing a motor-pump.

    Attributes
    ----------
        path: str, default=''
            The path to the txt file with the pump specifications.

        lpm: dict, default is None
            Dictionary containing pump specs: voltage as keys and
            flow rate as values.

        tdh: dict, default is None
            Dictionary containing pump specs: voltage as keys and
            total dynamic head as values.

        current: dict, default is None
            Dictionary containing pump specs: voltage as keys and
            current drawn by pump as values.

        motor_electrical_architecture: str, default is None
            'permanent_magnet', 'series_excited', 'shunt_excited',
            'separately_excited'.

        modeling_method: str, , default is 'arab'
            name of the method used for modeling the pump.

        idname: str, default is None
            name of the pump

        price: numeric, default is None
            The price of the pump

        controller: str, default is None
            Name of controller

    Computed Attributes: (available after the object declaration)

        voltage_list: list,
            list of voltage (the keys of preceding dictionaries) [V]

        specs: pandas.DataFrame,
            Dataframe with columns of following numeric:
                'voltage': voltage at pump input [V]
                'current': current at pump input [A]
                'power': electrical power at pump input [W]]
                'tdh': total dynamic head in the pipes at output [m]
                'flow': pump output flow rate [liter per minute]

        data_completeness: dict,
            Provides some figures to assess the completeness of the data.
            (for more details, see pump.specs_completeness() )

    """
    _ids = count(1)

    def __init__(self, path,
                 lpm=None, tdh=None, current=None,
                 motor_electrical_architecture=None,
                 idname=None,
                 price=np.nan,
                 controller=None,
                 diameter_output=None,
                 modeling_method='arab'):

        self.id = next(self._ids)

        self.controller = controller

        # retrieve pump data from txt datasheet given by path
        if None in (lpm, tdh, current):
            self.specs, metadata = get_data_pump(path)
            self.voltage_list = self.specs.voltage.drop_duplicates()
            try:
                self.price = float(metadata['price'])
                if not np.isnan(price):
                    self.price = price
                    warnings.warn('price attribute overwritten.')
            except KeyError:
                self.price = price

            try:
                self.idname = metadata['pump name']
                if idname is not None:
                    self.idname = idname
                    warnings.warn('idname attribute overwritten.')
            except KeyError:
                self.idname = idname

            try:
                self.motor_electrical_architecture = \
                    metadata['electrical architecture']
                if motor_electrical_architecture is not None:
                    self.motor_electrical_architecture = \
                        motor_electrical_architecture
                    warnings.warn('motor_electrical_architecture '
                                  'attribute overwritten.')
            except KeyError:
                self.motor_electrical_architecture = \
                    motor_electrical_architecture

        # retrieve pump data from dict given in parameter
        else:
            self.voltage_list = list(lpm.keys())
            # put data in the form of DataFrame
            vol = []
            head = []
            cur = []
            flow = []
            power = []
            for V in self.voltage_list:
                for i, Idata in enumerate(current[V]):
                    vol.append(V)
                    head.append(tdh[V][i])
                    cur.append(Idata)
                    flow.append(lpm[V][i])
                    power.append(V*Idata)
            self.specs = pd.DataFrame({'voltage': vol,
                                       'tdh': head,
                                       'current': cur,
                                       'flow': flow,
                                       'power': power})

        self.range = pd.DataFrame([self.specs.max(), self.specs.min()],
                                  index=['max', 'min'])

        # complete power data
        if 'power' not in self.specs.columns or \
                self.specs.power.isna().any():
            self.specs['power'] = self.specs.voltage * self.specs.current

        # complete efficiency data
        if 'efficiency' not in self.specs.columns or \
                self.specs.efficiency.isna().any():
            # TODO: first condition only used by theoretical model,
            # put it in _curves_coeffs_theoretical or algo asi
            if (self.specs.power == self.specs.power.max()).all():
                # Case with very few data
                hydrau_power = self.specs.flow/60000 * self.specs.tdh * 9810
                rated_data = self.specs[hydrau_power == hydrau_power.max()]
                rated_efficiency = float(hydrau_power.max()/rated_data.power)
                if not 0 < rated_efficiency < 1:
                    raise ValueError('The rated efficiency is found to be '
                                     'out of the range [0, 1].')
                # arbitrary coeff
                coeff = 1
                global_efficiency = coeff * rated_efficiency
                self.specs['efficiency'] = global_efficiency
                warnings.warn('Power and current data will be redetermined'
                              'from efficiency.')
                self.specs.power = hydrau_power / global_efficiency
                self.specs.current = self.specs.power / self.specs.voltage
            else:
                self.specs['efficiency'] = ((self.specs.flow/60000)
                                            * self.specs.tdh * 9.81 * 1000) \
                                            / self.specs.power

        self.data_completeness = specs_completeness(
                self.specs,
                self.motor_electrical_architecture)

        self.modeling_method = modeling_method

    def __repr__(self):
        affich = "name: " + str(self.idname) + \
                 "\nprice: " + str(self.price) + \
                 "\nmodeling method: " + str(self.modeling_method)
        return affich

    @property  # getter
    def modeling_method(self):
        return self._modeling_method

    # setter: allows to recalculate attribute coeffs when changing the method
    @modeling_method.setter
    def modeling_method(self, model):
        if model.lower() == 'kou':
            self.coeffs = _curves_coeffs_Kou98(
                    self.specs, self.data_completeness)
        elif model.lower() == 'arab':
            self.coeffs = _curves_coeffs_Arab06(
                    self.specs, self.data_completeness)
        elif model.lower() == 'hamidat':
            self.coeffs = _curves_coeffs_Hamidat08(
                    self.specs, self.data_completeness)
        elif model.lower() == 'theoretical':
            self.coeffs = _curves_coeffs_theoretical(
                    self.specs, self.data_completeness,
                    self.motor_electrical_architecture)
        else:
            raise NotImplementedError(
                "The requested modeling method is not available. Check your "
                "spelling, or choose between the following: {0}".format(
                        'kou', 'arab', 'hamidat', 'theoretical'))
        self._modeling_method = model

    # TODO: work on following function
    def starting_characteristics(self, tdh, motor_electrical_architecture):
        """
        To Develop:
        In order to start, the pump usually need a higher power input
        than the minimum power input in standard functioning.
        One potential path for adressing this issue is in [1]

        The other path is to consider the controller that goes with the pump.
        Check 'pump_files/PCA_PCC_BLS_Controller_Data_Sheet.pdf! for more
        details.

        References
        ----------
        [1] Singer and Appelbaum,"Starting characteristics of direct
        current motors powered by solar cells", IEEE transactions on
        energy conversion, vol8, 1993

        """
        raise NotImplementedError

    def iv_curve_data(self, head, nbpoint=40):
        """
        Function returning the data needed for plotting the IV curve at
        a given head.

        Parameters
        ----------
        head: float
            Total dynamic head at pump output [m]
        nbpoint: integer, default 40
            Number of data point wanted

        Return
        ------
        dict with following couples keys:values :
            I: list of current [A]
            V: list of voltage [V]
        """

        fctI, intervals = self.functIforVH()

        Vvect = np.linspace(min(intervals['V'](head)),
                            max(intervals['V'](head)),
                            nbpoint)
        Ivect = np.zeros(nbpoint)

        for i, V in enumerate(Vvect):
            Ivect[i] = fctI(V, head)

        return {'I': Ivect, 'V': Vvect}

    def plot_Q_vs_H(self):
        """
        Print the graph of Q(in liter per minute) vs tdh(in m)

        Prints
        -------
        * Graph Q vs H: matplotlib.figure

        """
        # Get the model function
        f2, intervals = self.functQforVH()
        # Loops for computing the data computed with the model
        modeled_data = pd.DataFrame()
        for V in self.voltage_list:
            tdh_max = self.specs[self.specs.voltage == V].tdh.max()
            tdh_vect = np.linspace(0, tdh_max, num=10)  # vector of tdh
            for H in tdh_vect:
                modeled_data = modeled_data.append(
                        {'voltage': V, 'tdh': H, 'flow': f2(V, H)['Q']},
                        ignore_index=True)

        # Plot
        plt.figure(facecolor='White')
        ax1 = plt.subplot(1, 1, 1)  # needed for using the prop_cycler

        for i, V in enumerate(self.voltage_list):
            # get the next color to have the same color by voltage:
            col = next(ax1._get_lines.prop_cycler)['color']
            # plot simulated data
            plot(modeled_data[modeled_data.voltage == V].tdh,
                 modeled_data[modeled_data.voltage == V].flow,
                 linestyle='--',
                 linewidth=1.5,
                 color=col,
                 label=str(V)+'VDC extrapolated')
            # plot measured data
            plot(self.specs[self.specs.voltage == V].tdh,
                 self.specs[self.specs.voltage == V].flow,
                 linestyle='-',
                 linewidth=2,
                 color=col,
                 label=str(V)+'VDC from specs')
        # graph general appearance
        ax1.set_title(str(self.model) +
                      ' Flow rate curves Vs. Head')
        ax1.set_xlabel('lpm')
        ax1.set_ylabel('Head (m)')
        ax1.set_ylim(0, tdh_max*1.1)
        ax1.legend(loc='best')
        ax1.grid(True)

    def functIforVH(self):
        """
        Function computing the IV characteristics of the pump
        depending on head H.

        Returns
        -------
        Tuple containing :

        Function giving I according to voltage V and head H for the pump:
            I = f1(V, H)

        Domains of validity for V and H. Can be functions, so as the
            range of one depends on the other, or fixed ranges.
        """

        if self.modeling_method == 'kou':
            return self.functIforVH_Kou()
        if self.modeling_method == 'arab':
            return self.functIforVH_Arab()
        if self.modeling_method == 'theoretical':
            return self.functIforVH_theoretical()
        if self.modeling_method == 'hamidat':
            raise NotImplementedError(
                "Hamidat method does not provide model for functIforVH.")
        else:
            raise NotImplementedError(
                "The function functIforVH corresponding to the requested "
                "modeling method is not available yet, need to "
                "implemented another valid method.")
        # TODO: Standardize output of functionIforVH with output of QforPH?

    def functIforVH_Arab(self):
        """
        Function using [1] for modeling I vs V of pump.

        Reference
        ---------
        [1] Kou Q, Klein S.A. & Beckman W.A., "A method for estimating the
        long-term performance of direct-coupled PV pumping systems", 1998,
        Solar Energy
        """

        coeffs = self.coeffs['coeffs_f1']

        if self.data_completeness['data_number'] >= 12 \
                and self.data_completeness['voltage_number'] >= 3:
            funct_mod = function_models.compound_polynomial_1_3
        else:
            funct_mod = function_models.compound_polynomial_1_2

        # domain of V and tdh and gathering in one single variable
        dom = _domain_V_H(self.specs, self.data_completeness)
        intervals = {'V': dom[0],
                     'H': dom[1]}

        def functI(V, H, error_raising=True):
            """Function giving voltage V according to current I and tdh H.

            Error_raising parameter allows to check the given values
            according to the possible intervals and to raise errors if not
            corresponding.
            """
            if error_raising is True:
                # check if the head is available for the pump
                v_max = intervals['V'](0)[1]
                if not 0 <= H <= intervals['H'](v_max)[1]:
                    raise errors.HeadError(
                            'H (={0}) is out of bounds for this pump. '
                            'H should be in the interval {1}.'
                            .format(H, intervals['H'](v_max)))
                # check if there is enough current for given head
                if not intervals['V'](H)[0] <= V <= intervals['V'](H)[1]:
                    raise errors.VoltageError(
                            'V (={0}) is out of bounds. For this specific '
                            'head H (={1}), V should be in the interval {2}'
                            .format(V, H, intervals['V'](H)))
            return funct_mod([V, H], *coeffs)

        return functI, intervals

    def functIforVH_Kou(self):
        """
        Function using [1] for modeling I vs V of pump.

        Reference
        ---------
        [1] Kou Q, Klein S.A. & Beckman W.A., "A method for estimating the
        long-term performance of direct-coupled PV pumping systems", 1998,
        Solar Energy
        """

        coeffs = self.coeffs['coeffs_f1']
        funct_mod = function_models.polynomial_multivar_3_3_4

        # domain of V and tdh and gathering in one single variable
        dom = _domain_V_H(self.specs, self.data_completeness)
        intervals = {'V': dom[0],
                     'H': dom[1]}

        def functI(V, H, error_raising=True):
            """Function giving voltage V according to current I and tdh H.

            Error_raising parameter allows to check the given values
            according to the possible intervals and to raise errors if not
            corresponding.
            """
            if error_raising is True:
                # check if the head is available for the pump
                v_max = intervals['V'](0)[1]
                if not 0 <= H <= intervals['H'](v_max)[1]:
                    raise errors.HeadError(
                            'H (={0}) is out of bounds for this pump. '
                            'H should be in the interval {1}.'
                            .format(H, intervals['H'](v_max)))
                # check if there is enough current for given head
                if not intervals['V'](H)[0] <= V <= intervals['V'](H)[1]:
                    raise errors.VoltageError(
                            'V (={0}) is out of bounds. For this specific '
                            'head H (={1}), V should be in the interval {2}'
                            .format(V, H, intervals['V'](H)))
            return funct_mod([V, H], *coeffs)

        return functI, intervals

    def functIforVH_theoretical(self):
        """
        Function using electrical architecture for modeling V vs I of pump.

        Reference
        ---------
        [1]
        """

        coeffs = self.coeffs['coeffs_f1']

        def funct_mod(input_values, R_a, beta_0, beta_1, beta_2):
            """Returns the equation v(i, h).
            """
            i, h = input_values
            funct_mod_beta = function_models.polynomial_2
            beta = funct_mod_beta(h, beta_0, beta_1, beta_2)
            return R_a*i + beta*np.sqrt(i)

        # domain of V and tdh and gathering in one single variable
        dom_VH = _domain_V_H(self.specs, self.data_completeness)
        intervals_VH = {'V': dom_VH[0],
                        'H': dom_VH[1]}

        def functV(I, H, error_raising=True):
            """Function giving current I according to voltage V and tdh H,
            as theoretical model enables
            """
            # No need of error_raising because this function is only used
            # for being inversed numerically after
            if error_raising is True:
                pass
            return funct_mod([I, H], *coeffs)

        def functI(V, H, error_raising=True):
            """Inverse function of functV.
            Note that functV must be strictly monotonic."""
            inv_fun = inverse.inversefunc(functV,
                                          args=(H, False))

            if error_raising is True:
                # check if the head is available for the pump
                v_max = intervals_VH['V'](0)[1]
                if not 0 <= H <= intervals_VH['H'](v_max)[1]:
                    raise errors.HeadError(
                            'H (={0}) is out of bounds for this pump. '
                            'H should be in the interval {1}.'
                            .format(H, intervals_VH['H'](v_max)))
                # check if there is enough current for given head
                if not intervals_VH['V'](H)[0] <= V <= intervals_VH['V'](H)[1]:
                    raise errors.VoltageError(
                            'V (={0}) is out of bounds. For this specific '
                            'head H (={1}), V should be in the interval {2}'
                            .format(V, H, intervals_VH['V'](H)))

            return float(inv_fun(V))  # type casting to standardize with rest

        return functI, intervals_VH

    def functQforVH(self):
        """
        Function redirecting to functQforPH. It first computes P with
        functIforVH(), and then reinject it in functQforPH().
        """

        def functQ(V, H):
            f1, _ = self.functIforVH()
            f2, _ = self.functQforPH()
            try:
                cur = f1(V, H)
            except (errors.VoltageError, errors.HeadError):
                cur = np.nan
            return f2(V*cur, H)

        dom = _domain_V_H(self.specs, self.data_completeness)
        intervals = {'V': dom[0],
                     'H': dom[1]}

        return functQ, intervals

    def functQforPH(self):
        """
        Function computing the output flow rate of the pump.

        Returns
        -------
        * a tuple containing :
            - the function giving Q according to power P and  head H
            for the pump : Q = f2(P, H)
            - the domains of validity for P and H. Can be functions, so as the
            range of one depends on the other, or fixed ranges.
        """

        if self.modeling_method == 'kou':
            return self.functQforPH_Kou()
        if self.modeling_method == 'arab':
            return self.functQforPH_Arab()
        if self.modeling_method == 'hamidat':
            return self.functQforPH_Hamidat()
        if self.modeling_method == 'theoretical':
            return self.functQforPH_theoretical()
        else:
            raise NotImplementedError(
                "The function functQforPH corresponding to the requested "
                "modeling method is not available yet, need to "
                "implemented another valid method.")

    def functQforPH_Hamidat(self):
        """
        Function using [1] for output flow rate modeling.

        Reference
        ---------
        [1] Hamidat A., Benyoucef B., Mathematic models of photovoltaic
        motor-pump systems, 2008, Renewable Energy
        """
        coeffs = self.coeffs['coeffs_f2']

        funct_mod_P = function_models.compound_polynomial_3_3

        def funct_P(Q, power, head):
            """Function supposed to equal 0, used for finding numerically the
            value of flow-rate depending on power.
            """
            return funct_mod_P([Q, head], *coeffs) - power

        dom = _domain_P_H(self.specs, self.data_completeness)
        intervals = {'P': dom[0],
                     'H': dom[1]}

        def functQ(P, H):
            # check if head is in available range (NOT redundant with rest)
            if H > intervals['H'](P)[1]:
                Q = 0
                P_unused = P
            # check if P is insufficient
            if P < intervals['P'](H)[0]:
                Q = 0
                P_unused = P
            # if P is in available range
            elif intervals['P'](H)[0] <= P <= intervals['P'](H)[1]:
                # Newton-Raphson numeraical method:
                # actually fprime should be given for using Newton-Raphson
                Q = opt.newton(funct_P, 5, args=(P, H))
                P_unused = 0  # power unused for pumping
            # if P is more than maximum
            elif intervals['P'](H)[1] < P:
                Pmax = intervals['P'](H)[1]
                Q = opt.newton(funct_P, 5, args=(Pmax, H))
                if Q < 0:  # Case where extrapolation from curve fit is bad
                    Q = 0
                P_unused = P - Pmax
            # if P is NaN or other
            else:
                Q = np.nan
                P_unused = np.nan
            return {'Q': Q, 'P_unused': P_unused}

        return functQ, intervals

    def functQforPH_Arab(self):
        """
        Function using [1] and [2] for output flow rate modeling.

        References
        ---------
        [1] Hadj Arab A., Benghanem M. & Chenlo F.,
        "Motor-pump system modelization", 2006, Renewable Energy
        [2] Djoudi Gherbi, Hadj Arab A., Salhi H., "Improvement and validation
        of PV motor-pump model for PV pumping system performance analysis",
        2017
        """

        coeffs = self.coeffs['coeffs_f2']
        if len(coeffs) == 12:
            funct_mod = function_models.compound_polynomial_2_3
        elif len(coeffs) == 9:
            funct_mod = function_models.compound_polynomial_2_2
        elif len(coeffs) == 8:
            funct_mod = function_models.compound_polynomial_1_3

        # domain of V and tdh and gathering in one single variable
        dom = _domain_P_H(self.specs, self.data_completeness)
        intervals = {'P': dom[0],
                     'H': dom[1]}

        def functQ(P, H):
            # check if head is in available range (NOT redundant with rest)
            if H > intervals['H'](P)[1]:
                Q = 0
                P_unused = P
            # check if P is insufficient
            elif P < intervals['P'](H)[0]:
                Q = 0
                P_unused = P
            # if P is in available range
            elif intervals['P'](H)[0] <= P <= intervals['P'](H)[1]:
                Q = funct_mod([P, H], *coeffs)
                P_unused = 0
                if Q < 0:  # Case where extrapolation from curve fit is bad
                    Q = 0
            # if P is more than maximum
            elif intervals['P'](H)[1] < P:
                Pmax = intervals['P'](H)[1]
                Q = funct_mod([Pmax, H], *coeffs)
                P_unused = P - Pmax
            # if P is NaN or other
            else:
                Q = np.nan
                P_unused = np.nan
            return {'Q': Q, 'P_unused': P_unused}

        return functQ, intervals

    def functQforPH_Kou(self):
        """
        Function using [1] for output flow rate modeling.

        Reference
        ---------
        [1] Kou Q, Klein S.A. & Beckman W.A., "A method for estimating the
        long-term performance of direct-coupled PV pumping systems", 1998,
        Solar Energy
        """

        coeffs = self.coeffs['coeffs_f2']
        funct_mod = function_models.polynomial_multivar_3_3_4

        # domain of V and tdh and gathering in one single variable
        dom = _domain_P_H(self.specs, self.data_completeness)
        intervals = {'P': dom[0],
                     'H': dom[1]}

        def functQ(P, H):
            # check if head is in available range (NOT redundant with rest)
            if H > intervals['H'](P)[1]:
                Q = 0
                P_unused = P
            # check if P is insufficient
            if P < intervals['P'](H)[0]:
                Q = 0
                P_unused = P
            # if P is in available range
            elif intervals['P'](H)[0] <= P <= intervals['P'](H)[1]:
                Q = funct_mod([P, H], *coeffs)
                P_unused = 0
            # if P is more than maximum
            elif intervals['P'](H)[1] < P:
                Pmax = intervals['P'](H)[1]
                Q = funct_mod([P, H], *coeffs)
                if Q < 0:  # Case where extrapolation from curve fit is bad
                    Q = 0
                P_unused = P - Pmax
            # if P is NaN or other
            else:
                Q = np.nan
                P_unused = np.nan
            return {'Q': Q, 'P_unused': P_unused}

        return functQ, intervals

    def functQforPH_theoretical(self):
        """
        Function using theoretical approach for output flow rate modeling.

        Reference
        ---------
        [1]
        """

        if self.data_completeness['data_number'] >= 4 \
                and self.data_completeness['voltage_number'] >= 2:
            def funct_mod(input_values, a, b, c, d):
                P, H = input_values
                return (a + b*H) * (c + d*P)
        else:
            def funct_mod(input_values, mean_efficiency):
                P, H = input_values
                return mean_efficiency * (60000 * P) / (H * 9.81 * 1000)

        coeffs = self.coeffs['coeffs_f2']

        # domain of V and tdh and gathering in one single variable
        dom = _domain_P_H(self.specs, self.data_completeness)
        intervals = {'P': dom[0],
                     'H': dom[1]}

        def functQ(P, H):
            # check if head is in available range (NOT redundant with rest)
            if H > intervals['H'](P)[1]:
                Q = 0
                P_unused = P
            # check if P is insufficient
            if P < intervals['P'](H)[0]:
                Q = 0
                P_unused = P
            # if P is in available range
            elif intervals['P'](H)[0] <= P <= intervals['P'](H)[1]:
                Q = funct_mod([P, H], *coeffs)
                if Q < 0:  # Case where extrapolation from curve fit is bad
                    Q = 0
                P_unused = 0
            # if P is more than maximum
            elif intervals['P'](H)[1] < P:
                Pmax = intervals['P'](H)[1]
                Q = funct_mod([P, H], *coeffs)
                P_unused = P - Pmax
            # if P is NaN or other
            else:
                Q = np.nan
                P_unused = np.nan
            return {'Q': Q, 'P_unused': P_unused}

        return functQ, intervals


def get_data_pump(path):
    """
    Loads the pump data from the .txt file designated by the path.
    This .txt files contains the specifications of the datasheets, and must
    follow the style of the template:
    (~/pvpumpingsystem/data/pump_files/0_template_for_pump_specs.txt)

    Parameters
    ----------
    path: str
        path to the file of the pump data

    Returns
    -------
    Tuple with:

        pandas.DataFrame containing the following columns:
            * voltage: list,
                input voltage given in specifications [V]
            * flow: dict
                output flow rate [liter/minute]
            * tdh: dict
                total dynamic head [m]
            * current: dict
                input current [A]
            * power: dict
                electrical power at input [W]

        dict: metadata (only name for now) of the pump
    """
    # open in read-only option
    csvdata = open(path, 'r')

    metadata = {}
    header = True
    while header is True:
        # get metadata
        line = csvdata.readline()

        # check that it is still header
        if line.startswith('# '):
            header is False
            break

        # remove carriage return and split at ':'.
        # .strip() removes leading or trailing whitespace
        content = re.split(':|#', line.rstrip('\n'))
        metadata[content[0].lower().strip()] = content[1].strip()

    # Import data
    # header=0 because firstline already read before
    data_df = pd.read_csv(csvdata, sep='\t', header=0, comment='#')

    return data_df, metadata


def specs_completeness(specs,
                       motor_electrical_architecture):
    """
    Evaluates the data completeness of a pump.

    Returns
    -------
    dictionary with following keys:
        * voltage_number: float
            number of voltage for which data are given
        * data_number: float
            number of points for which lpm, current, voltage and head are
            given
        * lpm_min: float
            Ratio between min flow_rate given and maximum.
            Should be ideally 0.
        * head_min:float
            Ratio between min head given and maximum.
            Should be ideally 0.
        * elec_archi: boolean
            A valid electrical architecture for the motor is given
    """

    valid_elec_archi = (motor_electrical_architecture in (
            'permanent_magnet', 'series_excited', 'shunt_excited',
            'separately_excited'))

    # nb voltages
    voltages = specs.voltage.drop_duplicates()
    volt_nb = len(voltages)

    # flow data completeness (ideally goes until zero)
    lpm_ratio = []
    for v in voltages:
        lpm_ratio.append(min(specs[specs.voltage == v].flow)
                         / max(specs[specs.voltage == v].flow))
    mean_lpm_ratio = np.mean(lpm_ratio)

    # nb heads
    heads = specs.tdh.drop_duplicates()
    heads_nb = len(heads)

    # head data completeness (minimum tdh should be 0 ideally)
    head_ratio = min(specs.tdh)/max(specs.tdh)

    data_number = 0
    for v in voltages:
        for i in specs[specs.voltage == v].flow:
            data_number += 1

    return {'voltage_number': volt_nb,
            'lpm_min': mean_lpm_ratio,
            'head_min': head_ratio,
            'head_number': heads_nb,
            'elec_archi': valid_elec_archi,
            'data_number': data_number}


# TODO: add way to use it with only very few data point in the case of mppt
def _curves_coeffs_Arab06(specs, data_completeness):
    """
    Compute curve-fitting coefficient with method of Hadj Arab [1] and
    Djoudi Gherbi [2].

    It uses a 3rd order polynomial to model Q(P) and
    a 1st order polynomial to model I(V). Each corresponding
    coefficient depends on TDH through a 3rd order polynomial.

    Parameters
    ----------
    specs: pd.DataFrame
        DataFrame with specs.

    Reference
    ---------
    [1] Hadj Arab A., Benghanem M. & Chenlo F.,
    "Motor-pump system modelization", 2006, Renewable Energy
    [2] Djoudi Gherbi, Hadj Arab A., Salhi H., "Improvement and validation
    of PV motor-pump model for PV pumping system performance analysis", 2017

    """
    # TODO: add check on number of head available (for lin. reg. of coeffs)

    # Original model from [2]
    if data_completeness['data_number'] >= 12 \
            and data_completeness['voltage_number'] >= 3:
        funct_mod_1 = function_models.compound_polynomial_1_3
        funct_mod_2 = function_models.compound_polynomial_2_3
    # Original model from [1]
    elif data_completeness['data_number'] >= 9 \
            and data_completeness['voltage_number'] >= 3:
        funct_mod_1 = function_models.compound_polynomial_1_2
        funct_mod_2 = function_models.compound_polynomial_2_2
    # Other alternative for more restricted pump specifications
    elif data_completeness['data_number'] >= 8 \
            and data_completeness['voltage_number'] >= 2:
        funct_mod_1 = function_models.compound_polynomial_1_2
        funct_mod_2 = function_models.compound_polynomial_1_3
    else:
        raise errors.InsufficientDataError('Lack of information on lpm, '
                                           'current or tdh for pump.')

    # f1: I(V, H)
    dataxy = [np.array(specs.voltage),
              np.array(specs.tdh)]
    dataz = np.array(specs.current)

    param_f1, covmat_f1 = opt.curve_fit(funct_mod_1, dataxy, dataz)
    # computing of statistical figures for f1
    stats_f1 = function_models.correlation_stats(funct_mod_1, param_f1,
                                                 dataxy, dataz)

    # f2: Q(P, H)
    dataxy = [np.array(specs.power),
              np.array(specs.tdh)]
    dataz = np.array(specs.flow)

    param_f2, covmat_f2 = opt.curve_fit(funct_mod_2, dataxy, dataz)
    # computing of statistical figures for f2
    stats_f2 = function_models.correlation_stats(funct_mod_2, param_f2,
                                                 dataxy, dataz)

    return {'coeffs_f1': param_f1,
            'rmse_f1': stats_f1['rmse'],
            'nrmse_f1': stats_f1['nrmse'],
            'r_squared_f1': stats_f1['r_squared'],
            'adjusted_r_squared_f1': stats_f1['adjusted_r_squared'],
            'coeffs_f2': param_f2,
            'rmse_f2': stats_f2['rmse'],
            'nrmse_f2': stats_f2['nrmse'],
            'r_squared_f2': stats_f2['r_squared'],
            'adjusted_r_squared_f2': stats_f2['adjusted_r_squared']}


def _curves_coeffs_Kou98(specs, data_completeness):
    """Compute curve-fitting coefficient with method of Kou [1].

    It uses a 3rd order multivariate polynomial with cross terms to model
    V(I, TDH) and Q(V, TDH) from the data.

    Parameters
    ----------
    specs: pd.DataFrame
        DataFrame with specs.

    Reference
    ---------
    [1] Kou Q, Klein S.A. & Beckman W.A., "A method for estimating the
    long-term performance of direct-coupled PV pumping systems", 1998,
    Solar Energy

    """
# TODO: change the condition data_number to head_number (better)
    if data_completeness['voltage_number'] >= 4 \
            and data_completeness['data_number'] >= 16:
        funct_mod = function_models.polynomial_multivar_3_3_4
    else:
        raise errors.InsufficientDataError('Lack of information on lpm, '
                                           'current or tdh for pump.')

    # f1: I(V, H)
    dataxy = [np.array(specs.voltage),
              np.array(specs.tdh)]
    dataz = np.array(specs.current)

    param_f1, covmat_f1 = opt.curve_fit(funct_mod, dataxy, dataz)
    # computing of statistical figures for f1
    stats_f1 = function_models.correlation_stats(funct_mod, param_f1,
                                                 dataxy, dataz)

    # f2: Q(P, H)
    dataxy = [np.array(specs.power),
              np.array(specs.tdh)]
    dataz = np.array(specs.flow)

    param_f2, covmat_f2 = opt.curve_fit(funct_mod, dataxy, dataz)
    # computing of statistical figures for f2
    stats_f2 = function_models.correlation_stats(funct_mod, param_f2,
                                                 dataxy, dataz)

    return {'coeffs_f1': param_f1,
            'rmse_f1': stats_f1['rmse'],
            'nrmse_f1': stats_f1['nrmse'],
            'r_squared_f1': stats_f1['r_squared'],
            'adjusted_r_squared_f1': stats_f1['adjusted_r_squared'],
            'coeffs_f2': param_f2,
            'rmse_f2': stats_f2['rmse'],
            'nrmse_f2': stats_f2['nrmse'],
            'r_squared_f2': stats_f2['r_squared'],
            'adjusted_r_squared_f2': stats_f2['adjusted_r_squared']}


def _curves_coeffs_Hamidat08(specs, data_completeness):
    """
    Compute curve-fitting coefficient with method of Hamidat [1].
    It uses a 3rd order polynomial to model P(Q) = a + b*Q + c*Q^2 + d*Q^3
    and each corresponding coefficient depends on TDH through a 3rd order
    polynomial as well. This function needs to be reversed numerically
    to be used as Q(P).

    Parameters
    ----------
    specs: pd.DataFrame
        DataFrame with specs.

    Returns
    -------
    * dict with coefficients and statistical outputs

    Reference
    ---------
    [1] Hamidat A., Benyoucef B., Mathematic models of photovoltaic
    motor-pump systems, 2008, Renewable Energy
    """
    if data_completeness['data_number'] >= 16 \
            and data_completeness['head_number'] >= 4:
        funct_mod_2 = function_models.compound_polynomial_3_3
    elif data_completeness['data_number'] >= 12 \
            and data_completeness['head_number'] >= 4:
        funct_mod_2 = function_models.compound_polynomial_2_3
    else:
        raise errors.InsufficientDataError('Lack of information on lpm, '
                                           'current or tdh for pump.')

    # f2: Q(P, H)
    dataxy = [np.array(specs.flow),
              np.array(specs.tdh)]
    dataz = np.array(specs.power)

    param_f2, covmat_f2 = opt.curve_fit(funct_mod_2, dataxy, dataz)
    # computing of statistical figures for f2
    stats_f2 = function_models.correlation_stats(funct_mod_2, param_f2,
                                                 dataxy, dataz)

    return {'coeffs_f2': param_f2,
            'rmse_f2': stats_f2['rmse'],
            'nrmse_f2': stats_f2['nrmse'],
            'r_squared_f2': stats_f2['r_squared'],
            'adjusted_r_squared_f2': stats_f2['adjusted_r_squared']}


# TODO: add way to use it with only one data point in the case of mppt
def _curves_coeffs_theoretical(specs, data_completeness, elec_archi):
    """Compute curve-fitting coefficient following theoretical analysis of
    motor architecture.

    It uses a equation of the form V = R_a*i + beta(H)*np.sqrt(i) to model
    V(I, TDH) and an equation of the form Q = (a + b*H) * (c + d*P) to model
    Q(P, TDH) from the data.

    This kind of equation is used in [1], [2], ...


    Parameters
    ----------
    specs: pd.DataFrame
        DataFrame with specs.

    Reference
    ---------
    [1] Mokkedem & al, ...

    """
    if elec_archi != 'permanent_magnet':
        raise NotImplementedError(
            'This model is not implemented yet for electrical architecture '
            'different from permanent magnet motor.')

#    if not data_completeness['data_number'] >= 2 \
#            and not data_completeness['voltage_number'] >= 2:
#        raise errors.InsufficientDataError('Lack of information on lpm, '
#                                           'current or tdh for pump.')

    # f1: V(I, H) - To change in I(V, H) afterward
    def funct_mod_1(input_values, R_a, beta_0, beta_1, beta_2):
        """Returns the equation v(i, h).
        """
        i, h = input_values
        funct_mod_beta = function_models.polynomial_2
        beta = funct_mod_beta(h, beta_0, beta_1, beta_2)
        return R_a*i + beta*np.sqrt(i)

    dataxy = [np.array(specs.current),
              np.array(specs.tdh)]
    dataz = np.array(specs.voltage)
    param_f1, matcov = opt.curve_fit(funct_mod_1, dataxy, dataz, maxfev=10000)
    # computing of statistical figures for f1
    stats_f1 = function_models.correlation_stats(funct_mod_1, param_f1,
                                                 dataxy, dataz)

    # f2:; Q=f2(P, H)
    if data_completeness['data_number'] >= 4 \
            and data_completeness['voltage_number'] >= 2:
        # TODO: equivalent to developped form with cross term,
        # -> take from function_models
        def funct_mod_2(input_values, a, b, c, d):
            P, H = input_values
            return (a + b*H) * (c + d*P)
            # theoretically it should be the following formula,
            # but doesn't work:
            # return (a + b*H + c*H**2) * P/H

        dataxy = [np.array(specs.power),
                  np.array(specs.tdh)]
        dataz = np.array(specs.flow)

        param_f2, matcov = opt.curve_fit(funct_mod_2, dataxy, dataz,
                                         maxfev=10000)
        # computing of statistical figures for f2
        stats_f2 = function_models.correlation_stats(funct_mod_2, param_f2,
                                                     dataxy, dataz)
    else:
        warnings.warn('Simplistic model of constant efficiency applied.')
        # Simple constant efficiency
        param_f2 = [0.7 * specs.efficiency.max()]

        def funct_Q_for_PH(input_values, efficiency):
            P, H = input_values
            return efficiency * (60000 * P) / (H * 9.81 * 1000)

    #    dataxy_alter = [np.array(specs.power[specs.tdh = 0]),
    #                    np.array(specs.tdh[specs.tdh != 0])]
    #    dataz_alter = np.array(specs.flow[specs.tdh != 0])
        # TODO: remove the extreme parts of the domain as here
        dataxy = [np.array(specs.power[specs.tdh > 7]),
                  np.array(specs.tdh[specs.tdh > 7])]
        dataz = np.array(specs.flow[specs.tdh > 7])

#        # computing of statistical figures for f2
#        stats_f2 = function_models.correlation_stats(funct_Q_for_PH,
#                                                     param_f2,
#                                                     dataxy,
#                                                     dataz)
        # statistical figures for f2 don't make sense in this case:
        stats_f2 = {'rmse': np.nan,
                    'nrmse': np.nan,
                    'r_squared': np.nan,
                    'adjusted_r_squared': np.nan,
                    'nb_data': data_completeness['data_number']}

    # affinity law with constant efficiency - if power data is all the same
    # Use Martiré & al, 2008
#    def funct_P_for_tdh(input_values, a, b, c):
#        H = input_values
#        return a + b * H + c * H**2
#    # get alpha(tdh) for P = alpha(tdh) * Q**3
#    alpha = specs.power / (specs.flow**3)
#    def funct_alpha(H, a, b, c):
#        return (a + b * H + c * H**2)
#    dataH = np.array(specs.tdh[specs.tdh != 0])
#    dataA = np.array(alpha[specs.tdh != 0])
#    param_alpha, matcov = opt.curve_fit(funct_alpha,
#                                        dataH,
#                                        dataA)
#    # apply affinity law
#    def funct_Q_for_PH(P, H):
#        alpha = funct_alpha(H, *param_alpha)
#        return (P/alpha)**(1/3)
    # TO CONTINUE

    return {'coeffs_f1': param_f1,
            'rmse_f1': stats_f1['rmse'],
            'nrmse_f1': stats_f1['nrmse'],
            'r_squared_f1': stats_f1['r_squared'],
            'adjusted_r_squared_f1': stats_f1['adjusted_r_squared'],
            'coeffs_f2': param_f2,
            'rmse_f2': stats_f2['rmse'],
            'nrmse_f2': stats_f2['nrmse'],
            'r_squared_f2': stats_f2['r_squared'],
            'adjusted_r_squared_f2': stats_f2['adjusted_r_squared']}


def _domain_I_H(specs, data_completeness):
    """
    Function giving the domain of cur depending on tdh, and vice versa.

    """

    funct_mod = function_models.polynomial_2

    # domains of I and tdh depending on each other
    data_v = specs.voltage.drop_duplicates()

    cur_tips = []
    tdh_tips = []
    for v in data_v:
        cur_tips.append(min(specs[specs.voltage == v].current))
        tdh_tips.append(max(specs[specs.voltage == v].tdh))

    if data_completeness['voltage_number'] > 2 \
            and data_completeness['lpm_min'] == 0:
        # case working fine for SunPumps - not sure about complete data from
        # other manufacturer
        param_tdh, pcov_tdh = opt.curve_fit(funct_mod,
                                            cur_tips, tdh_tips)
        param_cur, pcov_cur = opt.curve_fit(funct_mod,
                                            tdh_tips, cur_tips)

        def interval_cur(y):
            "Interval on x depending on y"
            return [max(funct_mod(y, *param_cur), min(specs.current)),
                    max(specs.current)]

        def interval_tdh(x):
            "Interval on y depending on x"
            return [0, min(max(funct_mod(x, *param_tdh),
                               0),
                           max(specs.tdh))]

    else:
        # Would need deeper work to fully understand what are the limits
        # on I and V depending on tdh, and how it affects the flow rate
        def interval_cur(*args):
            "Interval on current, independent of tdh"
            return [min(specs.current), max(specs.current)]

        def interval_tdh(*args):
            "Interval on tdh, independent of current"
            return [min(specs.tdh), max(specs.tdh)]

    return interval_cur, interval_tdh


def _domain_V_H(specs, data_completeness):
    """
    Function giving the range of voltage and head in which the pump will
    work.
    """
    funct_mod = function_models.polynomial_2

    data_v = specs.voltage.drop_duplicates()
    tdh_tips = []
    for v in data_v:
        tdh_tips.append(max(specs[specs.voltage == v].tdh))

    if data_completeness['voltage_number'] > 2 \
            and data_completeness['lpm_min'] == 0:
        # case working fine for SunPumps - not sure about complete data from
        # other manufacturer
        param_tdh, pcov_tdh = opt.curve_fit(funct_mod,
                                            data_v, tdh_tips)
        param_v, pcov_v = opt.curve_fit(funct_mod,
                                        tdh_tips, data_v)

        def interval_vol(tdh):
            "Interval on v depending on tdh"
            return [max(funct_mod(tdh, *param_v), min(data_v)),
                    max(data_v)]

        def interval_tdh(v):
            "Interval on tdh depending on v"
            return [0, min(max(funct_mod(v, *param_tdh), 0),
                           max(specs.tdh))]

    else:
        # Would need deeper work to fully understand what are the limits
        # on I and V depending on tdh, and how it affects lpm
        def interval_vol(*args):
            "Interval on vol, independent of tdh"
            return [min(data_v), max(data_v)]

        def interval_tdh(*args):
            "Interval on tdh, independent of vol"
            return [0, max(specs.tdh)]

    return interval_vol, interval_tdh


def _domain_P_H(specs, data_completeness):
    """
    Function giving the range of power and head in which the pump will
    work.
    """
    funct_mod = function_models.polynomial_1

    if data_completeness['voltage_number'] >= 2 \
            and data_completeness['lpm_min'] == 0:
        # case working fine for SunPumps - not sure about complete data from
        # other manufacturer
        df_flow_null = specs[specs.flow == 0]

        datapower_df = df_flow_null['power']
        datatdh_df = df_flow_null['tdh']

        datapower_ar = np.array(datapower_df)
        datatdh_ar = np.array(datatdh_df)

        param_tdh, pcov_tdh = opt.curve_fit(funct_mod,
                                            datapower_ar, datatdh_ar)
        param_pow, pcov_pow = opt.curve_fit(funct_mod,
                                            datatdh_ar, datapower_ar)

        def interval_power(tdh):
            "Interval on power depending on tdh"
            power_max_for_tdh = max(specs[specs.tdh <= tdh].power)
            return [max(funct_mod(tdh, *param_pow), min(datapower_ar)),
                    power_max_for_tdh]

        def interval_tdh(power):
            "Interval on tdh depending on v"
            return [0, min(max(funct_mod(power, *param_tdh), 0),
                           max(datatdh_ar))]

    elif data_completeness['voltage_number'] >= 2:
        tdhmax_df = specs[specs.tdh == max(specs.tdh)]
        power_min_tdhmax = min(tdhmax_df.power)
        tdhmin_df = specs[specs.tdh == min(specs.tdh)]
        power_min_tdhmin = min(tdhmin_df.power)

        datapower_ar = np.array([power_min_tdhmin, power_min_tdhmax])
        datatdh_ar = np.array(
            [float(specs[specs.power == power_min_tdhmin].tdh),
             float(specs[specs.power == power_min_tdhmax].tdh)])
        param_tdh, pcov_tdh = opt.curve_fit(funct_mod,
                                            datapower_ar, datatdh_ar)
        param_pow, pcov_pow = opt.curve_fit(funct_mod,
                                            datatdh_ar, datapower_ar)

        def interval_power(tdh):
            "Interval on power depending on tdh"
            power_max_for_tdh = max(specs[specs.tdh <= tdh].power)
            return [max(funct_mod(tdh, *param_pow), min(datapower_ar)),
                    power_max_for_tdh]

        def interval_tdh(power):
            "Interval on tdh depending on v"
            return [0, min(max(funct_mod(power, *param_tdh), 0),
                           max(datatdh_ar))]

    else:
        # Would need deeper work to fully understand what are the limits
        # on I and V depending on tdh, and how it affects lpm
        # -> relates to function starting characteristics
        datax_ar = np.array(specs.power)
        datay_ar = np.array(specs.tdh)

        def interval_power(*args):
            "Interval on power, independent of tdh"
            return [min(datax_ar), max(datax_ar)]

        def interval_tdh(*args):
            "Interval on tdh, independent of power"
            return [0, max(datay_ar)]

    return interval_power, interval_tdh


if __name__ == "__main__":
    # %% pump creation
    pump1 = Pump(path="data/pump_files/SCS_18_90_60_BL.txt",
                 modeling_method='arab',
                 motor_electrical_architecture='permanent_magnet')

#    pump2 = Pump(lpm={12: [212, 204, 197, 189, 186, 178, 174, 166, 163, 155,
#                           136],
#                      24: [443, 432, 413, 401, 390, 382, 375, 371, 352, 345,
#                           310]},
#                 tdh={12: [6.1, 12.2, 18.3, 24.4, 30.5, 36.6, 42.7, 48.8,
#                           54.9, 61.0, 70.1],
#                      24: [6.1, 12.2, 18.3, 24.4, 30.5, 36.6, 42.7, 48.8,
#                           54.9, 61.0, 70.1]},
#                 current={12: [1.2, 1.5, 1.8, 2.0, 2.1, 2.4, 2.7, 3.0, 3.3,
#                               3.4, 3.9],
#                          24: [1.5, 1.7, 2.1, 2.4, 2.6, 2.8, 3.1, 3.3, 3.6,
#                               3.8, 4.1]
#                          },
#                 idname='Shurflo_9325',
#                 modeling_method='theoretical',
#                 motor_electrical_architecture='permanent_magnet')

#    pump3 = Pump(path="data/pump_files/Shurflo_9325.txt",
#                 idname='Shurflo_9325',
#                 modeling_method='theoretical',
#                 motor_electrical_architecture='permanent_magnet')

#    pump4 = Pump(path="data/pump_files/aquatec_swp_4000.txt",
#                 idname='aquatec_swp_4000',
#                 modeling_method='arab',
#                 motor_electrical_architecture='permanent_magnet')

# Deficient pump data:
#    pump5 = Pump(path="data/pump_files/rosen_SC33-158-D380-9200.txt",
#                 idname='rosen_SC33',
#                 modeling_method='theoretical',
#                 motor_electrical_architecture='permanent_magnet')

#    pump1.plot_Q_vs_H()


# %% plot of functIforVH
#    pump_concerned = pump1
#    f2, intervals = pump_concerned.functIforVH()
#    cur_check = []
#    for index, row in pump_concerned.specs.iterrows():
#        cur_check.append(f2(row.voltage, row.tdh, error_raising=False))
#
#    fig = plt.figure()
#    ax = fig.add_subplot(111, projection='3d',
#                            title='Current as a function of'
#                         ' voltage (V) and static head (m)')
#    ax.scatter(pump_concerned.specs.voltage, pump_concerned.specs.tdh,
#               pump_concerned.specs.current, label='from data')
#    ax.scatter(pump_concerned.specs.voltage, pump_concerned.specs.tdh,
#               cur_check, label='from curve fitting')
#    ax.set_xlabel('voltage')
#    ax.set_ylabel('head')
#    ax.set_zlabel('current I')
#    ax.legend(loc='lower left')
#    plt.show()
#    print('I for VH=(80, 25): {0:.2f}'.format(f2(80, 25)))

# %% plot of functQforPH
    pump_concerned = pump1
    f4, intervals = pump_concerned.functQforPH()
    lpm_check = []

#    if pump_concerned == pump5:
#        pump_concerned.specs = pump_concerned.specs[
#                pump_concerned.specs.tdh > 7]

    for index, row in pump_concerned.specs.iterrows():
        try:
            Q = f4(row.power, row.tdh)
        except (errors.PowerError, errors.HeadError):
            Q = 0
        lpm_check.append(Q['Q'])
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d',
                         title='Flow Q depending on P and H')
    ax.scatter(pump_concerned.specs.power, pump_concerned.specs.tdh,
               pump_concerned.specs.flow,
               label='from data')
    ax.scatter(pump_concerned.specs.power, pump_concerned.specs.tdh,
               lpm_check,
               label='from curve fitting with modeling method {0}'.format(
                       pump_concerned.modeling_method))
    ax.set_xlabel('power')
    ax.set_ylabel('head')
    ax.set_zlabel('discharge Q')
    ax.legend(loc='lower left')
    plt.show()
