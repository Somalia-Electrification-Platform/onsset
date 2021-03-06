from onsset import *
import matplotlib.pylab as plt
import seaborn as sns

def tech_specifications(discount_rate, grid_generation_cost, grid_power_plants_capital_cost, grid_losses,
                        mg_hydro_capital_cost, sa_pv_capital_cost_1, sa_pv_capital_cost_2, sa_pv_capital_cost_3,
                        sa_pv_capital_cost_4, sa_pv_capital_cost_5, sa_pv_life, hv_line_capacity, hv_line_cost,
                        mv_line_cost, mv_line_capacity, lv_line_capacity, lv_line_cost,
                        lv_line_max_length, distribution_losses, distribution_om, hv_mv_transformer_cost,
                        mv_lv_transformer_cost, service_transformer_type, service_transformer_cost,
                        max_nodes_per_serv_transformer, connection_cost_per_household, hydro_life,
                        start_year, end_year):

    # Mini-grid hydro costs
    mg_hydro_calc = Technology(om_of_td_lines=distribution_om,
                               distribution_losses=distribution_losses,
                               connection_cost_per_hh=connection_cost_per_household,
                               base_to_peak_load_ratio=0.85,
                               capacity_factor=0.5,
                               tech_life=hydro_life,
                               capital_cost={float("inf"): mg_hydro_capital_cost},
                               om_costs=0.02,
                               )

    # Stand-alone PV costs
    sa_pv_calc = Technology(base_to_peak_load_ratio=0.9,
                            tech_life=sa_pv_life,
                            om_costs=0.075,
                            capital_cost={float("inf"): sa_pv_capital_cost_5,
                                          1: sa_pv_capital_cost_4,
                                          0.100: sa_pv_capital_cost_3,
                                          0.050: sa_pv_capital_cost_2,
                                          0.020: sa_pv_capital_cost_1},
                            standalone=True
                            )

    mg_pv_hybrid_calc = Technology(om_of_td_lines=distribution_om,
                                   distribution_losses=distribution_losses,
                                   connection_cost_per_hh=connection_cost_per_household,
                                   capacity_factor=0.5,
                                   tech_life=30,
                                   mini_grid=True,
                                   hybrid=True)

    mg_wind_hybrid_calc = Technology(om_of_td_lines=distribution_om,
                                     distribution_losses=distribution_losses,
                                     connection_cost_per_hh=connection_cost_per_household,
                                     capacity_factor=0.5,
                                     tech_life=30,
                                     mini_grid=True,
                                     hybrid=True)

    Technology.set_default_values(base_year=start_year,
                                  start_year=start_year,
                                  end_year=end_year,
                                  discount_rate=discount_rate,
                                  hv_line_type=hv_line_capacity,
                                  hv_line_cost=hv_line_cost,
                                  mv_line_type=mv_line_capacity,
                                  mv_line_amperage_limit=8.0,
                                  mv_line_cost=mv_line_cost,
                                  lv_line_type=lv_line_capacity,
                                  lv_line_cost=lv_line_cost,
                                  lv_line_max_length=lv_line_max_length,
                                  service_transf_type=service_transformer_type,
                                  service_transf_cost=service_transformer_cost,
                                  max_nodes_per_serv_trans=max_nodes_per_serv_transformer,
                                  mv_lv_sub_station_cost=mv_lv_transformer_cost,
                                  mv_mv_sub_station_cost=mv_lv_transformer_cost,
                                  hv_lv_sub_station_cost=hv_mv_transformer_cost,
                                  hv_mv_sub_station_cost=hv_mv_transformer_cost)

    return mg_hydro_calc, sa_pv_calc, mg_pv_hybrid_calc, mg_wind_hybrid_calc

