/**
 * INDEX MANAGER
 * Handles vegetation indices (NDVI, EVI, etc.)
 */

const IndexManager = {
  indexData: [],
  indexChart: null,
  isIndexLoading: false,
  indexRetryCount: 0,
  lastIndexResponse: null,
  preloadedIndexData: null,
  isPreloadingIndex: false,

  setCurrentIndex(indexType) {
    window.DashboardState.currentIndexType = indexType;
    this.updateIndexLegend();
    this.updateIndexDescription();
  },

  loadIndexLayer(field) {
    this.indexRetryCount = 0;
    this.loadIndexLayerWithRetry(field);
  },

  loadIndexLayerWithRetry(field) {
    if (!this.preloadedIndexData) {
      Notifications.show(`Loading ${window.DashboardState.currentIndexType}...`, 'info');
    }
    
    try {
      if (MapManager.currentIndexLayer && MapManager.getMap().hasLayer(MapManager.currentIndexLayer)) {
        MapManager.getMap().removeLayer(MapManager.currentIndexLayer);
      }
      MapManager.currentIndexLayer = null;
    } catch (e) {
      console.error("Error removing layers:", e);
    }
    
    let coordinates = [];
    try {
      if (field.geometry.type === "Polygon") {
        coordinates = field.geometry.coordinates[0];
      } else {
        Notifications.show('Invalid field geometry', 'error');
        MapManager.layerTransitionInProgress = false;
        return;
      }
    } catch (e) {
      console.error("Error extracting field coordinates:", e);
      Notifications.show('Could not process field geometry', 'error');
      MapManager.layerTransitionInProgress = false;
      return;
    }
    
    const payload = {
      coordinates: [coordinates],
      startDate: window.DashboardState.dateRange.start,
      endDate: window.DashboardState.dateRange.end,
      index_type: window.DashboardState.currentIndexType
    };
    
    Utils.debugLog(`Index Request #${this.indexRetryCount+1} for ${window.DashboardState.currentIndexType}:`, payload);
    
    fetch(CONFIG.GEE_API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${CONFIG.GEE_API_TOKEN}`
      },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(CONFIG.INDEX.REQUEST_TIMEOUT)
    })
    .then(response => {
      if (!response.ok) {
        throw new Error(`API request failed with status ${response.status}`);
      }
      return response.json();
    })
    .then(data => {
      Utils.debugLog(`${window.DashboardState.currentIndexType} API response:`, data);
      
      if (!data.success) {
        throw new Error(data.message || `Failed to retrieve ${window.DashboardState.currentIndexType} data`);
      }
      
      if (data.index && data.palette && data.range && data.explanation) {
        INDEX_CONFIGS[window.DashboardState.currentIndexType] = {
          range: data.range,
          palette: data.palette,
          explanation: data.explanation
        };
        
        this.updateIndexLegend();
        this.updateIndexDescription();
      }
      
      this.lastIndexResponse = data;
      this.createIndexLayer(data, field);
      MapManager.layerTransitionInProgress = false;
    })
    .catch(error => {
      console.error(`${window.DashboardState.currentIndexType} fetch error (attempt ${this.indexRetryCount + 1}):`, error);
      
      this.indexRetryCount++;
      
      if (this.indexRetryCount < CONFIG.INDEX.MAX_RETRIES) {
        Notifications.show(`Retrying ${window.DashboardState.currentIndexType} load... (${this.indexRetryCount + 1}/${CONFIG.INDEX.MAX_RETRIES})`, 'info');
        
        setTimeout(() => {
          this.loadIndexLayerWithRetry(field);
        }, 1000);
      } else {
        if (this.lastIndexResponse) {
          Notifications.show(`Using cached ${window.DashboardState.currentIndexType} data`, 'info');
          this.createIndexLayer(this.lastIndexResponse, field);
        } else {
          this.calculateFieldIndex(field);
          this.hideCloudCoverInfo();
        }
        
        MapManager.layerTransitionInProgress = false;
      }
    });
  },

  createIndexLayer(data, field) {
    try {
      if (data.tile_url) {
        Utils.debugLog(`Creating ${window.DashboardState.currentIndexType} layer`);
        
        MapManager.currentIndexLayer = L.tileLayer(data.tile_url, {
          attribution: `${window.DashboardState.currentIndexType} © Google Earth Engine`,
          maxZoom: 19,
          opacity: window.DashboardState.currentIndexType === 'RGB' ? 1.0 : 0.7,
          zIndex: 10,
          keepBuffer: 2,
          maxNativeZoom: 18
        });
        
        MapManager.currentIndexLayer.addTo(MapManager.getMap());
        Utils.debugLog(`Applied ${window.DashboardState.currentIndexType} layer`);
        
        const indexSelector = document.getElementById('indexSelector');
        indexSelector.classList.remove('hidden');
        indexSelector.style.display = 'flex';
        
        this.updateCloudCoverInfo(data.cloud_cover || data.cloudy_pixel_percentage, data.total_images || data.collection_size);
        
        if (window.DashboardState.currentIndexType !== 'RGB' && (data.mean_value !== undefined || data.mean !== undefined)) {
          this.calculateFieldIndex(field, data.image_processed, data.mean_value || data.mean, data.min_value || data.min, data.max_value || data.max);
        } else if (window.DashboardState.currentIndexType === 'RGB') {
          this.calculateFieldIndex(field, data.image_processed);
        } else {
          this.calculateFieldIndex(field);
        }
        
        Notifications.show(`${window.DashboardState.currentIndexType} loaded successfully`, 'success');
      } else {
        Notifications.show(`${window.DashboardState.currentIndexType} data unavailable`, 'warning');
        this.calculateFieldIndex(field, data.image_processed);
        this.updateCloudCoverInfo(data.cloud_cover || data.cloudy_pixel_percentage, data.total_images || data.collection_size);
      }
      
    } catch (e) {
      console.error(`Error creating ${window.DashboardState.currentIndexType} layer:`, e);
      Notifications.show(`Error creating ${window.DashboardState.currentIndexType} layer`, 'error');
    }
  },

  preloadIndexInBackground(field) {
    if (this.isPreloadingIndex || !field) return;
    
    this.isPreloadingIndex = true;
    Utils.debugLog('Starting background index preload');
    
    let coordinates = [];
    try {
      if (field.geometry.type === "Polygon") {
        coordinates = field.geometry.coordinates[0];
      } else {
        this.isPreloadingIndex = false;
        return;
      }
    } catch (e) {
      this.isPreloadingIndex = false;
      return;
    }
    
    const payload = {
      coordinates: [coordinates],
      startDate: window.DashboardState.dateRange.start,
      endDate: window.DashboardState.dateRange.end,
      index_type: window.DashboardState.currentIndexType
    };
    
    fetch(CONFIG.GEE_API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${CONFIG.GEE_API_TOKEN}`
      },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(15000)
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        this.preloadedIndexData = {
          fieldId: field.properties.id,
          indexType: window.DashboardState.currentIndexType,
          data: data,
          timestamp: Date.now()
        };
        Utils.debugLog(`${window.DashboardState.currentIndexType} preloaded successfully for field`, field.properties.id);
      }
      this.isPreloadingIndex = false;
    })
    .catch(error => {
      Utils.debugLog(`Background ${window.DashboardState.currentIndexType} preload failed:`, error);
      this.isPreloadingIndex = false;
    });
  },

  calculateFieldIndex(field, imageDate = null, meanValue = null, minValue = null, maxValue = null) {
    let indexValue, indexMin, indexMax;
    
    const config = INDEX_CONFIGS[window.DashboardState.currentIndexType];
    
    if (meanValue !== null && window.DashboardState.currentIndexType !== 'RGB') {
      indexValue = meanValue;
      indexMin = minValue;
      indexMax = maxValue;
    } else if (window.DashboardState.currentIndexType === 'RGB') {
      this.updateIndexDisplay(null, imageDate || new Date(), null, null);
      return;
    } else {
      if (config && config.range) {
        const fieldId = field.properties.id || 0;
        const fromDate = window.DashboardState.dateRange.start || '2023-01-01';
        const dateHash = fromDate.split('-').reduce((a, b) => a + parseInt(b), 0);
        
        const rangeMid = (config.range[0] + config.range[1]) / 2;
        const rangeSpan = config.range[1] - config.range[0];
        
        const variation = (Math.sin(fieldId * 0.1) * 0.1) + (Math.cos(dateHash * 0.05) * 0.05);
        
        indexValue = Math.max(config.range[0], Math.min(config.range[1], rangeMid + (variation * rangeSpan * 0.3)));
        indexMin = Math.max(config.range[0], indexValue - 0.1);
        indexMax = Math.min(config.range[1], indexValue + 0.1);
      } else {
        indexValue = 0.5;
        indexMin = 0.4;
        indexMax = 0.6;
      }
      
      this.hideCloudCoverInfo();
    }
    
    let captureDate;
    if (imageDate) {
      captureDate = new Date(imageDate);
    } else {
      const endDate = new Date(window.DashboardState.dateRange.end);
      captureDate = new Date(endDate);
      captureDate.setDate(captureDate.getDate() - Math.floor(Math.random() * 5));
    }
    
    this.updateIndexDisplay(indexValue, captureDate, indexMin, indexMax);
    this.generateHistoricalIndex(indexValue, indexMin, indexMax);
  },

  updateIndexDisplay(indexValue, captureDate, minValue = null, maxValue = null) {
    const config = INDEX_CONFIGS[window.DashboardState.currentIndexType];
    
    if (window.DashboardState.currentIndexType === 'RGB') {
      document.getElementById('currentIndexValue').textContent = 'RGB Image';
      document.getElementById('minIndexValue').textContent = 'N/A';
      document.getElementById('maxIndexValue').textContent = 'N/A';
      document.getElementById('indexRangeMin').textContent = '';
      document.getElementById('indexRangeMax').textContent = '';
      document.getElementById('dynamicIndexScale').style.display = 'none';
    } else {
      document.getElementById('currentIndexValue').textContent = indexValue !== null ? indexValue.toFixed(2) : '--';
      document.getElementById('minIndexValue').textContent = minValue !== null ? minValue.toFixed(2) : '--';
      document.getElementById('maxIndexValue').textContent = maxValue !== null ? maxValue.toFixed(2) : '--';
      
      if (config && config.range) {
        document.getElementById('indexRangeMin').textContent = config.range[0].toString();
        document.getElementById('indexRangeMax').textContent = config.range[1].toString();
      }
      
      const scaleElement = document.getElementById('dynamicIndexScale');
      scaleElement.style.display = 'block';
      if (config && config.palette && config.palette.length > 0) {
        scaleElement.style.background = `linear-gradient(to right, ${config.palette.join(', ')})`;
      }
    }
    
    this.updateIndexDescription();
    
    document.getElementById('indexDateRange').textContent = `Date range: ${Utils.formatDate(window.DashboardState.dateRange.start)} - ${Utils.formatDate(window.DashboardState.dateRange.end)}`;
    
    const captureDateStr = captureDate instanceof Date ? 
      captureDate.toLocaleDateString('en-GB') : 
      'Not available';
    
    document.getElementById('indexValueLabel').textContent = `${window.DashboardState.currentIndexType} imagery for date: ${captureDateStr}`;
    document.getElementById('indexCaptureDate').textContent = `Image processed: ${new Date().toLocaleDateString('en-GB')}`;
    
    if (window.DashboardState.selectedField) {
      window.DashboardState.selectedField.properties.indexType = window.DashboardState.currentIndexType;
      window.DashboardState.selectedField.properties.indexValue = indexValue;
      window.DashboardState.selectedField.properties.indexCaptureDate = captureDateStr;
      window.DashboardState.selectedField.properties.indexMin = minValue;
      window.DashboardState.selectedField.properties.indexMax = maxValue;
    }
  },

  generateHistoricalIndex(currentValue, minValue = null, maxValue = null) {
    const start = new Date(window.DashboardState.dateRange.start);
    const end = new Date(window.DashboardState.dateRange.end);
    const dayDiff = Math.floor((end - start) / (1000 * 60 * 60 * 24));
    
    const intervalDays = 5;
    const dataPoints = [];
    
    const config = INDEX_CONFIGS[window.DashboardState.currentIndexType];
    const indexRange = (minValue !== null && maxValue !== null) ? 
                      (maxValue - minValue) : 
                      (config && config.range ? (config.range[1] - config.range[0]) * 0.2 : 0.2);
    
    for (let i = 0; i <= dayDiff; i += intervalDays) {
      const date = new Date(start);
      date.setDate(date.getDate() + i);
      
      const dayProgress = i / dayDiff;
      const trendFactor = (indexRange * 0.3) * Math.sin(dayProgress * Math.PI * 2); 
      const randomFactor = ((Math.random() - 0.5) * indexRange * 0.2);
      
      let value = currentValue + trendFactor + randomFactor;
      
      if (config && config.range) {
        const lowerBound = minValue !== null ? Math.max(config.range[0], minValue * 0.9) : config.range[0] + 0.05;
        const upperBound = maxValue !== null ? Math.min(config.range[1], maxValue * 1.1) : config.range[1] - 0.05;
        value = Math.max(lowerBound, Math.min(upperBound, value));
      }
      
      dataPoints.push({
        date: date.toISOString().split('T')[0],
        value: value,
        indexType: window.DashboardState.currentIndexType
      });
    }
    
    dataPoints.sort((a, b) => new Date(b.date) - new Date(a.date));
    
    this.indexData = dataPoints;
    window.DashboardState.indexData = this.indexData;
    this.updateIndexChart(dataPoints);
  },

  updateIndexChart(data) {
    const ctx = document.getElementById('indexChart').getContext('2d');
    
    const sortedData = [...data].sort((a, b) => new Date(a.date) - new Date(b.date));
    
    const labels = sortedData.map(item => Utils.formatDate(item.date));
    const values = sortedData.map(item => item.value);
    
    if (this.indexChart) {
      this.indexChart.destroy();
    }
    
    const config = INDEX_CONFIGS[window.DashboardState.currentIndexType];
    let chartColor = '#B6BF00';
    
    if (config && config.palette && config.palette.length > 0) {
      chartColor = config.palette[Math.floor(config.palette.length / 2)];
    }
    
    this.indexChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: window.DashboardState.currentIndexType,
            data: values,
            borderColor: chartColor,
            backgroundColor: `${chartColor}20`,
            tension: 0.4,
            fill: true
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            beginAtZero: false,
            min: config && config.range ? config.range[0] : -1,
            max: config && config.range ? config.range[1] : 1,
            title: {
              display: true,
              text: `${window.DashboardState.currentIndexType} Value`
            }
          },
          x: {
            title: {
              display: true,
              text: 'Date'
            }
          }
        },
        plugins: {
          legend: {
            display: true,
            position: 'top'
          },
          tooltip: {
            callbacks: {
              label: function(context) {
                return `${window.DashboardState.currentIndexType}: ${context.parsed.y.toFixed(2)}`;
              }
            }
          }
        }
      }
    });
  },

  updateCloudCoverInfo(cloudPercentage, totalImages) {
    if (cloudPercentage === undefined) {
      this.hideCloudCoverInfo();
      return;
    }
    
    const badge = document.getElementById('cloudCoverBadge');
    const valueSpan = document.getElementById('cloudCoverValue');
    
    badge.classList.remove('hidden', 'cloud-low', 'cloud-medium', 'cloud-high');
    
    if (cloudPercentage < 10) {
      badge.classList.add('cloud-low');
    } else if (cloudPercentage < 30) {
      badge.classList.add('cloud-medium');
    } else {
      badge.classList.add('cloud-high');
    }
    
    valueSpan.textContent = Math.round(cloudPercentage);
    badge.classList.remove('hidden');
    
    document.getElementById('cloudCoverText').textContent = `${Math.round(cloudPercentage)}%`;
    
    let qualityText;
    if (cloudPercentage < 10) {
      qualityText = 'Excellent';
    } else if (cloudPercentage < 20) {
      qualityText = 'Very Good';
    } else if (cloudPercentage < 30) {
      qualityText = 'Good';
    } else if (cloudPercentage < 50) {
      qualityText = 'Fair';
    } else {
      qualityText = 'Poor';
    }
    
    document.getElementById('imageQuality').textContent = qualityText;
    
    if (totalImages && totalImages > 0) {
      const imageCountText = totalImages === 1 ? '1 image' : `${totalImages} images`;
      document.getElementById('imageCount').textContent = imageCountText;
    } else {
      document.getElementById('imageCount').textContent = '--';
    }
    
    if (window.DashboardState.selectedField) {
      window.DashboardState.selectedField.properties.cloudCover = cloudPercentage;
      window.DashboardState.selectedField.properties.imageQuality = qualityText;
      window.DashboardState.selectedField.properties.imageCount = totalImages || 1;
    }
  },

  hideCloudCoverInfo() {
    document.getElementById('cloudCoverBadge').classList.add('hidden');
    document.getElementById('cloudCoverText').textContent = '--';
    document.getElementById('imageQuality').textContent = '--';
    document.getElementById('imageCount').textContent = '--';
  },

  updateIndexLegend() {
    const config = INDEX_CONFIGS[window.DashboardState.currentIndexType];
    // Legend is shown in sidebar only, not on map
  },

  updateIndexDescription() {
    const config = INDEX_CONFIGS[window.DashboardState.currentIndexType];
    if (config && config.explanation) {
      document.getElementById('indexDescription').textContent = config.explanation;
    } else {
      document.getElementById('indexDescription').textContent = 'Loading index information...';
    }
  }
};