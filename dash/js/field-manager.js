/**
 * FIELD MANAGER
 * Handles field data loading, rendering, and selection
 */

const FieldManager = {
  fieldsData: [],
  fieldLayers: {},

  init() {
    this.loadFieldsData();
  },

  loadFieldsData() {
    Utils.updateLoadingProgress(40, 'Loading fields...');
    
    fetch("api/get_fields.php")
      .then(res => res.json())
      .then(data => {
        Utils.debugLog('Raw API response:', data);
        
        if (data.error) {
          console.error("API Error:", data.error);
          Notifications.show('Error loading field data: ' + data.error, 'error');
          document.getElementById('emptyStateContainer').classList.remove('hidden');
          Utils.updateLoadingProgress(60, 'Error loading fields...');
          Utils.hideLoadingOverlay();
          return;
        }
        
        if (data.type === "FeatureCollection") {
          this.fieldsData = data.features;
          window.DashboardState.fieldsData = this.fieldsData;
          Utils.debugLog('Processed fields data:', this.fieldsData);
          
          if (this.fieldsData.length === 0) {
            document.getElementById('emptyStateContainer').classList.remove('hidden');
            Utils.updateLoadingProgress(60, 'No fields available...');
            Utils.hideLoadingOverlay();
            return;
          }
          
          this.processBatchFields();
        } else {
          console.error("Invalid GeoJSON structure:", data);
          Notifications.show('Error: Invalid field data format', 'error');
          this.loadSampleFieldData();
        }
      })
      .catch(err => {
        console.error("Error loading fields:", err);
        Notifications.show('Error loading field data. Using sample data.', 'warning');
        this.loadSampleFieldData();
      });
  },

  processBatchFields() {
    let batchSize = CONFIG.UI.FIELD_BATCH_SIZE;
    let currentBatch = 0;
    
    const processBatch = () => {
      const startIndex = currentBatch * batchSize;
      const endIndex = Math.min(startIndex + batchSize, this.fieldsData.length);
      
      for (let i = startIndex; i < endIndex; i++) {
        this.addFieldToMap(this.fieldsData[i]);
      }
      
      currentBatch++;
      const progress = Math.min(60 + (currentBatch * batchSize / this.fieldsData.length) * 30, 90);
      Utils.updateLoadingProgress(progress, `Loading fields... (${Math.min(endIndex, this.fieldsData.length)}/${this.fieldsData.length})`);
      
      if (endIndex < this.fieldsData.length) {
        setTimeout(processBatch, CONFIG.UI.BATCH_PROCESS_DELAY);
      } else {
        this.finishFieldLoading();
      }
    };
    
    processBatch();
  },

  finishFieldLoading() {
    if (this.fieldsData.length > 0) {
      const allFieldsLayer = L.featureGroup(Object.values(this.fieldLayers));
      MapManager.getMap().fitBounds(allFieldsLayer.getBounds());
      this.selectField(this.fieldsData[0]);
    }
    
    Utils.updateLoadingProgress(90, 'Fields loaded...');
    Utils.hideLoadingOverlay();
    this.initSearchSuggestions();
  },

  addFieldToMap(field) {
    const layer = L.geoJSON(field, {
      style: function() {
        return { 
          color: '#ef4444',
          weight: 2,
          fillColor: 'transparent',
          fillOpacity: 0,
          smoothFactor: 1.5,
          interactive: true
        };
      },
      pane: 'overlayPane'
    }).addTo(MapManager.getMap());
    
    let tooltipContent = `<strong>${field.properties.name || 'Unnamed Field'}</strong><br>`;
    
    if (field.properties.crop) {
      tooltipContent += `Crop: ${field.properties.crop}<br>`;
    }
    
    if (field.properties.area_ha) {
      tooltipContent += `Area: ${field.properties.area_ha.toFixed(2)} ha<br>`;
    }
    
    if (field.properties.farmer_name) {
      tooltipContent += `Farmer: ${field.properties.farmer_name}<br>`;
    }
    
    if (field.properties.owner_name) {
      tooltipContent += `Institution: ${field.properties.owner_name}<br>`;
    }
    
    layer.bindTooltip(tooltipContent, { 
      sticky: true,
      opacity: 0.9
    });
    
    layer.on('click', () => {
      this.selectField(field);
    });
    
    this.fieldLayers[field.properties.id] = layer;
    layer.setZIndex(1000);
  },

  selectField(field) {
    window.DashboardState.selectedField = field;
    
    const props = field.properties;
    
    document.getElementById('fieldName').textContent = props.name || 'Unnamed Field';
    document.getElementById('fieldArea').textContent = props.area_ha ? props.area_ha.toFixed(2) + ' ha' : 'N/A';
    document.getElementById('fieldOwner').textContent = props.farmer_name || '--';
    document.getElementById('fieldInsurer').textContent = props.owner_name || '--';
    document.getElementById('fieldCrop').textContent = props.crop ? `${props.crop} ${props.variety ? '(' + props.variety + ')' : ''}` : 'N/A';
    
    Object.values(this.fieldLayers).forEach(layer => {
      layer.setStyle({
        color: '#ef4444',
        fillOpacity: 0,
        weight: 2
      });
    });
    
    if (this.fieldLayers[props.id]) {
      this.fieldLayers[props.id].setStyle({
        color: '#B6BF00',
        fillOpacity: 0.1,
        fillColor: '#B6BF00',
        weight: 3
      });
      
      MapManager.getMap().fitBounds(this.fieldLayers[props.id].getBounds());
    }
    
    WeatherManager.fetchWeatherData(field);
    
    if (MapManager.currentMapMode !== 'index') {
      setTimeout(() => {
        IndexManager.preloadIndexInBackground(field);
      }, 1000);
    }
    
    if (MapManager.currentMapMode === 'index') {
      IndexManager.loadIndexLayer(field);
      
      const indexSelector = document.getElementById('indexSelector');
      indexSelector.classList.remove('hidden');
      indexSelector.style.display = 'flex';
    }
    
    if (window.innerWidth < 768) {
      document.getElementById('panel').classList.add('active');
      document.getElementById('panelOverlay').classList.add('active');
    }
  },

  loadSampleFieldData() {
    const userEntityId = window.DashboardState.userEntityId || 0;
    const userRole = window.DashboardState.userRole || '';
    
    const sampleFields = [
      {
        type: "Feature",
        properties: {
          id: 1,
          name: "Field 1 - Wheat",
          farm_name: "Green Valley Farm",
          owner_name: "Green Valley Cooperative",
          owner_type: "farmer",
          insurer_name: "Zimbabwe Insurance Ltd",
          crop: "Wheat",
          variety: "SC513",
          area_ha: 25.7,
          planting_date: "2023-03-15",
          irrigated: true,
          owner_entity_id: userEntityId || 1,
          insurer_id: 1
        },
        geometry: {
          type: "Polygon",
          coordinates: [[
            [31.01, -17.78],
            [31.02, -17.78],
            [31.02, -17.79],
            [31.01, -17.79],
            [31.01, -17.78]
          ]]
        }
      },
      {
        type: "Feature",
        properties: {
          id: 2,
          name: "Field 2 - Maize",
          farm_name: "Sunnydale Farm",
          owner_name: "Sunnydale Farmers Co-op",
          owner_type: "farmer",
          insurer_name: "National Insurance",
          crop: "Maize",
          variety: "Pioneer 30G19",
          area_ha: 18.3,
          planting_date: "2023-03-01",
          irrigated: false,
          owner_entity_id: userEntityId || 2,
          insurer_id: 2
        },
        geometry: {
          type: "Polygon",
          coordinates: [[
            [31.03, -17.80],
            [31.04, -17.80],
            [31.04, -17.81],
            [31.03, -17.81],
            [31.03, -17.80]
          ]]
        }
      }
    ];
    
    if (userRole === 'admin') {
      this.fieldsData = sampleFields;
    } else if (userEntityId > 0) {
      this.fieldsData = sampleFields.filter(field => 
        field.properties.owner_entity_id === userEntityId
      );
    } else {
      this.fieldsData = [];
    }
    
    window.DashboardState.fieldsData = this.fieldsData;
    
    if (this.fieldsData.length === 0) {
      document.getElementById('emptyStateContainer').classList.remove('hidden');
      Utils.updateLoadingProgress(60, 'No fields available...');
      Utils.hideLoadingOverlay();
      return;
    }
    
    this.fieldsData.forEach(field => {
      this.addFieldToMap(field);
    });
    
    this.finishFieldLoading();
  },

  initSearchSuggestions() {
    const searchField = document.getElementById('searchField');
    const suggestionsContainer = document.getElementById('searchSuggestions');
    
    const highlightMatch = (text, query) => {
      if (!query) return text;
      const regex = new RegExp(`(${query})`, 'gi');
      return text.replace(regex, '<span class="search-suggestion-highlight">$1</span>');
    };
    
    searchField.addEventListener('input', () => {
      const searchTerm = searchField.value.toLowerCase().trim();
      
      suggestionsContainer.innerHTML = '';
      
      if (!searchTerm) {
        suggestionsContainer.style.display = 'none';
        return;
      }
      
      const matchingFields = this.fieldsData.filter(field => 
        (field.properties.name && field.properties.name.toLowerCase().includes(searchTerm)) ||
        (field.properties.farm_name && field.properties.farm_name.toLowerCase().includes(searchTerm)) ||
        (field.properties.owner_name && field.properties.owner_name.toLowerCase().includes(searchTerm)) ||
        (field.properties.crop && field.properties.crop.toLowerCase().includes(searchTerm))
      );
      
      if (matchingFields.length === 0) {
        suggestionsContainer.style.display = 'none';
        return;
      }
      
      matchingFields.forEach(field => {
        const suggestion = document.createElement('div');
        suggestion.className = 'search-suggestion';
        
        const fieldName = field.properties.name || 'Unnamed Field';
        const farmName = field.properties.farm_name || 'Unknown Farm';
        const ownerName = field.properties.owner_name || 'Unknown Owner';
        const cropType = field.properties.crop || 'Unknown Crop';
        
        suggestion.innerHTML = `
          <div>${highlightMatch(fieldName, searchTerm)}</div>
          <div class="suggestion-details">
            <span><i class="fas fa-home text-gray-400"></i>${highlightMatch(farmName, searchTerm)}</span>
            <span><i class="fas fa-user text-gray-400"></i>${highlightMatch(ownerName, searchTerm)}</span>
            <span><i class="fas fa-seedling text-gray-400"></i>${highlightMatch(cropType, searchTerm)}</span>
          </div>
        `;
        
        suggestion.addEventListener('click', () => {
          this.selectField(field);
          searchField.value = fieldName;
          suggestionsContainer.style.display = 'none';
        });
        
        suggestionsContainer.appendChild(suggestion);
      });
      
      suggestionsContainer.style.display = 'block';
    });
    
    document.addEventListener('click', (e) => {
      if (!searchField.contains(e.target) && !suggestionsContainer.contains(e.target)) {
        suggestionsContainer.style.display = 'none';
      }
    });
    
    searchField.addEventListener('keyup', (e) => {
      if (e.key === 'Enter') {
        const searchTerm = searchField.value.toLowerCase().trim();
        if (!searchTerm) return;
        
        const matchedField = this.fieldsData.find(field => 
          (field.properties.name && field.properties.name.toLowerCase().includes(searchTerm)) ||
          (field.properties.farm_name && field.properties.farm_name.toLowerCase().includes(searchTerm)) ||
          (field.properties.owner_name && field.properties.owner_name.toLowerCase().includes(searchTerm))
        );
        
        if (matchedField) {
          this.selectField(matchedField);
          suggestionsContainer.style.display = 'none';
          Notifications.show(`Found: ${matchedField.properties.name}`, 'success');
        } else {
          Notifications.show('No matching fields found', 'warning');
        }
      }
    });
  }
};
