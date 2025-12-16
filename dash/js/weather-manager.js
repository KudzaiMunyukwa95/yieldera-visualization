/**
 * WEATHER MANAGER
 * Handles weather data fetching and charts
 */

const WeatherManager = {
  weatherData: [],
  forecastData: [],
  cumulativeRainfall: 0,
  tempChart: null,
  historicalChart: null,

  fetchWeatherData(field) {
    if (!field) return;
    
    let lat, lon;
    try {
      if (field.geometry.type === "Polygon") {
        const bounds = L.geoJSON(field).getBounds();
        lat = bounds.getCenter().lat;
        lon = bounds.getCenter().lng;
      } else if (field.geometry.type === "Point") {
        const coords = field.geometry.coordinates;
        lon = coords[0];
        lat = coords[1];
      } else {
        Notifications.show('Unsupported field geometry type', 'error');
        return;
      }
    } catch (e) {
      console.error("Error getting field coordinates:", e);
      Notifications.show('Could not determine field location', 'error');
      return;
    }
    
    this.weatherData = [];
    this.cumulativeRainfall = 0;
    this.forecastData = [];
    window.DashboardState.weatherData = this.weatherData;
    window.DashboardState.forecastData = this.forecastData;
    
    document.getElementById('currentWeather').innerHTML = `
      <div class="col-span-2 flex justify-center items-center py-4">
        <div class="spinner"></div>
      </div>
    `;
    
    document.getElementById('weatherDataContainer').innerHTML = `
      <div class="text-center py-4">
        <div class="spinner mx-auto mb-2"></div>
        <div class="text-sm text-gray-500 dark:text-gray-400">Loading weather data...</div>
      </div>
    `;
    
    document.getElementById('forecastData').innerHTML = `
      <div class="text-center py-4">
        <div class="spinner mx-auto mb-2"></div>
        <div class="text-sm text-gray-500 dark:text-gray-400">Loading forecast data...</div>
      </div>
    `;
    
    fetch(`https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current_weather=true&timezone=auto`)
      .then(res => res.json())
      .then(currentData => {
        this.updateCurrentWeather(currentData);
        return fetch(`https://archive-api.open-meteo.com/v1/archive?latitude=${lat}&longitude=${lon}&start_date=${window.DashboardState.dateRange.start}&end_date=${window.DashboardState.dateRange.end}&daily=temperature_2m_max,temperature_2m_min,temperature_2m_mean,precipitation_sum,windspeed_10m_max&timezone=auto`);
      })
      .then(res => res.json())
      .then(histData => {
        this.updateHistoricalWeather(histData);
        return fetch(`https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max,uv_index_max,precipitation_probability_max,sunrise,sunset&forecast_days=7&timezone=auto`);
      })
      .then(res => res.json())
      .then(forecastData => {
        this.updateForecastWeather(forecastData);
      })
      .catch(error => {
        console.error("Error fetching weather data:", error);
        document.getElementById('currentWeather').innerHTML = `
          <div class="col-span-2 text-center py-4 text-red-500">
            <i class="fas fa-exclamation-circle text-xl mb-2"></i>
            <div>Error loading weather data</div>
          </div>
        `;
        document.getElementById('weatherDataContainer').innerHTML = `
          <div class="bg-gray-50 dark:bg-secondary-light rounded-lg p-4 mb-4">
            <div class="text-center text-red-500">
              <i class="fas fa-exclamation-circle text-xl mb-2"></i>
              <div>Failed to retrieve weather data. Please try again later.</div>
            </div>
          </div>
        `;
        document.getElementById('forecastData').innerHTML = `
          <div class="text-center py-4 text-red-500">
            <i class="fas fa-exclamation-circle text-xl mb-2"></i>
            <div>Failed to retrieve forecast data. Please try again later.</div>
          </div>
        `;
        Notifications.show('Error retrieving weather data', 'error');
      });
  },

  updateCurrentWeather(data) {
    if (!data || !data.current_weather) {
      document.getElementById('currentWeather').innerHTML = `
        <div class="col-span-2 text-center py-2">
          <div class="text-sm text-gray-500 dark:text-gray-400">No current weather data available</div>
        </div>
      `;
      return;
    }
    
    const current = data.current_weather;
    const currentDate = new Date();
    document.getElementById('currentDate').textContent = currentDate.toLocaleDateString('en-US', { 
      weekday: 'long', 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric' 
    });
    
    const weatherIconClass = Utils.getWeatherIconClass(current.weathercode);
    document.getElementById('weatherIcon').innerHTML = `<i class="${weatherIconClass}"></i>`;
    
    document.getElementById('currentWeather').innerHTML = `
      <div>
        <div class="text-xs text-gray-500 dark:text-gray-400">Temperature</div>
        <div class="text-base mt-1">${current.temperature}°C</div>
      </div>
      <div>
        <div class="text-xs text-gray-500 dark:text-gray-400">Weather</div>
        <div class="text-base mt-1">${Utils.getWeatherDescription(current.weathercode)}</div>
      </div>
      <div>
        <div class="text-xs text-gray-500 dark:text-gray-400">Wind Speed</div>
        <div class="text-base mt-1">${current.windspeed} km/h</div>
      </div>
      <div>
        <div class="text-xs text-gray-500 dark:text-gray-400">Wind Direction</div>
        <div class="text-base mt-1">${current.winddirection}°</div>
      </div>
    `;
  },

  updateHistoricalWeather(data) {
    if (!data || !data.daily) {
      document.getElementById('weatherDataContainer').innerHTML = `
        <div class="bg-gray-50 dark:bg-secondary-light rounded-lg p-4 mb-4">
          <div class="text-center text-gray-500 dark:text-gray-400 py-4">
            No historical weather data available for the selected date range
          </div>
        </div>
      `;
      return;
    }
    
    const dates = data.daily.time;
    const maxTemps = data.daily.temperature_2m_max;
    const minTemps = data.daily.temperature_2m_min;
    const avgTemps = data.daily.temperature_2m_mean;
    const rainfall = data.daily.precipitation_sum;
    const windspeed = data.daily.windspeed_10m_max;
    
    const tempData = {
      labels: [],
      minTemps: [],
      maxTemps: [],
      avgTemps: [],
      rainfall: []
    };
    
    let tableHtml = `
      <div class="bg-gray-50 dark:bg-secondary-light rounded-lg p-4 mb-4">
        <h3 class="font-medium mb-3">Daily Weather Data</h3>
        <div class="overflow-x-auto max-h-64 overflow-y-auto">
          <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead class="bg-gray-100 dark:bg-secondary sticky top-0">
              <tr>
                <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Date</th>
                <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Avg (°C)</th>
                <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Max (°C)</th>
                <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Min (°C)</th>
                <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Rain (mm)</th>
                <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Wind (km/h)</th>
              </tr>
            </thead>
            <tbody class="bg-white dark:bg-secondary-light divide-y divide-gray-200 dark:divide-gray-700">
    `;
    
    let totalRainfall = 0;
    let maxTemp = -Infinity;
    let minTemp = Infinity;
    let avgTempSum = 0;
    let daysCount = 0;
    
    const datesReversed = [...dates].reverse();
    const maxTempsReversed = [...maxTemps].reverse();
    const minTempsReversed = [...minTemps].reverse();
    const avgTempsReversed = [...avgTemps].reverse();
    const rainfallReversed = [...rainfall].reverse();
    const windspeedReversed = [...windspeed].reverse();
    
    for (let i = 0; i < datesReversed.length; i++) {
      const date = datesReversed[i];
      const max = maxTempsReversed[i] !== null ? maxTempsReversed[i] : 0;
      const min = minTempsReversed[i] !== null ? minTempsReversed[i] : 0;
      const avg = avgTempsReversed[i] !== null ? avgTempsReversed[i] : (max + min) / 2;
      const rain = rainfallReversed[i] !== null ? rainfallReversed[i] : 0;
      const wind = windspeedReversed[i] !== null ? windspeedReversed[i] : 0;
      
      tempData.labels.unshift(date);
      tempData.maxTemps.unshift(max !== 0 ? max : null);
      tempData.minTemps.unshift(min !== 0 ? min : null);
      tempData.avgTemps.unshift(avg !== 0 ? avg : null);
      tempData.rainfall.unshift(rain !== 0 ? rain : null);
      
      const formattedDate = Utils.formatDate(date);
      tableHtml += `
        <tr class="hover:bg-gray-50 dark:hover:bg-secondary">
          <td class="px-4 py-2 whitespace-nowrap text-sm">${formattedDate}</td>
          <td class="px-4 py-2 whitespace-nowrap text-sm">${avg !== 0 ? avg.toFixed(1) : 'N/A'}</td>
          <td class="px-4 py-2 whitespace-nowrap text-sm">${max !== 0 ? max.toFixed(1) : 'N/A'}</td>
          <td class="px-4 py-2 whitespace-nowrap text-sm">${min !== 0 ? min.toFixed(1) : 'N/A'}</td>
          <td class="px-4 py-2 whitespace-nowrap text-sm">${rain !== 0 ? rain.toFixed(1) : '0.0'}</td>
          <td class="px-4 py-2 whitespace-nowrap text-sm">${wind !== 0 ? wind.toFixed(1) : 'N/A'}</td>
        </tr>
      `;
      
      this.weatherData.push({
        date: formattedDate,
        avgTemp: avg !== 0 ? avg.toFixed(1) : 'N/A',
        maxTemp: max !== 0 ? max.toFixed(1) : 'N/A',
        minTemp: min !== 0 ? min.toFixed(1) : 'N/A',
        rain: rain !== 0 ? rain.toFixed(1) : '0.0',
        windSpeed: wind !== 0 ? wind.toFixed(1) : 'N/A'
      });
      
      totalRainfall += rain;
      if (max !== 0) maxTemp = Math.max(maxTemp, max);
      if (min !== 0) minTemp = Math.min(minTemp, min);
      if (avg !== 0) {
        avgTempSum += avg;
        daysCount++;
      }
    }
    
    window.DashboardState.weatherData = this.weatherData;
    
    tableHtml += `
            </tbody>
          </table>
        </div>
      </div>
    `;
    
    const summaryHtml = `
      <div class="bg-gray-50 dark:bg-secondary-light rounded-lg p-4 mb-4">
        <h3 class="font-medium mb-3">Weather Summary</h3>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <div class="text-xs text-gray-500 dark:text-gray-400">Total Rainfall</div>
            <div class="text-base mt-1">${totalRainfall.toFixed(1)} mm</div>
          </div>
          <div>
            <div class="text-xs text-gray-500 dark:text-gray-400">Max Temperature</div>
            <div class="text-base mt-1 ${maxTemp > 30 ? 'text-orange-500' : ''}">${maxTemp !== -Infinity ? maxTemp.toFixed(1) + '°C' : 'N/A'}</div>
          </div>
          <div>
            <div class="text-xs text-gray-500 dark:text-gray-400">Min Temperature</div>
            <div class="text-base mt-1">${minTemp !== Infinity ? minTemp.toFixed(1) + '°C' : 'N/A'}</div>
          </div>
          <div>
            <div class="text-xs text-gray-500 dark:text-gray-400">Avg Temperature</div>
            <div class="text-base mt-1">${daysCount > 0 ? (avgTempSum / daysCount).toFixed(1) + '°C' : 'N/A'}</div>
          </div>
        </div>
      </div>
    `;
    
    document.getElementById('weatherDataContainer').innerHTML = tableHtml + summaryHtml;
    
    this.cumulativeRainfall = totalRainfall;
    
    this.updateTemperatureChart(tempData);
    
    this.updateHistoricalTab(tempData, {
      totalRainfall: totalRainfall,
      maxTemp: maxTemp !== -Infinity ? maxTemp : null,
      minTemp: minTemp !== Infinity ? minTemp : null,
      avgTemp: daysCount > 0 ? avgTempSum / daysCount : null
    });
  },

  updateForecastWeather(data) {
    if (!data || !data.daily) {
      document.getElementById('forecastData').innerHTML = `
        <div class="text-center text-gray-500 dark:text-gray-400 py-4">
          No forecast data available
        </div>
      `;
      return;
    }
    
    const dates = data.daily.time;
    const maxTemps = data.daily.temperature_2m_max;
    const minTemps = data.daily.temperature_2m_min;
    const weatherCodes = data.daily.weathercode;
    const rainfall = data.daily.precipitation_sum;
    const windspeed = data.daily.windspeed_10m_max;
    const uvIndex = data.daily.uv_index_max;
    const rainProb = data.daily.precipitation_probability_max;
    const sunrise = data.daily.sunrise;
    const sunset = data.daily.sunset;
    
    this.forecastData = [];
    window.DashboardState.forecastData = this.forecastData;
    
    let forecastHtml = `<div class="grid grid-cols-1 md:grid-cols-2 gap-4">`;
    
    for (let i = 0; i < Math.min(dates.length, 7); i++) {
      const date = new Date(dates[i]);
      const formattedDate = date.toLocaleDateString('en-US', { 
        weekday: 'short', 
        month: 'short', 
        day: 'numeric' 
      });
      
      let sunriseTime = "N/A";
      let sunsetTime = "N/A";
      
      if (sunrise && sunset && sunrise[i] && sunset[i]) {
        const sunriseDate = new Date(sunrise[i]);
        const sunsetDate = new Date(sunset[i]);
        
        sunriseTime = sunriseDate.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        sunsetTime = sunsetDate.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
      }
      
      const weatherIconClass = Utils.getWeatherIconClass(weatherCodes[i]);
      
      forecastHtml += `
        <div class="forecast-card">
          <div class="forecast-date">${formattedDate}</div>
          <div class="forecast-icon">
            <i class="${weatherIconClass}"></i>
          </div>
          <div class="text-sm">${Utils.getWeatherDescription(weatherCodes[i])}</div>
          <div class="forecast-temp">
            <div class="forecast-temp-max">${maxTemps[i].toFixed(1)}°</div>
            <div class="forecast-temp-min">${minTemps[i].toFixed(1)}°</div>
          </div>
          <div class="weather-details mt-3">
            <div class="weather-detail">
              <i class="fas fa-tint"></i>
              <span>${rainfall[i].toFixed(1)} mm</span>
            </div>
            <div class="weather-detail">
              <i class="fas fa-percentage"></i>
              <span>${rainProb[i] || 'N/A'}%</span>
            </div>
            <div class="weather-detail">
              <i class="fas fa-wind"></i>
              <span>${windspeed[i].toFixed(1)} km/h</span>
            </div>
            <div class="weather-detail">
              <i class="fas fa-sun"></i>
              <span>UV ${uvIndex[i].toFixed(0)}</span>
            </div>
          </div>
          <div class="mt-2 w-full text-xs grid grid-cols-2 gap-1">
            <div class="text-center">
              <i class="fas fa-sunrise text-yellow-500 mr-1"></i>${sunriseTime}
            </div>
            <div class="text-center">
              <i class="fas fa-sunset text-orange-500 mr-1"></i>${sunsetTime}
            </div>
          </div>
        </div>
      `;
      
      this.forecastData.push({
        date: formattedDate,
        maxTemp: maxTemps[i].toFixed(1),
        minTemp: minTemps[i].toFixed(1),
        weather: Utils.getWeatherDescription(weatherCodes[i]),
        rainfall: rainfall[i].toFixed(1),
        rainProbability: rainProb[i] || 'N/A',
        windSpeed: windspeed[i].toFixed(1),
        uvIndex: uvIndex[i].toFixed(0),
        sunrise: sunriseTime,
        sunset: sunsetTime
      });
    }
    
    forecastHtml += `</div>`;
    
    document.getElementById('forecastData').innerHTML = forecastHtml;
  },

  updateTemperatureChart(data) {
    const ctx = document.getElementById('tempChart').getContext('2d');
    
    if (this.tempChart) {
      this.tempChart.destroy();
    }
    
    this.tempChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: data.labels.map(date => Utils.formatDate(date)),
        datasets: [
          {
            label: 'Max Temperature (°C)',
            data: data.maxTemps,
            borderColor: 'rgba(239, 68, 68, 1)',
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            tension: 0.4,
            fill: false
          },
          {
            label: 'Avg Temperature (°C)',
            data: data.avgTemps,
            borderColor: 'rgba(1, 40, 47, 1)',
            backgroundColor: 'rgba(1, 40, 47, 0.1)',
            tension: 0.4,
            fill: false
          },
          {
            label: 'Min Temperature (°C)',
            data: data.minTemps,
            borderColor: 'rgba(74, 222, 128, 1)',
            backgroundColor: 'rgba(74, 222, 128, 0.1)',
            tension: 0.4,
            fill: false
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            beginAtZero: false,
            title: {
              display: true,
              text: 'Temperature (°C)'
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
            position: 'top'
          },
          tooltip: {
            callbacks: {
              label: function(context) {
                return `${context.dataset.label}: ${context.raw !== null ? context.raw : 'N/A'}`;
              }
            }
          }
        }
      }
    });
  },

  updateHistoricalTab(data, stats) {
    document.getElementById('historicalDateRange').textContent = `Date range: ${Utils.formatDate(window.DashboardState.dateRange.start)} - ${Utils.formatDate(window.DashboardState.dateRange.end)}`;
    
    document.getElementById('historicalSummary').innerHTML = `
      <div>
        <div class="text-xs text-gray-500 dark:text-gray-400">Total Rainfall</div>
        <div class="text-base mt-1">${stats.totalRainfall.toFixed(1)} mm</div>
      </div>
      <div>
        <div class="text-xs text-gray-500 dark:text-gray-400">Max Temperature</div>
        <div class="text-base mt-1 ${stats.maxTemp > 30 ? 'text-orange-500' : ''}">${stats.maxTemp !== null ? stats.maxTemp.toFixed(1) + '°C' : 'N/A'}</div>
      </div>
      <div>
        <div class="text-xs text-gray-500 dark:text-gray-400">Min Temperature</div>
        <div class="text-base mt-1">${stats.minTemp !== null ? stats.minTemp.toFixed(1) + '°C' : 'N/A'}</div>
      </div>
      <div>
        <div class="text-xs text-gray-500 dark:text-gray-400">Avg Temperature</div>
        <div class="text-base mt-1">${stats.avgTemp !== null ? stats.avgTemp.toFixed(1) + '°C' : 'N/A'}</div>
      </div>
    `;
    
    const ctx = document.getElementById('historicalChart').getContext('2d');
    
    if (this.historicalChart) {
      this.historicalChart.destroy();
    }
    
    this.historicalChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: data.labels.map(date => Utils.formatDate(date)),
        datasets: [
          {
            label: 'Rainfall (mm)',
            data: data.rainfall,
            backgroundColor: 'rgba(59, 130, 246, 0.6)',
            borderColor: 'rgba(59, 130, 246, 1)',
            borderWidth: 1,
            yAxisID: 'y1'
          },
          {
            label: 'Min Temp (°C)',
            data: data.minTemps,
            backgroundColor: 'rgba(74, 222, 128, 0.6)',
            borderColor: 'rgba(74, 222, 128, 1)',
            borderWidth: 1,
            type: 'line',
            yAxisID: 'y'
          },
          {
            label: 'Max Temp (°C)',
            data: data.maxTemps,
            backgroundColor: 'rgba(239, 68, 68, 0.6)',
            borderColor: 'rgba(239, 68, 68, 1)',
            borderWidth: 1,
            type: 'line',
            yAxisID: 'y'
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            type: 'linear',
            display: true,
            position: 'left',
            title: {
              display: true,
              text: 'Temperature (°C)'
            }
          },
          y1: {
            type: 'linear',
            display: true,
            position: 'right',
            grid: {
              drawOnChartArea: false
            },
            title: {
              display: true,
              text: 'Rainfall (mm)'
            }
          }
        }
      }
    });
  }
};
