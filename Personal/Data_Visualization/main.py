from bokeh.plotting import figure, output_file, show, ColumnDataSource
from bokeh.models.tools import HoverTool
from bokeh.transform import factor_cmap
from bokeh.palettes import Blues8
from bokeh.embed import components
import pandas

# Read in csv
df = pandas.read_csv('cars.csv')

# Create ColumnDataSource from data frame
source = ColumnDataSource(df)

output_file('index.html')

# Car list
car_list = source.data['Car'].tolist()

# Add plot
p = figure(
    y_range=car_list,
    width=800,
    height=600,
    title='Cars With Top Horsepower',
    x_axis_label='Horsepower',
    tools="pan,box_select,zoom_in,zoom_out,save,reset"
)


# Loop through each car to create individual legend entries
for i, car in enumerate(car_list):
    car_data = ColumnDataSource(df.loc[df['Car'] == car])
    p.hbar(
        y='Car',
        right='Horsepower',
        left=0,
        height=0.4,
        fill_color=Blues8[i % len(Blues8)],  # Use a gradient color for each bar
        fill_alpha=0.9,
        source=car_data,
        legend_label=car  # Each car gets its own legend entry
    )

# Add Legend
p.legend.orientation = 'vertical'
p.legend.location = 'top_right'
p.legend.label_text_font_size = '10px'

# Add Tooltips (всплывающая подсказка при наведений курсора)
hover = HoverTool()
hover.tooltips = """
  <div>
    <h3>@Car</h3>
    <div><strong>Price: </strong>@Price</div>
    <div><strong>HP: </strong>@Horsepower</div>
    <div><img src="@Image" alt="" width="200" /></div>
  </div>
"""
p.add_tools(hover)


# Show results
show(p)

# Uncomment the following lines if you want to save or print the components
# save(p)
# script, div = components(p)
# print(div)
# print(script)
