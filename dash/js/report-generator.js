/**
 * REPORT GENERATOR
 * Handles PDF and CSV report generation
 */

const ReportGenerator = {
  init() {
    this.initReportButtons();
  },

  initReportButtons() {
    document.getElementById('generateWeatherReport')?.addEventListener('click', () => {
      this.generatePdfReport('weather');
    });

    document.getElementById('downloadWeatherData')?.addEventListener('click', () => {
      this.exportWeatherData();
    });

    document.getElementById('generateIndexReport')?.addEventListener('click', () => {
      this.generateAdvancedReport();
    });

    document.getElementById('refreshForecastData')?.addEventListener('click', () => {
      if (window.DashboardState.selectedField) {
        Notifications.show('Refreshing forecast data...', 'info');
        WeatherManager.fetchWeatherData(window.DashboardState.selectedField);
      } else {
        Notifications.show('No field selected', 'warning');
      }
    });

    document.getElementById('generateForecastReport')?.addEventListener('click', () => {
      this.generateForecastReport();
    });

    document.getElementById('refreshIndexData')?.addEventListener('click', () => {
      if (window.DashboardState.selectedField) {
        Notifications.show(`Refreshing ${window.DashboardState.currentIndexType} data...`, 'info');
        IndexManager.lastIndexResponse = null;

        if (MapManager.currentMapMode === 'index') {
          IndexManager.lastIndexResponse = null;
          IndexManager.preloadedIndexData = null;
          IndexManager.indexRetryCount = 0;
          IndexManager.loadIndexLayer(window.DashboardState.selectedField);
        }
      } else {
        Notifications.show('No field selected', 'warning');
      }
    });
  },

  generateAdvancedReport() {
    const selectedField = window.DashboardState.selectedField;
    const dateRange = window.DashboardState.dateRange;
    const token = CONFIG.GEE_API_TOKEN;

    if (!selectedField) {
      Notifications.show('No field selected', 'warning');
      return;
    }

    const props = selectedField.properties;
    const payload = {
      field_name: props.name || 'Unknown Field',
      crop: props.crop || 'Unknown Crop',
      area: props.area_ha || 0,
      irrigation: props.irrigated ? 'irrigated' : 'rainfed',
      planting_date: props.planting_date || null,
      coordinates: selectedField.geometry,
      start_date: dateRange.start,
      end_date: dateRange.end
    };

    Notifications.show('🤖 Generating AI-powered intelligence report... This may take 10-20 seconds.', 'info');

    const reportButton = document.getElementById('generateIndexReport');
    const originalButtonText = reportButton.innerHTML;
    this.setButtonLoading(reportButton, true);

    fetch(CONFIG.REPORT_API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(60000)
    })
      .then(response => {
        if (!response.ok) {
          throw new Error(`API request failed with status ${response.status}`);
        }
        return response.json();
      })
      .then(data => {
        if (!data.success) {
          throw new Error(data.error || 'Failed to generate report');
        }

        const pdfBase64 = data.pdf.base64;
        const filename = data.pdf.filename || `${props.name || 'Field'}_AI_Report_${new Date().toISOString().split('T')[0]}.pdf`;

        this.downloadPDFFromBase64(pdfBase64, filename);
        Notifications.show('✅ AI Intelligence Report generated successfully!', 'success');
        this.setButtonLoading(reportButton, false, originalButtonText);
      })
      .catch(error => {
        console.error('Error generating AI report:', error);
        Notifications.show(`❌ Error generating AI report: ${error.message}`, 'error');
        this.setButtonLoading(reportButton, false, originalButtonText);
      });
  },

  setButtonLoading(button, isLoading, originalText = '') {
    if (isLoading) {
      button.disabled = true;
      button.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Generating AI Report...';
    } else {
      button.disabled = false;
      button.innerHTML = originalText;
    }
  },

  downloadPDFFromBase64(base64String, filename) {
    const binaryString = atob(base64String);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }

    const blob = new Blob([bytes], { type: 'application/pdf' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  },

  // Helper method to load Yieldera logo as base64
  async loadYielderaLogo() {
    try {
      // Use PNG version of logo for better jsPDF compatibility
      const logoUrl = 'https://yieldera.co.zw/assets/img/logo.png';
      const response = await fetch(logoUrl);
      const blob = await response.blob();

      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onloadend = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsDataURL(blob);
      });
    } catch (error) {
      console.warn('Could not load Yieldera logo:', error);
      return null;
    }
  },

  async generatePdfReport(type = 'weather') {
    if (!window.DashboardState.selectedField) {
      Notifications.show('No field selected', 'warning');
      return;
    }

    if (type === 'weather' && WeatherManager.weatherData.length === 0) {
      Notifications.show('No weather data available for PDF report', 'warning');
      return;
    }

    if (type === 'index' && (!window.DashboardState.selectedField.properties.indexValue && window.DashboardState.currentIndexType !== 'RGB')) {
      Notifications.show('No index data available for PDF report', 'warning');
      return;
    }

    Notifications.show(`Generating ${type} PDF report...`, 'info');

    const props = window.DashboardState.selectedField.properties;

    let fieldLat = 'N/A', fieldLon = 'N/A';
    try {
      const bounds = L.geoJSON(window.DashboardState.selectedField).getBounds();
      fieldLat = bounds.getCenter().lat.toFixed(6);
      fieldLon = bounds.getCenter().lng.toFixed(6);
    } catch (e) {
      console.error("Error getting field coordinates for PDF:", e);
    }

    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();

    // Load logo
    const logoBase64 = await this.loadYielderaLogo();

    // Header
    doc.setFillColor(1, 40, 47);
    doc.rect(0, 0, 210, 25, 'F');
    doc.setTextColor(255, 255, 255);

    // Add Yieldera logo
    if (logoBase64) {
      try {
        // Add logo image (adjust dimensions as needed)
        doc.addImage(logoBase64, 'PNG', 15, 8, 30, 10);
      } catch (e) {
        console.warn('Could not add logo to PDF:', e);
        // Fallback to text
        doc.setFontSize(16);
        doc.setFont('helvetica', 'bold');
        doc.text("YIELDERA", 15, 15);
      }
    } else {
      // Fallback to text if logo couldn't be loaded
      doc.setFontSize(16);
      doc.setFont('helvetica', 'bold');
      doc.text("YIELDERA", 15, 15);
    }

    doc.setFontSize(18);
    doc.text(type === 'weather' ? "Weather Report" : `${window.DashboardState.currentIndexType} Report`, 105, 15, { align: 'center' });
    doc.setFontSize(8);
    doc.text(new Date().toLocaleDateString('en-GB'), 195, 15, { align: 'right' });

    // Field Details
    doc.setFontSize(14);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(0, 0, 0);
    doc.text("Field Details", 14, 35);
    doc.setFont('helvetica', 'normal');

    const fieldDetails = [
      ["Field Name:", props.name || 'N/A'],
      ["Farm Name:", props.farm_name || 'N/A'],
      ["Owner:", props.owner_name || 'N/A'],
      ["Crop Type:", props.crop || 'N/A'],
      ["Variety:", props.variety || 'N/A'],
      ["Planting Date:", props.planting_date ? Utils.formatDate(props.planting_date) : 'N/A'],
      ["Area:", props.area_ha ? props.area_ha.toFixed(2) + ' ha' : 'N/A'],
      ["Irrigated:", props.irrigated ? 'Yes' : 'No'],
      ["Latitude:", fieldLat + "°"],
      ["Longitude:", fieldLon + "°"],
      ["Date Range:", `${Utils.formatDate(window.DashboardState.dateRange.start)} to ${Utils.formatDate(window.DashboardState.dateRange.end)}`]
    ];

    if (type === 'weather') {
      fieldDetails.push(["Total Rainfall:", WeatherManager.cumulativeRainfall.toFixed(2) + " mm"]);
    } else {
      const config = INDEX_CONFIGS[window.DashboardState.currentIndexType];
      if (config) {
        fieldDetails.push(["Index Type:", window.DashboardState.currentIndexType]);
        if (window.DashboardState.currentIndexType !== 'RGB' && props.indexValue !== undefined) {
          fieldDetails.push(["Current " + window.DashboardState.currentIndexType + ":", props.indexValue.toFixed(2)]);
          fieldDetails.push(["Image Captured:", props.indexCaptureDate || 'Not available']);
          if (props.indexMin !== undefined && props.indexMin !== null) {
            fieldDetails.push(["Minimum " + window.DashboardState.currentIndexType + ":", props.indexMin.toFixed(2)]);
          }
          if (props.indexMax !== undefined && props.indexMax !== null) {
            fieldDetails.push(["Maximum " + window.DashboardState.currentIndexType + ":", props.indexMax.toFixed(2)]);
          }
        }
        if (props.cloudCover !== undefined) {
          fieldDetails.push(["Cloud Cover:", props.cloudCover.toFixed(1) + "%"]);
          fieldDetails.push(["Image Quality:", props.imageQuality || 'N/A']);
        }
      }
    }

    doc.autoTable({
      startY: 40,
      head: [],
      body: fieldDetails,
      theme: 'grid',
      styles: { fontSize: 10 },
      columnStyles: {
        0: { cellWidth: 50, fontStyle: 'bold' }
      },
      headStyles: { fillColor: [182, 191, 0] }
    });

    if (type === 'weather') {
      const yPos = doc.previousAutoTable.finalY + 10;
      doc.setFontSize(14);
      doc.setFont('helvetica', 'bold');
      doc.text("Weather Data", 14, yPos);
      doc.setFont('helvetica', 'normal');

      const tableData = WeatherManager.weatherData.map(row => [
        row.date,
        row.avgTemp,
        row.maxTemp,
        row.minTemp,
        row.rain,
        row.windSpeed
      ]);

      doc.autoTable({
        startY: yPos + 5,
        head: [['Date', 'Avg Temp (°C)', 'Max Temp (°C)', 'Min Temp (°C)', 'Rainfall (mm)', 'Wind (km/h)']],
        body: tableData,
        theme: 'grid',
        headStyles: { fillColor: [1, 40, 47] }
      });
    } else {
      const config = INDEX_CONFIGS[window.DashboardState.currentIndexType];

      if (window.DashboardState.currentIndexType !== 'RGB' && config && config.palette && config.palette.length > 0) {
        const yPos = doc.previousAutoTable.finalY + 10;
        doc.setFontSize(14);
        doc.setFont('helvetica', 'bold');
        doc.text(`${window.DashboardState.currentIndexType} Information`, 14, yPos);
        doc.setFont('helvetica', 'normal');
        doc.setFontSize(10);
        const splitDescription = doc.splitTextToSize(config.explanation, 180);
        doc.text(splitDescription, 14, yPos + 10);
      }

      if (IndexManager.indexData && IndexManager.indexData.length > 0) {
        const tableYPos = doc.previousAutoTable ? doc.previousAutoTable.finalY + 30 : 100;
        doc.setFontSize(14);
        doc.setFont('helvetica', 'bold');
        doc.text(`${window.DashboardState.currentIndexType} History`, 14, tableYPos);
        doc.setFont('helvetica', 'normal');

        const tableData = IndexManager.indexData.map(row => [
          Utils.formatDate(row.date),
          window.DashboardState.currentIndexType !== 'RGB' ? row.value.toFixed(2) : 'RGB Image'
        ]);

        doc.autoTable({
          startY: tableYPos + 5,
          head: [['Date', `${window.DashboardState.currentIndexType} Value`]],
          body: tableData,
          theme: 'grid',
          headStyles: { fillColor: [1, 40, 47] }
        });
      }
    }

    // Footer
    const pageCount = doc.internal.getNumberOfPages();
    for (let i = 1; i <= pageCount; i++) {
      doc.setPage(i);
      doc.setFillColor(1, 40, 47);
      doc.rect(0, 280, 210, 17, 'F');
      doc.setTextColor(255, 255, 255);
      doc.setFontSize(8);
      doc.text("Generated by Yieldera - " + new Date().toLocaleString(), 105, 290, { align: 'center' });
      doc.text(`Page ${i} of ${pageCount}`, 195, 290, { align: 'right' });
    }

    const today = new Date();
    let fileName;
    if (type === 'weather') {
      fileName = `${props.name || 'Field'}_Weather_Report_${today.toISOString().split('T')[0]}.pdf`;
    } else {
      fileName = `${props.name || 'Field'}_${window.DashboardState.currentIndexType}_Report_${today.toISOString().split('T')[0]}.pdf`;
    }
    doc.save(fileName);

    Notifications.show(`${type.charAt(0).toUpperCase() + type.slice(1)} PDF report generated`, 'success');
  },

  async generateForecastReport() {
    if (!window.DashboardState.selectedField || WeatherManager.forecastData.length === 0) {
      Notifications.show('No forecast data available for report', 'warning');
      return;
    }

    Notifications.show('Generating forecast report...', 'info');

    const props = window.DashboardState.selectedField.properties;
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();

    // Load logo
    const logoBase64 = await this.loadYielderaLogo();

    // Header
    doc.setFillColor(1, 40, 47);
    doc.rect(0, 0, 210, 25, 'F');
    doc.setTextColor(255, 255, 255);

    // Add Yieldera logo
    if (logoBase64) {
      try {
        // Add logo image (adjust dimensions as needed)
        doc.addImage(logoBase64, 'PNG', 15, 8, 30, 10);
      } catch (e) {
        console.warn('Could not add logo to PDF:', e);
        // Fallback to text
        doc.setFontSize(16);
        doc.setFont('helvetica', 'bold');
        doc.text("YIELDERA", 15, 15);
      }
    } else {
      // Fallback to text if logo couldn't be loaded
      doc.setFontSize(16);
      doc.setFont('helvetica', 'bold');
      doc.text("YIELDERA", 15, 15);
    }

    doc.setFontSize(18);
    doc.text("Weather Forecast Report", 105, 15, { align: 'center' });
    doc.setFontSize(8);
    doc.text(new Date().toLocaleDateString('en-GB'), 195, 15, { align: 'right' });

    // Field Details
    doc.setFontSize(14);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(0, 0, 0);
    doc.text("Field Details", 14, 35);
    doc.setFont('helvetica', 'normal');

    let fieldLat = 'N/A', fieldLon = 'N/A';
    try {
      const bounds = L.geoJSON(window.DashboardState.selectedField).getBounds();
      fieldLat = bounds.getCenter().lat.toFixed(6);
      fieldLon = bounds.getCenter().lng.toFixed(6);
    } catch (e) { }

    const fieldDetails = [
      ["Field Name:", props.name || 'N/A'],
      ["Farm Name:", props.farm_name || 'N/A'],
      ["Owner:", props.owner_name || 'N/A'],
      ["Crop Type:", props.crop || 'N/A'],
      ["Area:", props.area_ha ? props.area_ha.toFixed(2) + ' ha' : 'N/A'],
      ["Latitude:", fieldLat + "°"],
      ["Longitude:", fieldLon + "°"],
      ["Forecast Date:", new Date().toLocaleDateString('en-GB')]
    ];

    doc.autoTable({
      startY: 40,
      head: [],
      body: fieldDetails,
      theme: 'grid',
      styles: { fontSize: 10 },
      columnStyles: {
        0: { cellWidth: 40, fontStyle: 'bold' }
      },
      headStyles: { fillColor: [182, 191, 0] }
    });

    const yPos = doc.previousAutoTable.finalY + 10;
    doc.setFontSize(14);
    doc.setFont('helvetica', 'bold');
    doc.text("7-Day Weather Forecast", 14, yPos);
    doc.setFont('helvetica', 'normal');

    const tableData = WeatherManager.forecastData.map(forecast => [
      forecast.date,
      forecast.weather,
      forecast.maxTemp + '°C',
      forecast.minTemp + '°C',
      forecast.rainfall + ' mm',
      forecast.rainProbability + '%',
      forecast.windSpeed + ' km/h',
      'UV ' + forecast.uvIndex
    ]);

    doc.autoTable({
      startY: yPos + 5,
      head: [['Date', 'Weather', 'Max Temp', 'Min Temp', 'Rainfall', 'Rain Prob', 'Wind', 'UV Index']],
      body: tableData,
      theme: 'grid',
      headStyles: { fillColor: [1, 40, 47] },
      styles: { fontSize: 9, cellPadding: 2 }
    });

    const sunsetYPos = doc.previousAutoTable.finalY + 10;
    doc.setFontSize(14);
    doc.setFont('helvetica', 'bold');
    doc.text("Sunrise & Sunset Times", 14, sunsetYPos);
    doc.setFont('helvetica', 'normal');

    const sunriseSunsetData = WeatherManager.forecastData.map(forecast => [
      forecast.date,
      forecast.sunrise,
      forecast.sunset
    ]);

    doc.autoTable({
      startY: sunsetYPos + 5,
      head: [['Date', 'Sunrise', 'Sunset']],
      body: sunriseSunsetData,
      theme: 'grid',
      headStyles: { fillColor: [1, 40, 47] }
    });

    const disclaimerY = doc.previousAutoTable.finalY + 10;
    doc.setFontSize(10);
    doc.setFont('helvetica', 'italic');
    doc.setTextColor(100, 100, 100);
    doc.text("Disclaimer: Weather forecasts are provided for informational purposes only and may not be entirely accurate. Please use this information as a general guide.", 14, disclaimerY, { maxWidth: 180 });

    // Footer
    const pageCount = doc.internal.getNumberOfPages();
    for (let i = 1; i <= pageCount; i++) {
      doc.setPage(i);
      doc.setFillColor(1, 40, 47);
      doc.rect(0, 280, 210, 17, 'F');
      doc.setTextColor(255, 255, 255);
      doc.setFontSize(8);
      doc.text("Generated by Yieldera - " + new Date().toLocaleString(), 105, 290, { align: 'center' });
      doc.text(`Page ${i} of ${pageCount}`, 195, 290, { align: 'right' });
    }

    const today = new Date();
    const fileName = `${props.name || 'Field'}_Forecast_Report_${today.toISOString().split('T')[0]}.pdf`;
    doc.save(fileName);

    Notifications.show('Forecast report generated successfully', 'success');
  },

  exportWeatherData() {
    if (!window.DashboardState.selectedField || WeatherManager.weatherData.length === 0) {
      Notifications.show('No data available to export', 'warning');
      return;
    }

    const props = window.DashboardState.selectedField.properties;

    let csvContent = "data:text/csv;charset=utf-8,";
    csvContent += "Field Report\r\n";
    csvContent += `Field Name,${props.name || 'N/A'}\r\n`;
    csvContent += `Farm Name,${props.farm_name || 'N/A'}\r\n`;
    csvContent += `Owner,${props.owner_name || 'N/A'}\r\n`;
    csvContent += `Crop Type,${props.crop || 'N/A'}\r\n`;
    csvContent += `Variety,${props.variety || 'N/A'}\r\n`;
    csvContent += `Planting Date,${props.planting_date ? Utils.formatDate(props.planting_date) : 'N/A'}\r\n`;
    csvContent += `Area,${props.area_ha ? props.area_ha.toFixed(2) + ' ha' : 'N/A'}\r\n`;
    csvContent += `Irrigated,${props.irrigated ? 'Yes' : 'No'}\r\n`;
    csvContent += `Date Range,${Utils.formatDate(window.DashboardState.dateRange.start)} to ${Utils.formatDate(window.DashboardState.dateRange.end)}\r\n`;
    csvContent += `Cumulative Rainfall,${WeatherManager.cumulativeRainfall.toFixed(2)} mm\r\n\r\n`;
    csvContent += "Date,Average Temperature (°C),Max Temperature (°C),Min Temperature (°C),Rainfall (mm),Wind Speed (km/h)\r\n";

    WeatherManager.weatherData.forEach(row => {
      csvContent += `${row.date},${row.avgTemp},${row.maxTemp},${row.minTemp},${row.rain},${row.windSpeed}\r\n`;
    });

    const encodedUri = encodeURI(csvContent);
    const today = new Date();
    const fileName = `${props.name || 'Field'}_Weather_Report_${today.toISOString().split('T')[0]}.csv`;

    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', fileName);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    Notifications.show('Weather data CSV downloaded', 'success');
  }
};