def summary_table(self, yearsofanalysis):
    elements = []
    for year in yearsofanalysis:
        elements.append("Population{}".format(year))
        elements.append("NewConnections{}".format(year))
        elements.append("Capacity{}".format(year))
        elements.append("Investment{}".format(year))

    techs = ["Grid", "SA_PV", "MG_PV_Hybrid", "MG_Wind_Hybrid", "MG_Hydro"]

    sumtechs = []
    for year in yearsofanalysis:
        sumtechs.extend(["Population{}".format(year) + t for t in techs])
        sumtechs.extend(["NewConnections{}".format(year) + t for t in techs])
        sumtechs.extend(["Capacity{}".format(year) + t for t in techs])
        sumtechs.extend(["Investment{}".format(year) + t for t in techs])

    summary = pd.Series(index=sumtechs, name='country')

    for year in yearsofanalysis:
        codes = [1, 3, 8, 9, 7]
        code_index = 0
        for t in techs:
            code = codes[code_index]
            code_index += 1

            summary.loc["Population{}".format(year) + t] = self.loc[(self[SET_MIN_OVERALL_CODE + '{}'.format(year)] == code) & (self[SET_ELEC_FINAL_CODE + '{}'.format(year)] < 99), SET_POP + '{}'.format(year)].sum()
            summary.loc["NewConnections{}".format(year) + t] = self.loc[(self[SET_MIN_OVERALL_CODE + '{}'.format(year)] == code) & (self[SET_ELEC_FINAL_CODE + '{}'.format(year)] < 99), SET_NEW_CONNECTIONS + '{}'.format(year)].sum()
            summary.loc["Capacity{}".format(year) + t] = self.loc[(self[SET_MIN_OVERALL_CODE + '{}'.format(year)] == code) & (self[SET_ELEC_FINAL_CODE + '{}'.format(year)] < 99), SET_NEW_CAPACITY + '{}'.format(year)].sum() / 1000
            summary.loc["Investment{}".format(year) + t] = self.loc[(self[SET_MIN_OVERALL_CODE + '{}'.format(year)] == code) & (self[SET_ELEC_FINAL_CODE + '{}'.format(year)] < 99), SET_INVESTMENT_COST + '{}'.format(year)].sum()
            code += 1

    index = techs + ['Total']
    columns = []
    for year in yearsofanalysis:
        columns.append("Population{}".format(year))
        columns.append("NewConnections{}".format(year))
        columns.append("Capacity{} (MW)".format(year))
        columns.append("Investment{} (million USD)".format(year))

    summary_table = pd.DataFrame(index=index, columns=columns)

    summary_table[columns[0]] = summary.iloc[0:5].astype(int).tolist() + [int(summary.iloc[0:5].sum())]
    summary_table[columns[1]] = summary.iloc[5:10].astype(int).tolist() + [int(summary.iloc[5:10].sum())]
    summary_table[columns[2]] = summary.iloc[10:15].astype(int).tolist() + [int(summary.iloc[10:15].sum())]
    summary_table[columns[3]] = [round(x / 1e4) / 1e2 for x in summary.iloc[15:20].astype(float).tolist()] + [round(summary.iloc[15:20].sum() / 1e4) / 1e2]
    summary_table[columns[4]] = summary.iloc[20:25].astype(int).tolist() + [int(summary.iloc[20:25].sum())]
    summary_table[columns[5]] = summary.iloc[25:30].astype(int).tolist() + [int(summary.iloc[25:30].sum())]
    summary_table[columns[6]] = summary.iloc[30:35].astype(int).tolist() + [int(summary.iloc[30:35].sum())]
    summary_table[columns[7]] = [round(x / 1e4) / 1e2 for x in summary.iloc[35:40].astype(float).tolist()] + [round(summary.iloc[35:40].sum() / 1e4) / 1e2]

    return summary_table

def summary_plots(summary_table, yearsofanalysis):
    colors = ['#73B2FF', '#FFD38C', '#FE5931', '#A56A56', '#00518E']
    techs = ["Grid", "SA_PV", "MG_PV_Hybrid", "MG_Wind_Hybrid", "MG_Hydro"]
    techs_colors = dict(zip(techs, colors))

    columns = []
    for year in yearsofanalysis:
        columns.append("Population{}".format(year))
        columns.append("NewConnections{}".format(year))
        columns.append("Capacity{} (MW)".format(year))
        columns.append("Investment{} (million USD)".format(year))

    summary_plot = summary_table.drop(labels='Total', axis=0)
    fig_size = [15, 15]
    font_size = 10
    plt.rcParams["figure.figsize"] = fig_size
    f, axarr = plt.subplots(2, 2)
    fig_size = [15, 15]
    font_size = 10
    plt.rcParams["figure.figsize"] = fig_size

    sns.barplot(x=summary_plot.index.tolist(), y=columns[4], data=summary_plot, ax=axarr[0, 0], palette=colors)
    axarr[0, 0].set_ylabel(columns[4], fontsize=2 * font_size)
    axarr[0, 0].tick_params(labelsize=font_size)
    sns.barplot(x=summary_plot.index.tolist(), y=columns[5], data=summary_plot, ax=axarr[0, 1], palette=colors)
    axarr[0, 1].set_ylabel(columns[5], fontsize=2 * font_size)
    axarr[0, 1].tick_params(labelsize=font_size)
    sns.barplot(x=summary_plot.index.tolist(), y=columns[6], data=summary_plot, ax=axarr[1, 0], palette=colors)
    axarr[1, 0].set_ylabel(columns[6], fontsize=2 * font_size)
    axarr[1, 0].tick_params(labelsize=font_size)
    sns.barplot(x=summary_plot.index.tolist(), y=columns[7], data=summary_plot, ax=axarr[1, 1], palette=colors)
    axarr[1, 1].set_ylabel(columns[7], fontsize=2 * font_size)
    axarr[1, 1].tick_params(labelsize=font_size)

    return summary_plot
