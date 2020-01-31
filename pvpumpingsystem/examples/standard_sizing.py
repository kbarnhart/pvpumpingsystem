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
from pvpumpingsystem import sizing


# ------------ MAIN INPUTS --------------------------------------------------

# Weather input
#weather_path = (
#    '../data/weather_files/CAN_PQ_Montreal.Intl.AP.716270_CWEC.epw')
#weather_data, weather_metadata = pvlib.iotools.epw.read_epw(
#        weather_path, coerce_year=2005)

# Consumption input
consumption_data = cs.Consumption(constant_flow=1,
                                  length=len(weather_data))

# Pipes set-up
pipes = pn.PipeNetwork(h_stat=20, l_tot=100, diam=0.08,
                       material='plastic', optimism=True)



pvgen1 = pvgen.PVGeneration(
            # Weather data
            path_weather_data=('../data/weather_files/CAN_PQ_Montreal.Intl.'
                               'AP.716270_CWEC.epw'),  # to adapt:

            # PV array parameters
            pv_module_name='kyocera solar KU270 6MCA',
            price_per_module=200,  # in US dollars
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
                                 pipes=pipes,
                                 consumption=consumption_data)


# ------------ ELEMENTS TO SIZE----------------------------------------------

# Pump database:
pump_sunpump = pp.Pump(path="../data/pump_files/SCB_10_150_120_BL.txt",
                       idname='SCB_10')

pump_shurflo = pp.Pump(path="../data/pump_files/Shurflo_9325.txt",
                       idname='Shurflo_9325',
                       motor_electrical_architecture='permanent_magnet')

# TODO: reform pump_database as DataFrame to be consistent with pv_database
pump_database = [pump_sunpump, pump_shurflo]

# PV array database:
# use regex to add more than one provider.
# for example: provider = "Canadian_Solar|Zytech"
provider = "Canadian_Solar"
nb_elt_kept = 5
pv_database = sizing.shrink_pv_database(provider, nb_elt_kept)


# ------------ RUN SIZING ---------------------------------------------------

weather_short = sizing.shrink_weather(weather_data)
selection, total = sizing.sizing_maximize_flow(pv_database,
                                               pump_database,
                                               weather_short,
                                               weather_metadata,
                                               pvps_fixture)

print(selection)
