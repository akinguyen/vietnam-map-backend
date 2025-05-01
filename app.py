from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import h3
import pandas as pd
import json

app = Flask(__name__)
CORS(app)  # Enable Cross-Origin requests from other origins
CORS(app, resources={r"/filter": {"origins": "*"}})

df = pd.read_csv('reduce-bomb-data.csv')    

location_data = []
with open("combined_grant_final_v2.json", 'r', encoding="utf-8") as file:
    location_data = json.load(file)

def find_city_by_coordinates(lon, lat):
    for item in location_data:
        if item['lon'] == lon and item['lat'] == lat:
            return item['city']
    return None  # Nếu không tìm thấy

def find_country_by_coordinates(lon, lat):
    for item in location_data:
        if item['lon'] == lon and item['lat'] == lat:
            return item['country']
    return None  # Nếu không tìm thấy

# Load data
def get_tooltip(row):
    city = row["city"]

    if city and city != "Ocean":
        city_html = f"<h2>{city}</h2>"
    else:
        city_html = ""
    
    link = ""
    video_element = ""

    if row["city"] == "Huế":
        link = "./video/hue.mp4"
    if row["city"] == "Củ Chi":
        link = "./video/cuchi.mp4"
    if row["city"] == "Cần Giờ":
        link = "./video/cangio.mp4" 
    if row["city"] == "Đà Nẵng":
        link = "./video/danang.mp4"
    if row["city"] == "Quảng Trị":
        link = "./video/quangtri.mp4"
    if row["city"] == "Sài Gòn":
        link = "./video/saigon.mp4"

    if link:
        video_element = f"""
            <video class="video-hide" width="350" autoplay loop muted playsinline>
                <source src="{link}" type="video/mp4">
                Your browser does not support the video tag.
            </video>
        """

    video_html = f"""
    <section class="tooltip-content">
        {city_html}
        <p>
            <strong>Số nhiệm vụ:</strong> {row['mission_count']}
        </p>
        <p>
            <strong>Kinh độ:</strong> {round(row["lon"], 3)}° E
        </p>
        <p>
            <strong>Vĩ độ:</strong> {round(row["lat"], 3) }° N
        </p>
        {video_element}
        </section>
    """
    return video_html


@app.route('/filter', methods=['POST'])
def filter_data():
    data = request.get_json()

    missiontype = data.get('missiontype', ['STRIKE','CLOSE AIR SUPPORT','DIRECT AIR SUPPORT', 'AIR INTERDICTION'])
    missionyear = data.get('missionyear', [1965, 1966])

    df_h3 = df.copy()
    df_h3 = df_h3[df_h3['missionyear'] != 0]
    df_h3 = df_h3[df_h3['missionyear'].isin(missionyear)]
    df_h3 = df_h3[df_h3['missiontype'].isin(missiontype)]
    df_h3 = df_h3[~df_h3['target_country'].isin(['CAMBODIA', 'LAOS', 'THAILAND', 'WESTPAC WATERS', 'PHILLIPINES'])]

    h3_resolution = 6
    result = []

    try:
        df_h3['h3_index'] = df_h3.apply(lambda row: h3.latlng_to_cell(row['target_lat'], row['target_lon'], h3_resolution), axis=1)
        # Aggregate mission count per H3 hex
        hex_counts = df_h3['h3_index'].value_counts().reset_index()
        hex_counts.columns = ['h3_index', 'mission_count']

        hex_counts["lat"] = hex_counts["h3_index"].apply(lambda h: h3.cell_to_latlng(h)[0])
        hex_counts["lon"] = hex_counts["h3_index"].apply(lambda h: h3.cell_to_latlng(h)[1])

        hex_counts['city'] = hex_counts.apply(lambda row: find_city_by_coordinates(row['lon'], row['lat']), axis=1)
        hex_counts['country'] = hex_counts.apply(lambda row: find_country_by_coordinates(row['lon'], row['lat']), axis=1)

        # Generate HTML tooltips with embedded video
        hex_counts["tooltip"] = hex_counts.apply(get_tooltip, axis=1)
        result = jsonify(hex_counts.to_dict(orient='records'))
    except:
        result = []

    return result


@app.route('/get_initial_map_data')
def get_initial_map_data():
    # Your original Python code that calculates hex_counts
    h3_resolution = 6

    df_h3 = df.dropna(subset=['target_lat', 'target_lon'])
    df_h3 = df_h3[df_h3['missionyear'] != 0]
    df_h3 = df_h3[df_h3['missionyear'].between(1965, 1975)]
    df_h3 = df_h3[df_h3['missiontype'].isin(['STRIKE','CLOSE AIR SUPPORT','DIRECT AIR SUPPORT', 'AIR INTERDICTION'])]
    df_h3 = df_h3[~df_h3['target_country'].isin(['CAMBODIA', 'LAOS', 'THAILAND', 'WESTPAC WATERS', 'PHILLIPINES'])]

    # Assuming df_h3 is already populated with your data
    df_h3['h3_index'] = df_h3.apply(lambda row: h3.latlng_to_cell(row['target_lat'], row['target_lon'], h3_resolution), axis=1)
    hex_counts = df_h3['h3_index'].value_counts().reset_index()
    hex_counts.columns = ['h3_index', 'mission_count']
    
    # Add latitude, longitude, and city/country
    hex_counts["lat"] = hex_counts["h3_index"].apply(lambda h: h3.cell_to_latlng(h)[0])
    hex_counts["lon"] = hex_counts["h3_index"].apply(lambda h: h3.cell_to_latlng(h)[1])
    hex_counts['city'] = hex_counts.apply(lambda row: find_city_by_coordinates(row['lon'], row['lat']), axis=1)
    hex_counts['country'] = hex_counts.apply(lambda row: find_country_by_coordinates(row['lon'], row['lat']), axis=1)
    #hex_counts = hex_counts[~hex_counts['country'].isin(["Thailand", "Indonesia", "China", "Myanmar (Burma)"])]

    # Generate tooltips (you can replace this with your own tooltip generation logic)
    hex_counts['tooltip'] = hex_counts.apply(get_tooltip, axis=1)

    # Return the data as JSON to the frontend
    return jsonify(hex_counts.to_dict(orient='records'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4000)  # Ensure it's listening on 0.0.0.0
