# -*- coding: utf-8 -*-
"""
Example of a simulation with pvpumpingsystem package.

@author: Tanguy Lunel
"""

import matplotlib.pyplot as plt

import pvpumpingsystem.pump as pp
import pvpumpingsystem.pipenetwork as pn
import pvpumpingsystem.reservoir as rv
import pvpumpingsystem.consumption as cs
import pvpumpingsystem.pvpumpsystem as pvps
import pvpumpingsystem.pvgeneration as pvgen


# ------------ DEFINITION OF FIXTURE -----------------

# For entering new pump data:
# 1) go in: "../data/pump_files/0_template_for_pump_specs.txt"
# 2) write your specs (watch the units!),
# 3) save it under a new name (like "name_of_pump.txt"),
# 4) and close the file.
#
# To use it here then, download it with the path as follows:
pump_sunpump = pp.Pump(path="../data/pump_files/SCB_10_150_120_BL.txt",
                       idname='SCB_10',
                       modeling_method='arab')
pump_shurflo = pp.Pump("../data/pump_files/Shurflo_9325.txt",
                       idname='Shurflo_9325',
                       motor_electrical_architecture='permanent_magnet',
                       modeling_method='arab')  # to adapt:


# ------------ PV MODELING STEPS -----------------------

pvgen1 = pvgen.PVGeneration(
            # Weather data
            weather_data=('../data/weather_files/CAN_PQ_Montreal.Intl.'
                          'AP.716270_CWEC_truncated.epw'),  # to adapt:

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

# Running of the PV generation model
pvgen1.run_model()


# ------------ PVPS MODELING STEPS ------------------------

pipes1 = pn.PipeNetwork(h_stat=10,  # static head [m]
                        l_tot=100,  # length of pipes [m]
                        diam=0.08,  # diameter [m]
                        material='plastic',
                        fittings=None,  # Not available yet
                        optimism=True)

reservoir1 = rv.Reservoir(size=1000000,  # size [L]
                          water_volume=0   # initial water in reservoir [L]
                          )

consumption1 = cs.Consumption(constant_flow=1,  # output flow rate [L/min]
                              length=len(pvgen1.weatherdata))

pvps1 = pvps.PVPumpSystem(pvgen1,
                          pump_shurflo,
                          coupling='mppt',  # to adapt: 'mppt' or 'direct',
                          pipes=pipes1,
                          consumption=consumption1,
                          reservoir=reservoir1)


# ------------ COMPARISON MPPT VS DIRECT COUPLING -----------------

#res1 = pvps.calc_flow_directly_coupled(chain1, pump1, pipes1, atol=0.01,
#                                       stop=8760)
#res2 = pvps.calc_flow_mppt_coupled(chain1, pump1, pipes1, atol=0.01,
#                                   stop=8760)
#compare = pd.DataFrame({'direct1': res1.Qlpm,
#                        'mppt': res2.Qlpm})
#eff1 = pvps1.calc_efficiency()

pvps1.run_model()
print(pvps1.flow[6:16])


# ------------ FIGURES -----------------------

#plt.figure()
#plt.plot(pvps1.efficiency.index, pvps1.efficiency.electric_power)
#plt.title('Electric power in vs time')
#
#plt.figure()
#plt.plot(pvps1.efficiency.index, pvps1.modelchain.effective_irradiance)
#plt.title('Effective irradiance vs time')


# ------------ WATER VOLUME AND FLOW RATE VS TIME ----------



fig, ax1 = plt.subplots()

ax1.set_xlabel('time')
ax1.set_ylabel('Water volume in tank [L]', color='r')
ax1.plot(pvps1.water_stored.index, pvps1.water_stored.volume, color='r',
         linewidth=1)
ax1.tick_params(axis='y', labelcolor='r')

ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis

ax2.set_ylabel('Pump output flow-rate [L/min]', color='b')
ax2.plot(pvps1.efficiency.index, pvps1.flow.Qlpm, color='b',
         linewidth=1)
ax2.tick_params(axis='y', labelcolor='b')

fig.tight_layout()  # otherwise the right y-label is slightly clipped
plt.show()


# ------------ POTENTIAL PATHS TO USE UNUSED ELECTRICITY  ---------------

total_unused_power_Wh = pvps1.flow.P_unused.sum()
total_pumped_water_L = (pvps1.flow.Qlpm).sum()*60

# potabilization of freshwater polluted from pathogen us bacteria can
# be obtained with MF-UF that requires low energy consumption: 1.2 kWh/m3
# or 1.2 Wh/L according to :
# 'Water Purification-Desalination with membrane technology supplied
# with renewable energy', Massimo Pizzichini, Claudio Russo
ratio_potabilized = ((total_unused_power_Wh / 1.2) /
                                 total_pumped_water_L)
# creuser avec ajout de cette machine sur installation:
# https://lacentrale-eco.com/fr/traitement-eau-fr/eau-domestique/traitement-uv-maison/platine-uv/platine-dom-de-traitement-uv-kit-complet-30w-ou-55w-jusqua-2-55-m-h.html

# with 4.2kJ/kg/K, water temperature can be increased of 50K with 58.5 Wh/L
ratio_heated_50K = ((total_unused_power_Wh / 58.5) /
                                   total_pumped_water_L)

print('ratio potabilized: ', ratio_potabilized,
      '\nratio heated +50C:', ratio_heated_50K)
