"""
Predefined regions for Yieldera Automated Visualization
"""

ZIMBABWE_PROVINCES = [
  {
    "id": "zw-harare",
    "name": "Harare Metropolitan",
    "category": "province",
    "geometry": {
      "type": "Polygon",
      "coordinates": [[
        [30.9, -17.6], [31.3, -17.6], [31.3, -18.0], [30.9, -18.0], [30.9, -17.6]
      ]]
    }
  },
  {
    "id": "zw-bulawayo",
    "name": "Bulawayo Metropolitan", 
    "category": "province",
    "geometry": {
      "type": "Polygon",
      "coordinates": [[
        [28.4, -20.0], [28.8, -20.0], [28.8, -20.3], [28.4, -20.3], [28.4, -20.0]
      ]]
    }
  },
  {
    "id": "zw-mashonaland-west",
    "name": "Mashonaland West",
    "category": "province",
    "geometry": {
      "type": "Polygon", 
      "coordinates": [[
        [29.5, -16.5], [31.0, -16.5], [31.0, -18.5], [29.5, -18.5], [29.5, -16.5]
      ]]
    }
  },
  {
    "id": "zw-mashonaland-central",
    "name": "Mashonaland Central",
    "category": "province",
    "geometry": {
      "type": "Polygon",
      "coordinates": [[
        [30.0, -15.5], [33.0, -15.5], [33.0, -17.5], [30.0, -17.5], [30.0, -15.5]
      ]]
    }
  },
  {
    "id": "zw-mashonaland-east",
    "name": "Mashonaland East", 
    "category": "province",
    "geometry": {
      "type": "Polygon",
      "coordinates": [[
        [31.0, -16.5], [33.0, -16.5], [33.0, -19.0], [31.0, -19.0], [31.0, -16.5]
      ]]
    }
  },
  {
    "id": "zw-manicaland",
    "name": "Manicaland",
    "category": "province",
    "geometry": {
      "type": "Polygon",
      "coordinates": [[
        [31.5, -17.5], [33.1, -17.5], [33.1, -20.2], [31.5, -20.2], [31.5, -17.5]
      ]]
    }
  },
  {
    "id": "zw-midlands",
    "name": "Midlands",
    "category": "province",
    "geometry": {
      "type": "Polygon", 
      "coordinates": [[
        [28.0, -18.5], [31.5, -18.5], [31.5, -20.5], [28.0, -20.5], [28.0, -18.5]
      ]]
    }
  },
  {
    "id": "zw-masvingo",
    "name": "Masvingo",
    "category": "province",
    "geometry": {
      "type": "Polygon",
      "coordinates": [[
        [29.5, -19.5], [32.5, -19.5], [32.5, -22.4], [29.5, -22.4], [29.5, -19.5]
      ]]
    }
  },
  {
    "id": "zw-matabeleland-south",
    "name": "Matabeleland South",
    "category": "province",
    "geometry": {
      "type": "Polygon", 
      "coordinates": [[
        [25.2, -19.5], [29.5, -19.5], [29.5, -22.4], [25.2, -22.4], [25.2, -19.5]
      ]]
    }
  },
  {
    "id": "zw-matabeleland-north",
    "name": "Matabeleland North",
    "category": "province",
    "geometry": {
      "type": "Polygon",
      "coordinates": [[
        [25.2, -16.0], [29.0, -16.0], [29.0, -19.5], [25.2, -19.5], [25.2, -16.0]
      ]]
    }
  }
]

