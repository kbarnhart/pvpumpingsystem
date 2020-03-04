# -*- coding: utf-8 -*-
"""
Example of a sizing with pvpumpingsystem package.

@author: Tanguy Lunel
"""

import pvlib

import pvpumpingsystem.pump as pp
import pvpumpingsystem.pipenetwork as pn
import pvpumpingsystem.consumption as cs
import pvpumpingsystem.pvpumpsystem as pvps
import pvpumpingsystem.pvgeneration as pvgen
import pvpumpingsystem.reservoir as rv
import pvpumpingsystem.mppt as mppt
from pvpumpingsystem import sizing


# ------------ MAIN INPUTS --------------------------------------------------

# Weather input
weather_path = (
    '../data/weather_files/CAN_PQ_Montreal.Intl.AP.716270_CWEC.epw')
weather_data, weather_metadata = pvlib.iotools.epw.read_epw(
        weather_path, coerce_year=2005)
# short weather to compute faster
weather_data = sizing.shrink_weather_worst_month(weather_data)

# Consumption input
consumption_data = cs.Consumption(constant_flow=5)  # in L/min

# Pipes set-up
pipes = pn.PipeNetwork(h_stat=20,  # vertical static head [m]
                       l_tot=100,  # length of pipes [m]
                       diam=0.08,  # diameter of pipes [m]
                       material='plastic',
                       optimism=True)

# Reservoir
reserv1 = rv.Reservoir(size=1000000,
                       water_volume=0,
                       price=1000)

# MPPT
mppt1 = mppt.MPPT(efficiency=0.96,
                  price=1000)

# PV generator parameters
pvgen1 = pvgen.PVGeneration(
            # Weather data
            weather_data_and_metadata={'weather_data': weather_data,
                          'weather_metadata': weather_metadata},  # to adapt:

            # PV array parameters
            pv_module_name='kyocera solar KU270 6MCA',
            price_per_watt=2.5,  # in US dollars
            surface_tilt=45,  # 0 = horizontal, 90 = vertical
            surface_azimuth=180,  # 180 = South, 90 = East
            albedo=0,  # between 0 and 1
            modules_per_string=2,
            strings_in_parallel=1,
            # PV module glazing parameters (not always given in specs)
            glass_params={'K': 4,  # extinction coefficient [1/m]
                          'L': 0.002,  # thickness [m]
                          'n': 1.526},  # refractive index
            racking_model='open_rack',  # or'close_mount' or 'insulated_back'

            # Models used (check pvlib.modelchain for all available models)
            orientation_strategy=None,  # or 'flat' or 'south_at_latitude_tilt'
            clearsky_model='ineichen',
            transposition_model='haydavies',
            solar_position_method='nrel_numpy',
            airmass_model='kastenyoung1989',
            dc_model='desoto',  # 'desoto' or 'cec'.
            ac_model='pvwatts',
            aoi_model='physical',
            spectral_model='first_solar',
            temperature_model='sapm',
            losses_model='pvwatts'
            )


pvps_fixture = pvps.PVPumpSystem(None,
                                 None,
                                 motorpump_model='arab',
                                 coupling='mppt',
                                 mppt=mppt1,
                                 reservoir=reserv1,
                                 pipes=pipes,
                                 consumption=consumption_data)


# ------------ ELEMENTS TO SIZE----------------------------------------------

# Pump database:
pump_sunpump = pp.Pump(path="../data/pump_files/SCB_10_150_120_BL.txt",
                       price=1100,
                       idname='SCB_10')

pump_shurflo = pp.Pump(path="../data/pump_files/Shurflo_9325.txt",
                       idname='Shurflo_9325',
                       price=700,
                       motor_electrical_architecture='permanent_magnet')

pump_database = [pump_sunpump,
                 pump_shurflo]

# PV array database:
pv_database = ['Canadian Solar 200',
               'Canadian solar 400']


# ------------ RUN SIZING ---------------------------------------------------

selection, total = sizing.sizing_minimize_npv(pv_database,
                                              pump_database,
                                              weather_data,
                                              weather_metadata,
                                              pvps_fixture,
                                              llp_accepted=0.05,
                                              M_s_guess=5)

print('configurations for llp of 0.05:\n', selection)
