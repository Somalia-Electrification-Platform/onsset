import folium
from onsset import *


def urban_pop_map(self):
    ## Urban/rural classification
    calib_df = self.loc[self[SET_POP_CALIB] > 500]
    x_ave = self[SET_X_DEG].mean()
    y_ave = self[SET_Y_DEG].mean()
    colors = ['lightgray', 'lightgray', '#73B2FF']
    m = folium.Map(location=[y_ave, x_ave], zoom_start=6)

    for index, row in calib_df.iterrows():
        tech_color = colors[int((row[SET_URBAN]))]

        if row[SET_URBAN] == 2:
            LineThree = "Urban"
        else:
            LineThree = "Rural"

        LineOne = "Buildings: " + str(row['Buildings'])
        LineTwo = "Population: " + str(round(row[SET_POP_CALIB]))
        LineFour = "id: " + str(row['id'])

        LineTot = LineOne + '<br>' + LineTwo + '<br>' + LineThree + '<br>' + LineFour

        iframe = folium.IFrame(LineTot, width=300, height=80)

        popup = folium.Popup(iframe, max_width=150)

        folium.Circle(
            location=[row[SET_Y_DEG], row[SET_X_DEG]],
            radius=np.sqrt(row[SET_GRID_CELL_AREA] / 3.14) * 1000,
            popup=popup,
            color=tech_color,
            fill_color=tech_color,
            fill=True
        ).add_to(m)

    try:
        os.makedirs('maps')
    except FileExistsError:
        pass

    return m

def least_cost_map(self, intermediate_year, end_year, pop_threshold, result_year):
    results_df = self.loc[self[SET_POP_CALIB] > pop_threshold]
    x_ave = self[SET_X_DEG].mean()
    y_ave = self[SET_Y_DEG].mean()

    colors = ['#73B2FF', '#73B2FF', '#FFD38C', '#8FB722', '#8FB722', '#8FB722', '#00518E', '#FE5931', '#A56A56']
    m = folium.Map(location=[y_ave, x_ave], zoom_start=5)

    # Very light gray for unelectrified settlements, the rest get same colors as platform
    for index, row in results_df.iterrows():
        if row["FinalElecCode{}".format(end_year)] == 99:
            tech_color = 'lightgray'
        else:
            tech_color = colors[int((row["FinalElecCode{}".format(end_year)])) - 1]

        technologies_available = {1: 'Grid',
                                  2: 'Expanded mini-grid',
                                  4: 'Mini-grid Diesel',
                                  8: 'Hybrid mini-grid PV',
                                  9: 'Hybrid mini-grid wind',
                                  7: 'Mini-grid hydro',
                                  3: 'Stand-alone PV'}

        # Data to show in popup, numbers have to transformed to strings first
        LineOne = "Technology choice: " + str(technologies_available.get(row["FinalElecCode{}".format(result_year)]))
        LineTwo = "Buildings: " + str(row['Buildings{}'.format(result_year)])
        LineThree = "Investment cost in first timestep: " + str(round(row['InvestmentCost{}'.format(intermediate_year)])) + " USD"
        LineFour = "Investment cost in second timestep: " + str(round(row['InvestmentCost{}'.format(end_year)])) + " USD"
        LineFive = "Total investment cost: " + str(round(row['InvestmentCost{}'.format(end_year)]) + round(row['InvestmentCost{}'.format(intermediate_year)])) + " USD"
        LineSix = "Added capacity in first timestep: " + str(round(row['NewCapacity{}'.format(intermediate_year)])) + " kW"
        LineSeven = "Added capacity in second timestep: " + str(round(row['NewCapacity{}'.format(end_year)])) + " kW"
        LineEight = "Total added capacity: " + str(round(row['NewCapacity{}'.format(end_year)]) + round(row['NewCapacity{}'.format(intermediate_year)])) + " kW"
        LineNine = "ID: " + str(row['id'])

        LineTot = LineOne + '<br>' + LineTwo + '<br>' + LineThree + '<br>' + LineFour + '<br>' + LineFive + '<br>' + LineSix + '<br>' + LineSeven + '<br>' + LineEight + '<br>' + LineNine

        iframe = folium.IFrame(LineTot,
                               width=550,
                               height=150)

        popup = folium.Popup(iframe,
                             max_width=325)

        folium.Circle(
            location=[row[SET_Y_DEG], row[SET_X_DEG]],
            radius=np.sqrt(row[SET_GRID_CELL_AREA] / 3.14) * 1000,
            popup=popup,
            color=tech_color,
            fill_color=tech_color,
            fill=True
        ).add_to(m)

    return m