ZIMBABWE_DISTRICTS = [
  # Mashonaland Central Districts
  { "id": "zw-bindura", "name": "Bindura", "province": "Mashonaland Central", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[31.2, -16.8], [31.6, -16.8], [31.6, -17.2], [31.2, -17.2], [31.2, -16.8]]] }},
  { "id": "zw-centenary", "name": "Centenary", "province": "Mashonaland Central", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[30.8, -15.8], [31.4, -15.8], [31.4, -16.4], [30.8, -16.4], [30.8, -15.8]]] }},
  { "id": "zw-shamva", "name": "Shamva", "province": "Mashonaland Central", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[31.4, -16.8], [31.8, -16.8], [31.8, -17.4], [31.4, -17.4], [31.4, -16.8]]] }},
  { "id": "zw-mount-darwin", "name": "Mount Darwin", "province": "Mashonaland Central", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[31.0, -16.0], [31.6, -16.0], [31.6, -16.8], [31.0, -16.8], [31.0, -16.0]]] }},
  { "id": "zw-rushinga", "name": "Rushinga", "province": "Mashonaland Central", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[31.8, -16.2], [32.4, -16.2], [32.4, -17.0], [31.8, -17.0], [31.8, -16.2]]] }},
  { "id": "zw-muzarabani", "name": "Muzarabani", "province": "Mashonaland Central", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[30.4, -15.8], [31.0, -15.8], [31.0, -16.6], [30.4, -16.6], [30.4, -15.8]]] }},
  { "id": "zw-guruve", "name": "Guruve", "province": "Mashonaland Central", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[30.6, -16.4], [31.2, -16.4], [31.2, -17.2], [30.6, -17.2], [30.6, -16.4]]] }},

  # Mashonaland East Districts  
  { "id": "zw-mutoko", "name": "Mutoko", "province": "Mashonaland East", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[31.8, -17.2], [32.4, -17.2], [32.4, -18.0], [31.8, -18.0], [31.8, -17.2]]] }},
  { "id": "zw-mudzi", "name": "Mudzi", "province": "Mashonaland East", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[31.6, -16.8], [32.2, -16.8], [32.2, -17.6], [31.6, -17.6], [31.6, -16.8]]] }},
  { "id": "zw-chikomba", "name": "Chikomba", "province": "Mashonaland East", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[31.0, -18.0], [31.8, -18.0], [31.8, -18.8], [31.0, -18.8], [31.0, -18.0]]] }},
  { "id": "zw-marondera", "name": "Marondera", "province": "Mashonaland East", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[31.4, -18.0], [32.0, -18.0], [32.0, -18.6], [31.4, -18.6], [31.4, -18.0]]] }},
  { "id": "zw-goromonzi", "name": "Goromonzi", "province": "Mashonaland East", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[31.0, -17.6], [31.6, -17.6], [31.6, -18.4], [31.0, -18.4], [31.0, -17.6]]] }},
  { "id": "zw-seke", "name": "Seke", "province": "Mashonaland East", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[31.0, -18.0], [31.4, -18.0], [31.4, -18.4], [31.0, -18.4], [31.0, -18.0]]] }},
  { "id": "zw-ump", "name": "UMP", "province": "Mashonaland East", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[31.6, -18.2], [32.2, -18.2], [32.2, -19.0], [31.6, -19.0], [31.6, -18.2]]] }},

  # Mashonaland West Districts
  { "id": "zw-kadoma", "name": "Kadoma", "province": "Mashonaland West", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[29.6, -18.2], [30.2, -18.2], [30.2, -18.8], [29.6, -18.8], [29.6, -18.2]]] }},
  { "id": "zw-chinhoyi", "name": "Chinhoyi", "province": "Mashonaland West", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[30.0, -17.0], [30.6, -17.0], [30.6, -17.8], [30.0, -17.8], [30.0, -17.0]]] }},
  { "id": "zw-kariba", "name": "Kariba", "province": "Mashonaland West", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[28.6, -16.4], [29.4, -16.4], [29.4, -17.2], [28.6, -17.2], [28.6, -16.4]]] }},
  { "id": "zw-hurungwe", "name": "Hurungwe", "province": "Mashonaland West", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[29.0, -16.8], [30.0, -16.8], [30.0, -17.8], [29.0, -17.8], [29.0, -16.8]]] }},
  { "id": "zw-makonde", "name": "Makonde", "province": "Mashonaland West", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[30.0, -16.8], [30.8, -16.8], [30.8, -17.6], [30.0, -17.6], [30.0, -16.8]]] }},
  { "id": "zw-zvimba", "name": "Zvimba", "province": "Mashonaland West", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[30.2, -17.4], [30.8, -17.4], [30.8, -18.2], [30.2, -18.2], [30.2, -17.4]]] }},
  { "id": "zw-chegutu", "name": "Chegutu", "province": "Mashonaland West", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[30.0, -18.0], [30.6, -18.0], [30.6, -18.6], [30.0, -18.6], [30.0, -18.0]]] }},

  # Manicaland Districts
  { "id": "zw-mutare", "name": "Mutare", "province": "Manicaland", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[32.4, -18.8], [33.0, -18.8], [33.0, -19.4], [32.4, -19.4], [32.4, -18.8]]] }},
  { "id": "zw-nyanga", "name": "Nyanga", "province": "Manicaland", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[32.6, -18.0], [33.1, -18.0], [33.1, -18.6], [32.6, -18.6], [32.6, -18.0]]] }},
  { "id": "zw-makoni", "name": "Makoni", "province": "Manicaland", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[32.0, -18.4], [32.6, -18.4], [32.6, -19.2], [32.0, -19.2], [32.0, -18.4]]] }},
  { "id": "zw-buhera", "name": "Buhera", "province": "Manicaland", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[31.6, -19.0], [32.4, -19.0], [32.4, -19.8], [31.6, -19.8], [31.6, -19.0]]] }},
  { "id": "zw-chipinge", "name": "Chipinge", "province": "Manicaland", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[32.4, -19.6], [33.0, -19.6], [33.0, -20.4], [32.4, -20.4], [32.4, -19.6]]] }},
  { "id": "zw-chimanimani", "name": "Chimanimani", "province": "Manicaland", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[32.8, -19.6], [33.1, -19.6], [33.1, -20.2], [32.8, -20.2], [32.8, -19.6]]] }},
  { "id": "zw-rusape", "name": "Rusape", "province": "Manicaland", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[32.0, -18.8], [32.6, -18.8], [32.6, -19.4], [32.0, -19.4], [32.0, -18.8]]] }},

  # Midlands Districts
  { "id": "zw-gweru", "name": "Gweru", "province": "Midlands", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[29.6, -19.2], [30.2, -19.2], [30.2, -19.8], [29.6, -19.8], [29.6, -19.2]]] }},
  { "id": "zw-kwekwe", "name": "Kwekwe", "province": "Midlands", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[29.6, -18.8], [30.2, -18.8], [30.2, -19.4], [29.6, -19.4], [29.6, -18.8]]] }},
  { "id": "zw-gokwe-north", "name": "Gokwe North", "province": "Midlands", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[28.4, -18.4], [29.2, -18.4], [29.2, -19.2], [28.4, -19.2], [28.4, -18.4]]] }},
  { "id": "zw-gokwe-south", "name": "Gokwe South", "province": "Midlands", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[28.6, -19.0], [29.4, -19.0], [29.4, -19.8], [28.6, -19.8], [28.6, -19.0]]] }},
  { "id": "zw-shurugwi", "name": "Shurugwi", "province": "Midlands", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[30.0, -19.4], [30.6, -19.4], [30.6, -20.2], [30.0, -20.2], [30.0, -19.4]]] }},
  { "id": "zw-chirumhanzu", "name": "Chirumhanzu", "province": "Midlands", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[30.2, -19.6], [30.8, -19.6], [30.8, -20.4], [30.2, -20.4], [30.2, -19.6]]] }},

  # Masvingo Districts
  { "id": "zw-masvingo-urban", "name": "Masvingo Urban", "province": "Masvingo", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[30.6, -20.0], [31.2, -20.0], [31.2, -20.6], [30.6, -20.6], [30.6, -20.0]]] }},
  { "id": "zw-chiredzi", "name": "Chiredzi", "province": "Masvingo", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[31.0, -21.0], [32.0, -21.0], [32.0, -22.0], [31.0, -22.0], [31.0, -21.0]]] }},
  { "id": "zw-bikita", "name": "Bikita", "province": "Masvingo", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[31.4, -20.0], [32.0, -20.0], [32.0, -20.8], [31.4, -20.8], [31.4, -20.0]]] }},
  { "id": "zw-zaka", "name": "Zaka", "province": "Masvingo", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[31.2, -20.4], [31.8, -20.4], [31.8, -21.2], [31.2, -21.2], [31.2, -20.4]]] }},
  { "id": "zw-gutu", "name": "Gutu", "province": "Masvingo", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[30.8, -19.8], [31.4, -19.8], [31.4, -20.6], [30.8, -20.6], [30.8, -19.8]]] }},
  { "id": "zw-chivi", "name": "Chivi", "province": "Masvingo", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[30.0, -20.4], [30.8, -20.4], [30.8, -21.4], [30.0, -21.4], [30.0, -20.4]]] }},
  { "id": "zw-mwenezi", "name": "Mwenezi", "province": "Masvingo", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[29.4, -21.0], [30.6, -21.0], [30.6, -22.2], [29.4, -22.2], [29.4, -21.0]]] }},

  # Matabeleland North Districts
  { "id": "zw-hwange", "name": "Hwange", "province": "Matabeleland North", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[25.8, -18.0], [27.0, -18.0], [27.0, -19.2], [25.8, -19.2], [25.8, -18.0]]] }},
  { "id": "zw-binga", "name": "Binga", "province": "Matabeleland North", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[27.0, -16.8], [28.0, -16.8], [28.0, -18.0], [27.0, -18.0], [27.0, -16.8]]] }},
  { "id": "zw-lupane", "name": "Lupane", "province": "Matabeleland North", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[27.6, -18.2], [28.6, -18.2], [28.6, -19.2], [27.6, -19.2], [27.6, -18.2]]] }},
  { "id": "zw-nkayi", "name": "Nkayi", "province": "Matabeleland North", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[28.4, -18.6], [29.2, -18.6], [29.2, -19.4], [28.4, -19.4], [28.4, -18.6]]] }},
  { "id": "zw-tsholotsho", "name": "Tsholotsho", "province": "Matabeleland North", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[27.4, -19.0], [28.4, -19.0], [28.4, -19.8], [27.4, -19.8], [27.4, -19.0]]] }},

  # Matabeleland South Districts
  { "id": "zw-gwanda", "name": "Gwanda", "province": "Matabeleland South", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[29.0, -20.6], [29.8, -20.6], [29.8, -21.4], [29.0, -21.4], [29.0, -20.6]]] }},
  { "id": "zw-beitbridge", "name": "Beitbridge", "province": "Matabeleland South", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[29.6, -21.8], [30.4, -21.8], [30.4, -22.4], [29.6, -22.4], [29.6, -21.8]]] }},
  { "id": "zw-matobo", "name": "Matobo", "province": "Matabeleland South", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[28.2, -20.2], [29.0, -20.2], [29.0, -21.0], [28.2, -21.0], [28.2, -20.2]]] }},
  { "id": "zw-mangwe", "name": "Mangwe", "province": "Matabeleland South", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[27.8, -20.6], [28.6, -20.6], [28.6, -21.4], [27.8, -21.4], [27.8, -20.6]]] }},
  { "id": "zw-bulilima", "name": "Bulilima", "province": "Matabeleland South", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[26.4, -20.8], [27.4, -20.8], [27.4, -21.8], [26.4, -21.8], [26.4, -20.8]]] }},
  { "id": "zw-insiza", "name": "Insiza", "province": "Matabeleland South", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[28.8, -20.0], [29.6, -20.0], [29.6, -20.8], [28.8, -20.8], [28.8, -20.0]]] }},
  { "id": "zw-umzingwane", "name": "Umzingwane", "province": "Matabeleland South", "category": "district", "geometry": { "type": "Polygon", "coordinates": [[[28.6, -20.4], [29.4, -20.4], [29.4, -21.2], [28.6, -21.2], [28.6, -20.4]]] }}
]

