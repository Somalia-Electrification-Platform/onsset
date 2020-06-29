import numpy as np
import logging
import pandas as pd

logging.basicConfig(format='%(asctime)s\t\t%(message)s', level=logging.DEBUG)


def pv_diesel_hybrid(
        energy_per_hh,  # kWh/household/year as defined
        ghi,  # highest annual GHI value encountered in the GIS data
        tier,
        start_year,
        end_year,
        pv_no=15,  # number of PV panel sizes simulated
        diesel_no=15,  # number of diesel generators simulated
        discount_rate=0.08,
        diesel_price=0.7
):
    n_chg = 0.92  # charge efficiency of battery
    n_dis = 0.92  # discharge efficiency of battery
    lpsp_max = 0.05  # maximum loss of load allowed over the year, in share of kWh
    battery_cost = 164  # battery capital capital cost, USD/kWh of storage capacity
    pv_cost = 796  # PV panel capital cost, USD/kW peak power
    diesel_cost = 261  # diesel generator capital cost, USD/kW rated power
    pv_life = 20  # PV panel expected lifetime, years
    diesel_life = 15  # diesel generator expected lifetime, years
    pv_om = 0.015  # annual OM cost of PV panels
    diesel_om = 0.1  # annual OM cost of diesel generator
    k_t = 0.005  # temperature factor of PV panels
    inverter_cost = 567
    inverter_life = 10
    inverter_efficiency = 0.92
    charge_controller = 196

    def read_environmental_data():
        ghi = pd.read_csv('Supplementary_files\Benin_data.csv', usecols=[3], skiprows=341882).as_matrix()
        temp = pd.read_csv('Supplementary_files\Benin_data.csv', usecols=[2], skiprows=341882).as_matrix()
        return ghi, temp
    ghi, temp = read_environmental_data()
    hour_numbers = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23) * 365
    dod_max = 0.8  # maximum depth of discharge of battery

    def load_curve(tier, energy_per_hh):
        # the values below define the load curve for the five tiers. The values reflect the share of the daily demand
        # expected in each hour of the day (sum of all values for one tier = 1)
        tier5_load_curve = [0.021008403, 0.021008403, 0.021008403, 0.021008403, 0.027310924, 0.037815126,
                            0.042016807, 0.042016807, 0.042016807, 0.042016807, 0.042016807, 0.042016807,
                            0.042016807, 0.042016807, 0.042016807, 0.042016807, 0.046218487, 0.050420168,
                            0.067226891, 0.084033613, 0.073529412, 0.052521008, 0.033613445, 0.023109244]
        tier4_load_curve = [0.017167382, 0.017167382, 0.017167382, 0.017167382, 0.025751073, 0.038626609,
                            0.042918455, 0.042918455, 0.042918455, 0.042918455, 0.042918455, 0.042918455,
                            0.042918455, 0.042918455, 0.042918455, 0.042918455, 0.0472103, 0.051502146,
                            0.068669528, 0.08583691, 0.075107296, 0.053648069, 0.034334764, 0.021459227]
        tier3_load_curve = [0.013297872, 0.013297872, 0.013297872, 0.013297872, 0.019060284, 0.034574468,
                            0.044326241, 0.044326241, 0.044326241, 0.044326241, 0.044326241, 0.044326241,
                            0.044326241, 0.044326241, 0.044326241, 0.044326241, 0.048758865, 0.053191489,
                            0.070921986, 0.088652482, 0.077570922, 0.055407801, 0.035460993, 0.019946809]
        tier2_load_curve = [0.010224949, 0.010224949, 0.010224949, 0.010224949, 0.019427403, 0.034764826,
                            0.040899796, 0.040899796, 0.040899796, 0.040899796, 0.040899796, 0.040899796,
                            0.040899796, 0.040899796, 0.040899796, 0.040899796, 0.04601227, 0.056237219,
                            0.081799591, 0.102249489, 0.089468303, 0.06390593, 0.038343558, 0.017893661]
        tier1_load_curve = [0, 0, 0, 0, 0.012578616, 0.031446541, 0.037735849, 0.037735849, 0.037735849,
                            0.037735849, 0.037735849, 0.037735849, 0.037735849, 0.037735849, 0.037735849,
                            0.037735849, 0.044025157, 0.062893082, 0.100628931, 0.125786164, 0.110062893,
                            0.078616352, 0.044025157, 0.012578616]

        if tier == 1:
            load_curve = tier1_load_curve * 365
        elif tier == 2:
            load_curve = tier2_load_curve * 365
        elif tier == 3:
            load_curve = tier3_load_curve * 365
        elif tier == 4:
            load_curve = tier4_load_curve * 365
        else:
            load_curve = tier5_load_curve * 365

        return np.array(load_curve) * energy_per_hh / 365

    load_curve = load_curve(tier, energy_per_hh)

    def pv_diesel_capacities(pv_capacity, battery_size, diesel_capacity, pv_no, diesel_no, battery_no):
        dod = np.zeros(shape=(24, battery_no, pv_no, diesel_no))
        battery_use = np.zeros(shape=(24, battery_no, pv_no, diesel_no))  # Stores the amount of battery discharge during the day
        fuel_result = np.zeros(shape=(battery_no, pv_no, diesel_no))
        battery_life = np.zeros(shape=(battery_no, pv_no, diesel_no))
        soc = np.ones(shape=(battery_no, pv_no, diesel_no)) * 0.5
        unmet_demand = np.zeros(shape=(battery_no, pv_no, diesel_no))
        annual_diesel_gen = np.zeros(shape=(battery_no, pv_no, diesel_no))
        dod_max = np.ones(shape=(battery_no, pv_no, diesel_no)) * 0.6

        for i in range(8760):

            # Battery self-discharge (0.02% per hour)
            battery_use[hour_numbers[i], :, :] = 0.0002 * soc
            soc *= 0.9998

            # Calculation of PV gen and net load
            t_cell = temp[i] + 0.0256 * ghi[i]  # PV cell temperature
            pv_gen = pv_capacity * 0.9 * ghi[i] / 1000 * (1 - k_t * (t_cell - 25))  # PV generation in the hour
            net_load = load_curve[hour_numbers[i]] - pv_gen  # remaining load not met by PV panels

            # Dispatchable energy from battery available to meet load
            battery_dispatchable = soc * battery_size * n_dis
            # Energy required to fully charge battery
            battery_chargeable = (1 - soc) * battery_size / n_chg

            # Below is the dispatch strategy for the diesel generator as described in word document

            if 4 < hour_numbers[i] <= 17:
                # During the morning and day, the batteries are dispatched primarily.
                # The diesel generator, if needed, is run at the lowest possible capacity

                # Minimum diesel capacity to cover the net load after batteries.
                # Diesel genrator limited by lowest possible capacity (40%) and rated capacity
                min_diesel = np.minimum(
                    np.maximum(net_load - battery_dispatchable, 0.4 * diesel_capacity),
                    diesel_capacity)

                diesel_gen = np.where(net_load > battery_dispatchable, min_diesel, 0)

            elif 17 > hour_numbers[i] > 23:
                # During the evening, the diesel generator is dispatched primarily, at max_diesel.
                # Batteries are dispatched if diesel generation is insufficient.

                #  Maximum amount of diesel needed to supply load and charge battery
                # Diesel genrator limited by lowest possible capacity (40%) and rated capacity
                max_diesel = np.maximum(
                    np.minimum(net_load + battery_chargeable, diesel_capacity),
                    0.4 * diesel_capacity)

                diesel_gen = np.where(net_load > 0, max_diesel, 0)
            else:
                # During night, batteries are dispatched primarily.
                # The diesel generator is used at max_diesel if load is larger than battery capacity

                #  Maximum amount of diesel needed to supply load and charge battery
                # Diesel genrator limited by lowest possible capacity (40%) and rated capacity
                max_diesel = np.maximum(
                    np.minimum(net_load + battery_chargeable, diesel_capacity),
                    0.4 * diesel_capacity)

                diesel_gen = np.where(net_load > battery_dispatchable, max_diesel, 0)

            fuel_result += np.where(diesel_gen > 0, diesel_capacity * 0.08145 + diesel_gen * 0.246, 0)
            annual_diesel_gen += diesel_gen

            # Reamining load after diesel generator
            net_load = net_load - diesel_gen

            # If diesel generation is larger than load, battery is charged
            # If diesel generation is smaller than load, battery is discharged
            soc -= np.where(net_load > 0,
                            net_load / n_dis / battery_size,
                            net_load * n_chg / battery_size)

            # The amount of battery discharge in the hour is stored (measured in State Of Charge)
            battery_use[hour_numbers[i], :, :] = \
                np.minimum(np.where(net_load > 0,
                                    net_load / n_dis / battery_size,
                                    0),
                           soc)

            # If State of charge is negative, that means there's demand that could not be met.
            unmet_demand += np.where(soc < 0,
                                     -soc / n_dis * battery_size,
                                     0)
            soc = np.maximum(soc, 0)

            # If State of Charge is larger than 1, that means there was excess PV/diesel generation
            soc = np.minimum(soc, 1)

            dod[hour_numbers[i], :, :] = 1 - soc  # The depth of discharge in every hour of the day is stored
            if hour_numbers[i] == 23:  # The battery wear during the last day is calculated
                battery_used = np.where(dod.max(axis=0) > 0, 1, 0)
                battery_life += battery_use.sum(axis=0) / (
                        531.52764 * np.maximum(0.1, dod.max(axis=0) * dod_max) ** -1.12297) * battery_used

        condition = unmet_demand / energy_per_hh  # LPSP is calculated
        battery_life = np.round(1 / battery_life)
        diesel_share = annual_diesel_gen / energy_per_hh

        return diesel_share, battery_life, condition, fuel_result

    # This section creates the range of PV capacities, diesel capacities and battery sizes to be simulated
    ref = 5 * load_curve[19]

    battery_sizes = [0.5 * energy_per_hh / 365, energy_per_hh / 365, 2 * energy_per_hh / 365]
    pv_caps = []
    diesel_caps = []
    diesel_extend = np.ones(pv_no)
    pv_extend = np.ones(diesel_no)

    for i in range(pv_no):
        pv_caps.append(ref * (pv_no - i) / pv_no)

    for j in range(diesel_no):
        diesel_caps.append(j * max(load_curve) / diesel_no)

    pv_caps = np.outer(np.array(pv_caps), pv_extend)
    diesel_caps = np.outer(diesel_extend, np.array(diesel_caps))

    # This section creates 2d-arrays to store information on V capacities, diesel capacities, battery sizes,
    # fuel usage, battery life and LPSP

    battery_size = np.ones((len(battery_sizes), pv_no, diesel_no))
    pv_panel_size = np.zeros((len(battery_sizes), pv_no, diesel_no))
    diesel_capacity = np.zeros((len(battery_sizes), pv_no, diesel_no))

    for j in range(len(battery_sizes)):
        battery_size[j, :, :] *= battery_sizes[j]
        pv_panel_size[j, :, :] = pv_caps
        diesel_capacity[j, :, :] = diesel_caps

    # For the number of diesel, pv and battery capacities the lpsp, battery lifetime, fuel usage and LPSP is calculated
    diesel_share, battery_life, lpsp, fuel_usage = \
        pv_diesel_capacities(pv_panel_size, battery_size, diesel_capacity, pv_no, diesel_no, len(battery_sizes))
    battery_life = np.minimum(20, battery_life)

    def calculate_hybrid_lcoe():
        # Necessary information for calculation of LCOE is defined
        project_life = end_year - start_year
        generation = np.ones(project_life) * energy_per_hh
        generation[0] = 0

        # Calculate LCOE
        sum_costs = np.zeros((len(battery_sizes), pv_no, diesel_no))
        sum_el_gen = np.zeros((len(battery_sizes), pv_no, diesel_no))
        investment = np.zeros((len(battery_sizes), pv_no, diesel_no))

        for year in range(project_life + 1):
            salvage = np.zeros((len(battery_sizes), pv_no, diesel_no))

            fuel_costs = fuel_usage * diesel_price
            om_costs = (pv_panel_size * pv_cost * pv_om + diesel_capacity * diesel_cost * diesel_om)

            inverter_investment = np.where(year % inverter_life == 0, max(load_curve) * inverter_cost, 0)
            diesel_investment = np.where(year % diesel_life == 0, diesel_capacity * diesel_cost, 0)
            pv_investment = np.where(year % pv_life == 0, pv_panel_size * pv_cost, 0)
            battery_investment = np.where(year % battery_life == 0, battery_size * battery_cost / dod_max, 0)  # TODO Include dod_max here?

            if year == project_life:
                salvage = (1 - (project_life % battery_life) / battery_life) * battery_cost * battery_size / dod_max + \
                          (1 - (project_life % diesel_life) / diesel_life) * diesel_capacity * diesel_cost + \
                          (1 - (project_life % pv_life) / pv_life) * pv_panel_size * pv_cost + \
                          (1 - (project_life % inverter_life) / inverter_life) * max(load_curve) * inverter_cost

            investment += diesel_investment + pv_investment + battery_investment + inverter_investment - salvage

            sum_costs += (fuel_costs + om_costs + battery_investment + diesel_investment + pv_investment - salvage) / ((1 + discount_rate) ** year)

            if year > 0:
                sum_el_gen += energy_per_hh / ((1 + discount_rate) ** year)

        return sum_costs / sum_el_gen, investment

    diesel_limit = 0.25
    lcoe, investment = calculate_hybrid_lcoe()
    lcoe = np.where(lpsp > lpsp_max, 99, lcoe)
    lcoe = np.where(diesel_share > diesel_limit, 99, lcoe)

    min_lcoe = np.min(lcoe)
    min_lcoe_combination = np.unravel_index(np.argmin(lcoe, axis=None), lcoe.shape)
    ren_share = 1 - diesel_share[min_lcoe_combination]
    capacity = pv_panel_size[min_lcoe_combination] + diesel_capacity[min_lcoe_combination]
    ren_capacity = pv_panel_size[min_lcoe_combination] / capacity

    return min_lcoe, investment[min_lcoe_combination], capacity, ren_share, ren_capacity

for i in range(10):
    logging.info('First')
    a1, b1, c1, d1, e1 = pv_diesel_hybrid(100, 2200, 3, 2020, 2030, pv_no=15, diesel_no=15)
    1+1

