// =====================================
// Automated Visualization Module - React Component
// Production-ready for Yieldera Platform Integration
// =====================================

import React, { useState, useEffect, useRef } from 'react';
import { MapContainer, TileLayer, FeatureGroup, useMap } from 'react-leaflet';
import { EditControl } from 'react-leaflet-draw';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import 'leaflet-draw/dist/leaflet.draw.css';
import axios from 'axios';
import './VisualizationModule.css';

// Fix Leaflet default markers
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: require('leaflet/dist/images/marker-icon-2x.png').default,
  iconUrl: require('leaflet/dist/images/marker-icon.png').default,
  shadowUrl: require('leaflet/dist/images/marker-shadow.png').default,
});

// =====================================
// MAIN VISUALIZATION MODULE COMPONENT
// =====================================

const AutomatedVisualizationModule = ({ apiBaseUrl = '/api/v1' }) => {
  const [analysisParams, setAnalysisParams] = useState({
    regionName: '',
    startDate: '',
    endDate: '',
    analysisType: 'anomaly',
    geometry: null
  });
  
  const [jobStatus, setJobStatus] = useState({
    status: 'idle',
    progress: 0,
    message: '',
    jobId: null
  });
  
  const [results, setResults] = useState(null);
  const [presets, setPresets] = useState([]);
  const [errors, setErrors] = useState({});
  
  const wsRef = useRef(null);
  
  useEffect(() => {
    loadAnalysisPresets();
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);
  
  const loadAnalysisPresets = async () => {
    try {
      const response = await axios.get(`${apiBaseUrl}/visualization/presets`);
      setPresets(response.data);
    } catch (error) {
      console.error('Failed to load presets:', error);
      setErrors(prev => ({ ...prev, presets: 'Failed to load presets' }));
    }
  };
  
  const handleAnalysisSubmit = async () => {
    // Validate form
    const validationErrors = validateForm();
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }
    
    setErrors({});
    
    try {
      const response = await axios.post(`${apiBaseUrl}/visualization/generate`, analysisParams);
      const { job_id } = response.data;
      
      setJobStatus({
        status: 'pending',
        progress: 0,
        message: 'Starting analysis...',
        jobId: job_id
      });
      
      // Start WebSocket connection for real-time updates
      startWebSocketConnection(job_id);
      
    } catch (error) {
      console.error('Failed to start analysis:', error);
      setErrors({ submit: error.response?.data?.detail || 'Failed to start analysis' });
    }
  };
  
  const startWebSocketConnection = (jobId) => {
    const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/visualization-jobs/${jobId}`;
    
    wsRef.current = new WebSocket(wsUrl);
    
    wsRef.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'progress_update') {
        setJobStatus(prev => ({
          ...prev,
          status: 'running',
          progress: data.progress,
          message: data.message
        }));
      } else if (data.type === 'job_completed') {
        setJobStatus(prev => ({
          ...prev,
          status: 'completed',
          progress: 100,
          message: 'Analysis completed successfully'
        }));
        loadJobResults(jobId);
      } else if (data.type === 'job_failed') {
        setJobStatus(prev => ({
          ...prev,
          status: 'failed',
          message: data.message || 'Analysis failed'
        }));
      }
    };
    
    wsRef.current.onerror = () => {
      // Fallback to polling if WebSocket fails
      pollJobStatus(jobId);
    };
  };
  
  const pollJobStatus = async (jobId) => {
    const interval = setInterval(async () => {
      try {
        const response = await axios.get(`${apiBaseUrl}/visualization/jobs/${jobId}/status`);
        const status = response.data;
        
        setJobStatus({
          status: status.status,
          progress: status.progress,
          message: status.message,
          jobId: jobId
        });
        
        if (status.status === 'completed') {
          clearInterval(interval);
          loadJobResults(jobId);
        } else if (status.status === 'failed') {
          clearInterval(interval);
        }
      } catch (error) {
        console.error('Failed to poll job status:', error);
      }
    }, 2000);
  };
  
  const loadJobResults = async (jobId) => {
    try {
      const response = await axios.get(`${apiBaseUrl}/visualization/jobs/${jobId}/preview`);
      setResults(response.data);
    } catch (error) {
      console.error('Failed to load results:', error);
    }
  };
  
  const validateForm = () => {
    const errors = {};
    
    if (!analysisParams.regionName.trim()) {
      errors.regionName = 'Region name is required';
    }
    
    if (!analysisParams.startDate) {
      errors.startDate = 'Start date is required';
    }
    
    if (!analysisParams.endDate) {
      errors.endDate = 'End date is required';
    }
    
    if (analysisParams.startDate && analysisParams.endDate) {
      const start = new Date(analysisParams.startDate);
      const end = new Date(analysisParams.endDate);
      
      if (start >= end) {
        errors.endDate = 'End date must be after start date';
      }
      
      const daysDiff = (end - start) / (1000 * 60 * 60 * 24);
      if (daysDiff > 366) {
        errors.endDate = 'Date range cannot exceed 366 days';
      }
    }
    
    if (!analysisParams.geometry) {
      errors.geometry = 'Please define an analysis area on the map';
    }
    
    return errors;
  };
  
  const handleGeometryChange = (geometry) => {
    setAnalysisParams(prev => ({ ...prev, geometry }));
    if (errors.geometry) {
      setErrors(prev => ({ ...prev, geometry: undefined }));
    }
  };
  
  const handleCancelJob = async () => {
    if (jobStatus.jobId) {
      try {
        await axios.post(`${apiBaseUrl}/visualization/jobs/${jobStatus.jobId}/cancel`);
        setJobStatus({ status: 'idle', progress: 0, message: '', jobId: null });
        if (wsRef.current) {
          wsRef.current.close();
        }
      } catch (error) {
        console.error('Failed to cancel job:', error);
      }
    }
  };
  
  return (
    <div className="automated-visualization-module">
      <div className="module-header">
        <h2>🗺️ Automated Agricultural Analysis</h2>
        <p>Generate publication-quality risk assessment maps with real-time satellite data</p>
      </div>
      
      <div className="module-content">
        <div className="control-panel">
          <AnalysisParametersForm 
            params={analysisParams}
            onChange={setAnalysisParams}
            presets={presets}
            onSubmit={handleAnalysisSubmit}
            isRunning={jobStatus.status === 'running' || jobStatus.status === 'pending'}
            errors={errors}
          />
          
          {(jobStatus.status === 'running' || jobStatus.status === 'pending') && (
            <JobProgressPanel 
              status={jobStatus}
              onCancel={handleCancelJob}
            />
          )}
          
          {jobStatus.status === 'failed' && (
            <div className="error-panel">
              <h4>❌ Analysis Failed</h4>
              <p>{jobStatus.message}</p>
              <button onClick={() => setJobStatus({ status: 'idle', progress: 0, message: '', jobId: null })}>
                Try Again
              </button>
            </div>
          )}
        </div>
        
        <div className="map-interface">
          <MapSelector 
            geometry={analysisParams.geometry}
            onGeometryChange={handleGeometryChange}
            presets={presets}
            error={errors.geometry}
          />
        </div>
        
        {results && (
          <div className="results-panel">
            <ResultsViewer 
              results={results}
              analysisParams={analysisParams}
              apiBaseUrl={apiBaseUrl}
            />
          </div>
        )}
      </div>
    </div>
  );
};

// =====================================
// ANALYSIS PARAMETERS FORM
// =====================================

const AnalysisParametersForm = ({ params, onChange, presets, onSubmit, isRunning, errors }) => {
  
  const handleInputChange = (field, value) => {
    onChange(prev => ({ ...prev, [field]: value }));
  };
  
  const applyPreset = (preset) => {
    onChange(prev => ({
      ...prev,
      regionName: preset.name,
      geometry: preset.geometry,
      startDate: preset.default_start_date || '',
      endDate: preset.default_end_date || ''
    }));
  };
  
  const getDateLimits = () => {
    const now = new Date();
    const maxDate = now.toISOString().split('T')[0];
    const minDate = new Date(2015, 0, 1).toISOString().split('T')[0];
    return { minDate, maxDate };
  };
  
  const { minDate, maxDate } = getDateLimits();
  
  return (
    <div className="parameters-form">
      <h3>🎯 Analysis Parameters</h3>
      
      {/* Quick Presets */}
      {presets.length > 0 && (
        <div className="form-section">
          <label>Quick Start Regions</label>
          <div className="preset-buttons">
            {presets.map(preset => (
              <button 
                key={preset.id}
                className="preset-btn"
                onClick={() => applyPreset(preset)}
                disabled={isRunning}
                type="button"
              >
                📍 {preset.name}
              </button>
            ))}
          </div>
        </div>
      )}
      
      {/* Region Name */}
      <div className="form-section">
        <label htmlFor="regionName">
          Region Name *
          {errors.regionName && <span className="error-text">{errors.regionName}</span>}
        </label>
        <input
          id="regionName"
          type="text"
          value={params.regionName}
          onChange={(e) => handleInputChange('regionName', e.target.value)}
          placeholder="e.g., Zimbabwe, Mashonaland Central"
          disabled={isRunning}
          className={errors.regionName ? 'error' : ''}
        />
      </div>
      
      {/* Date Range */}
      <div className="form-section">
        <div className="date-range">
          <div>
            <label htmlFor="startDate">
              Start Date *
              {errors.startDate && <span className="error-text">{errors.startDate}</span>}
            </label>
            <input
              id="startDate"
              type="date"
              value={params.startDate}
              onChange={(e) => handleInputChange('startDate', e.target.value)}
              disabled={isRunning}
              min={minDate}
              max={maxDate}
              className={errors.startDate ? 'error' : ''}
            />
          </div>
          <div>
            <label htmlFor="endDate">
              End Date *
              {errors.endDate && <span className="error-text">{errors.endDate}</span>}
            </label>
            <input
              id="endDate"
              type="date"
              value={params.endDate}
              onChange={(e) => handleInputChange('endDate', e.target.value)}
              disabled={isRunning}
              min={params.startDate || minDate}
              max={maxDate}
              className={errors.endDate ? 'error' : ''}
            />
          </div>
        </div>
      </div>
      
      {/* Analysis Type */}
      <div className="form-section">
        <label htmlFor="analysisType">Analysis Type</label>
        <select
          id="analysisType"
          value={params.analysisType}
          onChange={(e) => handleInputChange('analysisType', e.target.value)}
          disabled={isRunning}
        >
          <option value="anomaly">🌧️ Soil Moisture Anomaly</option>
          <option value="percentage">📊 Percentage Change</option>
          <option value="absolute">💧 Absolute Soil Moisture</option>
        </select>
      </div>
      
      {/* Submit Button */}
      <button 
        className={`generate-btn ${isRunning ? 'running' : ''}`}
        onClick={onSubmit}
        disabled={isRunning}
        type="button"
      >
        {isRunning ? (
          <>
            <span className="spinner"></span>
            Generating Analysis...
          </>
        ) : (
          <>
            🚀 Generate Visualization
          </>
        )}
      </button>
      
      {errors.submit && (
        <div className="error-message">
          {errors.submit}
        </div>
      )}
    </div>
  );
};

// =====================================
// MAP SELECTOR COMPONENT
// =====================================

const MapSelector = ({ geometry, onGeometryChange, presets, error }) => {
  const [drawnItems] = useState(new L.FeatureGroup());
  
  useEffect(() => {
    if (geometry) {
      drawnItems.clearLayers();
      const layer = L.geoJSON(geometry);
      drawnItems.addLayer(layer);
    }
  }, [geometry, drawnItems]);
  
  const handleDrawCreated = (e) => {
    drawnItems.clearLayers();
    const layer = e.layer;
    drawnItems.addLayer(layer);
    
    const geojson = layer.toGeoJSON();
    onGeometryChange(geojson.geometry);
  };
  
  const handleDrawEdited = () => {
    const layers = drawnItems.getLayers();
    if (layers.length > 0) {
      const geojson = layers[0].toGeoJSON();
      onGeometryChange(geojson.geometry);
    }
  };
  
  const handleDrawDeleted = () => {
    onGeometryChange(null);
  };
  
  return (
    <div className="map-selector">
      <h3>🗺️ Define Analysis Area</h3>
      {error && <div className="error-text">{error}</div>}
      
      <div className="map-container">
        <MapContainer
          center={[-19.0154, 29.1549]}
          zoom={6}
          style={{ height: '500px', width: '100%' }}
        >
          <TileLayer
            attribution='&copy; OpenStreetMap contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          
          <FeatureGroup>
            <EditControl
              position="topright"
              onCreated={handleDrawCreated}
              onEdited={handleDrawEdited}
              onDeleted={handleDrawDeleted}
              draw={{
                rectangle: { shapeOptions: { color: '#2563eb', fillOpacity: 0.2 } },
                polygon: { shapeOptions: { color: '#2563eb', fillOpacity: 0.2 } },
                circle: false,
                circlemarker: false,
                marker: false,
                polyline: false
              }}
              edit={{ edit: true, remove: true }}
            />
          </FeatureGroup>
        </MapContainer>
      </div>
      
      <div className="map-instructions">
        <p>
          📍 Use the drawing tools above to define your analysis area, or select a preset region.
          Supported shapes: rectangles and polygons.
        </p>
      </div>
    </div>
  );
};

// =====================================
// JOB PROGRESS PANEL
// =====================================

const JobProgressPanel = ({ status, onCancel }) => {
  const getProgressColor = () => {
    if (status.status === 'failed') return '#ef4444';
    if (status.progress < 30) return '#f59e0b';
    if (status.progress < 70) return '#3b82f6';
    return '#10b981';
  };
  
  return (
    <div className="job-progress-panel">
      <h3>📊 Analysis Progress</h3>
      
      <div className="progress-info">
        <div className="progress-bar">
          <div 
            className="progress-fill"
            style={{ 
              width: `${status.progress}%`,
              backgroundColor: getProgressColor()
            }}
          ></div>
        </div>
        <div className="progress-text">
          {status.progress}% - {status.message}
        </div>
      </div>
      
      <div className="progress-stages">
        <div className={`stage ${status.progress > 10 ? 'completed' : 'pending'}`}>
          1. Initialize Earth Engine Connection
        </div>
        <div className={`stage ${status.progress > 30 ? 'completed' : 'pending'}`}>
          2. Load Satellite Data (ERA5-Land)
        </div>
        <div className={`stage ${status.progress > 50 ? 'completed' : 'pending'}`}>
          3. Calculate Soil Moisture Anomalies
        </div>
        <div className={`stage ${status.progress > 70 ? 'completed' : 'pending'}`}>
          4. Generate Professional Cartography
        </div>
        <div className={`stage ${status.progress > 90 ? 'completed' : 'pending'}`}>
          5. Prepare Export Files
        </div>
      </div>
      
      <button className="cancel-btn" onClick={onCancel} type="button">
        ❌ Cancel Analysis
      </button>
    </div>
  );
};

// =====================================
// RESULTS VIEWER COMPONENT
// =====================================

const ResultsViewer = ({ results, analysisParams, apiBaseUrl }) => {
  const [selectedExportFormat, setSelectedExportFormat] = useState('png');
  const [selectedResolution, setSelectedResolution] = useState('300');
  const [isExporting, setIsExporting] = useState(false);
  
  const downloadMap = async (format, resolution) => {
    if (!results.job_id) return;
    
    setIsExporting(true);
    
    try {
      const response = await axios.post(`${apiBaseUrl}/visualization/export`, {
        job_id: results.job_id,
        format: format,
        resolution: parseInt(resolution)
      }, {
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      const filename = `${analysisParams.regionName.replace(/\s+/g, '_')}_analysis_${analysisParams.startDate}.${format}`;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
    } catch (error) {
      console.error('Export failed:', error);
      alert('Export failed. Please try again.');
    } finally {
      setIsExporting(false);
    }
  };
  
  const formatStatistic = (value, decimals = 3) => {
    return typeof value === 'number' ? value.toFixed(decimals) : 'N/A';
  };
  
  return (
    <div className="results-viewer">
      <h3>📄 Analysis Results</h3>
      
      {/* Preview Image */}
      <div className="preview-section">
        <h4>Generated Map</h4>
        <div className="map-preview">
          <img 
            src={`data:image/png;base64,${results.image_data}`}
            alt="Agricultural Analysis Map"
            style={{ maxWidth: '100%', height: 'auto', border: '1px solid #ddd' }}
          />
        </div>
      </div>
      
      {/* Statistics Summary */}
      {results.statistics && (
        <div className="statistics-section">
          <h4>📊 Statistical Summary</h4>
          <div className="stats-grid">
            <div className="stat-item">
              <span className="stat-label">Mean Anomaly</span>
              <span className="stat-value">{formatStatistic(results.statistics.mean_anomaly)} m³/m³</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Percentage Change</span>
              <span className="stat-value">{formatStatistic(results.statistics.percentage_change, 1)}%</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Range (Min/Max)</span>
              <span className="stat-value">
                {formatStatistic(results.statistics.min_anomaly)} to {formatStatistic(results.statistics.max_anomaly)}
              </span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Standard Deviation</span>
              <span className="stat-value">{formatStatistic(results.statistics.std_anomaly)} m³/m³</span>
            </div>
          </div>
        </div>
      )}
      
      {/* Export Options */}
      <div className="export-section">
        <h4>💾 Export Options</h4>
        
        <div className="export-controls">
          <div className="control-group">
            <label>Format</label>
            <select 
              value={selectedExportFormat}
              onChange={(e) => setSelectedExportFormat(e.target.value)}
              disabled={isExporting}
            >
              <option value="png">PNG (Web/Print)</option>
              <option value="pdf">PDF (Publication)</option>
              <option value="svg">SVG (Vector)</option>
              <option value="geotiff">GeoTIFF (GIS)</option>
            </select>
          </div>
          
          <div className="control-group">
            <label>Resolution (DPI)</label>
            <select 
              value={selectedResolution}
              onChange={(e) => setSelectedResolution(e.target.value)}
              disabled={isExporting || selectedExportFormat === 'svg'}
            >
              <option value="150">150 (Web)</option>
              <option value="300">300 (Print)</option>
              <option value="600">600 (High-resolution)</option>
            </select>
          </div>
        </div>
        
        <button 
          className="export-btn primary"
          onClick={() => downloadMap(selectedExportFormat, selectedResolution)}
          disabled={isExporting}
          type="button"
        >
          {isExporting ? (
            <>
              <span className="spinner"></span>
              Exporting...
            </>
          ) : (
            <>
              📥 Download {selectedExportFormat.toUpperCase()}
            </>
          )}
        </button>
      </div>
      
      {/* Analysis Info */}
      <div className="analysis-info">
        <h4>ℹ️ Analysis Information</h4>
        <div className="info-grid">
          <div><strong>Region:</strong> {analysisParams.regionName}</div>
          <div><strong>Period:</strong> {analysisParams.startDate} to {analysisParams.endDate}</div>
          <div><strong>Analysis Type:</strong> {analysisParams.analysisType}</div>
          <div><strong>Data Source:</strong> ERA5-Land (ECMWF)</div>
          <div><strong>Resolution:</strong> 10km × 10km grid</div>
          <div><strong>Generated:</strong> {new Date().toLocaleString()}</div>
        </div>
      </div>
    </div>
  );
};

export default AutomatedVisualizationModule;