SOUTHERN_AFRICA_COUNTRIES = [
  {
    "id": "sa-south-africa",
    "name": "South Africa",
    "category": "country",
    "geometry": {
      "type": "Polygon", 
      "coordinates": [[
        [16.4, -22.1], [32.9, -22.1], [32.9, -34.8], [16.4, -34.8], [16.4, -22.1]
      ]]
    }
  },
  {
    "id": "sa-botswana",
    "name": "Botswana",
    "category": "country",
    "geometry": {
      "type": "Polygon",
      "coordinates": [[
        [19.9, -17.8], [29.4, -17.8], [29.4, -26.9], [19.9, -26.9], [19.9, -17.8]
      ]]
    }
  },
  {
    "id": "sa-namibia",
    "name": "Namibia", 
    "category": "country",
    "geometry": {
      "type": "Polygon",
      "coordinates": [[
        [11.7, -17.2], [25.3, -17.2], [25.3, -28.9], [11.7, -28.9], [11.7, -17.2]
      ]]
    }
  },
  {
    "id": "sa-zambia",
    "name": "Zambia",
    "category": "country",
    "geometry": {
      "type": "Polygon",
      "coordinates": [[
        [21.9, -8.2], [33.7, -8.2], [33.7, -18.1], [21.9, -18.1], [21.9, -8.2]
      ]]
    }
  },
  {
    "id": "sa-malawi",
    "name": "Malawi",
    "category": "country",
    "geometry": {
      "type": "Polygon", 
      "coordinates": [[
        [32.7, -9.4], [35.9, -9.4], [35.9, -17.1], [32.7, -17.1], [32.7, -9.4]
      ]]
    }
  },
  {
    "id": "sa-mozambique",
    "name": "Mozambique",
    "category": "country",
    "geometry": {
      "type": "Polygon",
      "coordinates": [[
        [30.2, -10.5], [40.8, -10.5], [40.8, -26.9], [30.2, -26.9], [30.2, -10.5]
      ]]
    }
  },
  {
    "id": "sa-angola",
    "name": "Angola",
    "category": "country",
    "geometry": {
      "type": "Polygon",
      "coordinates": [[
        [11.7, -4.4], [24.1, -4.4], [24.1, -18.0], [11.7, -18.0], [11.7, -4.4]
      ]]
    }
  },
  {
    "id": "sa-eswatini",
    "name": "Eswatini (Swaziland)",
    "category": "country",
    "geometry": {
      "type": "Polygon",
      "coordinates": [[
        [30.8, -25.7], [32.1, -25.7], [32.1, -27.3], [30.8, -27.3], [30.8, -25.7]
      ]]
    }
  },
  {
    "id": "sa-lesotho",
    "name": "Lesotho",
    "category": "country",
    "geometry": {
      "type": "Polygon", 
      "coordinates": [[
        [27.0, -28.6], [29.5, -28.6], [29.5, -30.7], [27.0, -30.7], [27.0, -28.6]
      ]]
    }
  }
]

ZIMBABWE_COUNTRY = {
  "id": "zw-country",
  "name": "Zimbabwe (Complete Country)",
  "category": "country",
  "geometry": {
    "type": "Polygon",
    "coordinates": [[
      [25.2, -15.6], [33.1, -15.6], [33.1, -22.4], [25.2, -22.4], [25.2, -15.6]
    ]]
  }
}

ALL_REGIONS = [ZIMBABWE_COUNTRY] + ZIMBABWE_PROVINCES + ZIMBABWE_DISTRICTS + SOUTHERN_AFRICA_COUNTRIES
